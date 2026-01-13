import streamlit as st
import pandas as pd
import numpy as np
import re
import io
from datetime import datetime
from collections import defaultdict
import tempfile
import os

# 设置页面配置
st.set_page_config(
    page_title="销售线索合并工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 设置应用标题和说明
st.title("📊 销售线索合并工具 - Web版")
st.markdown("---")

# 初始化 session state
if 'df_merged' not in st.session_state:
    st.session_state.df_merged = None
if 'processing_log' not in st.session_state:
    st.session_state.processing_log = []

def add_log(message):
    """添加处理日志"""
    st.session_state.processing_log.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")

# 侧边栏配置
st.sidebar.header("⚙️ 配置选项")

# 1. 文件格式修复部分（原"改文件格式.ipynb"的功能）
st.sidebar.subheader("1. 文件格式修复")
uploaded_file = st.sidebar.file_uploader(
    "上传汽车之家CSV文件",
    type=['csv'],
    help="上传需要修复格式的汽车之家CSV文件"
)

if uploaded_file is not None:
    st.sidebar.success(f"已上传: {uploaded_file.name}")
    
    # 修复CSV格式的函数
    def fix_csv_format(file_content):
        """修复CSV格式问题"""
        lines = file_content.decode('utf-8-sig').splitlines()
        processed_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if i == 0:
                processed_lines.append(line)
                continue
            
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1]
            
            line = line.replace('""', 'TEMP_QUOTE')
            parts = line.split(',')
            
            processed_parts = []
            for part in parts:
                if part.startswith('"') and part.endswith('"'):
                    part = part[1:-1]
                part = part.replace('TEMP_QUOTE', '"')
                processed_parts.append(part)
            
            processed_lines.append(','.join(processed_parts))
        
        return '\n'.join(processed_lines)
    
    # 显示修复选项
    if st.sidebar.button("修复文件格式"):
        try:
            fixed_content = fix_csv_format(uploaded_file.getvalue())
            
            # 提供下载修复后的文件
            st.sidebar.download_button(
                label="下载修复后的文件",
                data=fixed_content,
                file_name=f"fixed_{uploaded_file.name}",
                mime="text/csv"
            )
            st.sidebar.success("文件格式修复完成！")
        except Exception as e:
            st.sidebar.error(f"修复失败: {str(e)}")

# 2. 销售线索合并配置
st.sidebar.subheader("2. 合并配置")

# 文件上传部分
col1, col2 = st.sidebar.columns(2)

with col1:
    yiche_file = st.file_uploader("易车网文件", type=['xlsx', 'xls'])
    
with col2:
    autohome_file = st.file_uploader("汽车之家文件", type=['csv'])

# 销售顾问选择
st.sidebar.subheader("销售顾问分配")
consultants = {
    "陈婷": st.sidebar.checkbox("陈婷", value=True),
    "张理平": st.sidebar.checkbox("张理平", value=True),
    "邵振艺": st.sidebar.checkbox("邵振艺", value=True),
    "耿佶": st.sidebar.checkbox("耿佶", value=True),
    "翁佳跃": st.sidebar.checkbox("翁佳跃", value=False),
    "陈杰": st.sidebar.checkbox("陈杰", value=False)
}

# 第一条线索指定顾问
first_consultant = st.sidebar.selectbox(
    "第一条线索指定顾问",
    ["自动分配", "陈婷", "张理平", "邵振艺", "耿佶"]
)

if first_consultant == "自动分配":
    first_consultant = ""

# 主功能区
tab1, tab2, tab3 = st.tabs(["📁 数据上传", "⚙️ 数据处理", "📊 结果分析"])

with tab1:
    st.header("数据文件上传")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("易车网文件")
        if yiche_file:
            try:
                df_yiche = pd.read_excel(yiche_file)
                st.success(f"✅ 成功读取易车网文件，共 {len(df_yiche)} 条记录")
                st.dataframe(df_yiche.head(), use_container_width=True)
            except Exception as e:
                st.error(f"读取失败: {str(e)}")
        else:
            st.info("请上传易车网Excel文件")
    
    with col2:
        st.subheader("汽车之家文件")
        if autohome_file:
            try:
                df_autohome = pd.read_csv(autohome_file)
                st.success(f"✅ 成功读取汽车之家文件，共 {len(df_autohome)} 条记录")
                st.dataframe(df_autohome.head(), use_container_width=True)
            except Exception as e:
                st.error(f"读取失败: {str(e)}")
        else:
            st.info("请上传汽车之家CSV文件")

# 复制原脚本的处理函数（需要稍作修改）
def remove_after_slash(value):
    """去除字符串中'/'之后的内容"""
    if pd.isna(value):
        return ""
    value_str = str(value).strip()
    if '/' in value_str:
        return value_str.split('/')[0].strip()
    return value_str

def get_consultant_unit(consultant_name):
    """获取顾问所属单位"""
    if consultant_name in ["张理平", "邵振艺", "耿佶", "陈婷"]:
        return "上海安吉名流汽车服务有限公司"
    elif consultant_name in ["翁佳跃", "陈杰"]:
        return "安吉名流销售部"
    return ""

def normalize_car_series(car_series, default_value="昂科威PLUS", original_source=None):
    """标准化车系名称"""
    # 这里需要复制原脚本的映射逻辑
    # 由于篇幅限制，这里简略处理
    if pd.isna(car_series) or str(car_series).strip() == '':
        return default_value
    return str(car_series).strip()

# 主要的合并函数
def process_merge(df_yiche, df_autohome, consultants, first_consultant):
    """处理合并逻辑"""
    results = []
    
    # 这里需要复制原脚本的完整处理逻辑
    # 由于代码较长，这里只展示框架
    
    # 处理易车网数据
    if df_yiche is not None:
        for idx, row in df_yiche.iterrows():
            name = remove_after_slash(row.get('客户姓名', ''))
            phone = remove_after_slash(row.get('客户号码', ''))
            
            if pd.isna(name) or pd.isna(phone) or name == '' or phone == '':
                continue
                
            # 其他处理逻辑...
            results.append({
                '姓名': name,
                '手机号': phone,
                '意向车系': normalize_car_series(row.get('线索意向车型车系', '')),
                '销售顾问': '',
                '单位': '',
                '线索来源': '易车'
            })
    
    # 处理汽车之家数据
    if df_autohome is not None:
        for idx, row in df_autohome.iterrows():
            name = remove_after_slash(row.get('客户姓名', ''))
            phone = remove_after_slash(row.get('客户手机', ''))
            
            if pd.isna(name) or pd.isna(phone) or name == '' or phone == '':
                continue
                
            # 其他处理逻辑...
            results.append({
                '姓名': name,
                '手机号': phone,
                '意向车系': normalize_car_series(row.get('意向车系', '')),
                '销售顾问': '',
                '单位': '',
                '线索来源': '汽车之家'
            })
    
    # 合并结果
    df = pd.DataFrame(results)
    
    # 去重
    before_dedup = len(df)
    df = df.drop_duplicates(subset=['手机号'], keep='first')
    after_dedup = len(df)
    
    add_log(f"去重: {before_dedup} -> {after_dedup} 条记录")
    
    return df

with tab2:
    st.header("数据处理")
    
    if yiche_file is not None or autohome_file is not None:
        if st.button("🚀 开始合并处理", type="primary"):
            with st.spinner("正在处理数据..."):
                try:
                    # 读取数据
                    df_yiche = pd.read_excel(yiche_file) if yiche_file else None
                    df_autohome = pd.read_csv(autohome_file) if autohome_file else None
                    
                    # 处理合并
                    df_result = process_merge(df_yiche, df_autohome, consultants, first_consultant)
                    
                    # 保存到session state
                    st.session_state.df_merged = df_result
                    
                    # 显示处理日志
                    st.success("✅ 数据处理完成！")
                    
                except Exception as e:
                    st.error(f"处理失败: {str(e)}")
    else:
        st.info("请先上传需要处理的文件")

with tab3:
    st.header("结果分析与下载")
    
    if st.session_state.df_merged is not None:
        df = st.session_state.df_merged
        
        # 显示数据预览
        st.subheader("📋 数据预览")
        st.dataframe(df.head(20), use_container_width=True)
        
        # 显示统计信息
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 基本统计")
            st.metric("总记录数", len(df))
            st.metric("去重前记录数", "待补充")
            
        with col2:
            st.subheader("🔍 车系统计")
            car_stats = df['意向车系'].value_counts()
            st.bar_chart(car_stats)
        
        # 提供下载
        st.subheader("💾 下载结果")
        
        # 转换为Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='合并结果')
        output.seek(0)
        
        st.download_button(
            label="📥 下载Excel文件",
            data=output,
            file_name=f"CRS线索_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("请先处理数据以查看结果")

# 页脚
st.markdown("---")
st.caption("销售线索合并工具 v1.0 | 技术支持")