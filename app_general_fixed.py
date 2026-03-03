import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import json
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
if 'fixed_yiche_df' not in st.session_state:
    st.session_state.fixed_yiche_df = None   # 修复后的易车网数据

# 初始化销售人员名单
if 'consultant_settings' not in st.session_state:
    st.session_state.consultant_settings = [
        {"姓名": "陈婷", "单位": "上海安吉名流汽车服务有限公司", "是否启用": True},
        {"姓名": "张理平", "单位": "上海安吉名流汽车服务有限公司", "是否启用": True},
        {"姓名": "邵振艺", "单位": "上海安吉名流汽车服务有限公司", "是否启用": True},
        {"姓名": "耿佶", "单位": "上海安吉名流汽车服务有限公司", "是否启用": True},
        {"姓名": "翁佳跃", "单位": "安吉名流销售部", "是否启用": False},
        {"姓名": "陈杰", "单位": "安吉名流销售部", "是否启用": False}
    ]

# 初始化映射规则
if 'car_series_mapping' not in st.session_state:
    st.session_state.car_series_mapping = [
        {"原始模式": r".*GL8.*陆尊.*", "目标车系": "GL8 豪华商务车", "是否启用": True},
        {"原始模式": r".*GL8.*陆上公务舱.*", "目标车系": "GL8 陆上公务舱", "是否启用": True},
        {"原始模式": r".*GL8.*陆尚.*", "目标车系": "GL8陆尚", "是否启用": True},
        {"原始模式": r".*GL8.*Avenir.*", "目标车系": "GL8 Avenir", "是否启用": True},
        {"原始模式": r".*GL8.*豪华商务车.*", "目标车系": "GL8 豪华商务车", "是否启用": True},
        {"原始模式": r".*君越.*", "目标车系": "全新一代君越", "是否启用": True},
        {"原始模式": r".*君威.*", "目标车系": "全新一代君威", "是否启用": True},
        {"原始模式": r".*新君威.*", "目标车系": "全新一代君威", "是否启用": True},
        {"原始模式": r".*昂科威Plus.*", "目标车系": "昂科威PLUS", "是否启用": True},
        {"原始模式": r".*昂科威PLUS.*", "目标车系": "昂科威PLUS", "是否启用": True},
        {"原始模式": r".*昂科威S.*", "目标车系": "昂科威S", "是否启用": True},
        {"原始模式": r".*威朗.*", "目标车系": "威朗Pro", "是否启用": True},
        {"原始模式": r".*微蓝6.*", "目标车系": "VELITE 6", "是否启用": True},
        {"原始模式": r".*VELITE 6.*", "目标车系": "VELITE 6", "是否启用": True},
        {"原始模式": r".*E5.*", "目标车系": "E 5", "是否启用": True},
        {"原始模式": r".*E 5.*", "目标车系": "E 5", "是否启用": True},
        {"原始模式": r".*世纪.*", "目标车系": "世纪", "是否启用": True},
        {"原始模式": r".*世家.*", "目标车系": "至境世家", "是否启用": True},
        {"原始模式": r".*L7.*", "目标车系": "至境L7", "是否启用": True},
        {"原始模式": r".*昂科旗.*", "目标车系": "昂科威PLUS", "是否启用": True},
        {"原始模式": r".*别克.*", "目标车系": "昂科威PLUS", "是否启用": True},
        {"原始模式": r".*E7.*", "目标车系": "至境E7", "是否启用": True},
    ]

if 'source_category_mapping' not in st.session_state:
    st.session_state.source_category_mapping = [
        {"原始来源": "车商汇", "目标分类": "垂媒", "是否启用": True},
        {"原始来源": "车商汇（集客号）", "目标分类": "垂媒", "是否启用": True},
        {"原始来源": "车商汇（IM会话）", "目标分类": "垂媒", "是否启用": True},
        {"原始来源": "车商汇（分期）", "目标分类": "垂媒", "是否启用": True},
        {"原始来源": "车商汇（平台活动）", "目标分类": "垂媒", "是否启用": True},
        {"原始来源": "智能产品（智能展厅）", "目标分类": "垂媒", "是否启用": True},
        {"原始来源": "抖音", "目标分类": "自媒", "是否启用": True},
        {"原始来源": "本地通-经销商号", "目标分类": "自媒", "是否启用": True},
        {"原始来源": "本地通异地-经销商号", "目标分类": "自媒", "是否启用": True},
        {"原始来源": "本地通", "目标分类": "自媒", "是否启用": True},
        {"原始来源": "易车网", "目标分类": "垂媒", "是否启用": True},
        {"原始来源": "汽车之家", "目标分类": "垂媒", "是否启用": True},
        {"原始来源": "别克私域", "目标分类": "主机厂下发", "是否启用": True},
        {"原始来源": "iBuick", "目标分类": "主机厂下发", "是否启用": True},
        {"原始来源": "总部矩阵号", "目标分类": "主机厂下发", "是否启用": True},
        {"原始来源": "经销商市场活动", "目标分类": "排除", "是否启用": True},
        {"原始来源": "高德地图", "目标分类": "主机厂下发", "是否启用": True},
        {"原始来源": "矩阵号", "目标分类": "主机厂下发", "是否启用": True},
        {"原始来源": "总部", "目标分类": "主机厂下发", "是否启用": True},
        {"原始来源": "本地", "目标分类": "自媒", "是否启用": True},
        {"原始来源": "官方", "目标分类": "主机厂下发", "是否启用": True},
        {"原始来源": "别克", "目标分类": "主机厂下发", "是否启用": True},
    ]

if 'source_detail_mapping' not in st.session_state:
    st.session_state.source_detail_mapping = [
        {"原始来源": "车商汇", "目标线索来源": "汽车之家", "是否启用": True},
        {"原始来源": "车商汇(集客号)", "目标线索来源": "汽车之家", "是否启用": True},
        {"原始来源": "车商汇（IM会话）", "目标线索来源": "汽车之家", "是否启用": True},
        {"原始来源": "车商汇（分期）", "目标线索来源": "汽车之家", "是否启用": True},
        {"原始来源": "车商汇（平台活动）", "目标线索来源": "汽车之家", "是否启用": True},
        {"原始来源": "智能产品（智能展厅）", "目标线索来源": "汽车之家", "是否启用": True},
        {"原始来源": "抖音", "目标线索来源": "抖音", "是否启用": True},
        {"原始来源": "本地通-经销商号", "目标线索来源": "抖音", "是否启用": True},
        {"原始来源": "本地通异地-经销商号", "目标线索来源": "抖音", "是否启用": True},
        {"原始来源": "本地", "目标线索来源": "抖音", "是否启用": True},
        {"原始来源": "易车网", "目标线索来源": "易车", "是否启用": True},
        {"原始来源": "汽车之家", "目标线索来源": "汽车之家", "是否启用": True},
        {"原始来源": "别克私域", "目标线索来源": "", "是否启用": True},
        {"原始来源": "iBuick", "目标线索来源": "", "是否启用": True},
        {"原始来源": "总部矩阵号", "目标线索来源": "", "是否启用": True},
        {"原始来源": "经销商市场活动", "目标线索来源": "排除", "是否启用": True},
        {"原始来源": "高德地图", "目标线索来源": "", "是否启用": True},
        {"原始来源": "矩阵号", "目标线索来源": "", "是否启用": True},
        {"原始来源": "总部", "目标线索来源": "", "是否启用": True},
        {"原始来源": "本地", "目标线索来源": "抖音", "是否启用": True},
        {"原始来源": "官方", "目标线索来源": "", "是否启用": True},
        {"原始来源": "别克", "目标线索来源": "", "是否启用": True},
    ]

def add_log(message):
    """添加处理日志"""
    st.session_state.processing_log.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")

# 侧边栏配置
st.sidebar.header("⚙️ 配置选项")

# 1. 文件格式修复部分（针对易车网CSV）
st.sidebar.subheader("1. 文件格式修复（易车网）")
uploaded_file = st.sidebar.file_uploader(
    "上传易车网CSV文件（如需修复格式）",
    type=['csv'],
    help="上传需要修复格式的易车网CSV文件",
    key="yiche_original"
)

if uploaded_file is not None:
    st.sidebar.success(f"已上传: {uploaded_file.name}")
    
    # 修复CSV格式的函数
    def fix_csv_format(file_content):
        """修复CSV格式问题"""
        try:
            # 尝试多种方式读取
            content = file_content.decode('utf-8-sig')
        except:
            try:
                content = file_content.decode('gbk')
            except:
                content = file_content.decode('utf-8', errors='ignore')
        
        lines = content.splitlines()
        processed_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if i == 0:
                # 标题行
                processed_lines.append(line)
                continue
            
            if not line:  # 跳过空行
                continue
            
            # 处理引号
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1]
            
            # 处理转义的双引号
            line = line.replace('""', 'TEMP_QUOTE')
            
            # 分割字段
            parts = []
            current_part = []
            in_quotes = False
            
            for char in line:
                if char == '"' and not in_quotes:
                    in_quotes = True
                elif char == '"' and in_quotes:
                    in_quotes = False
                elif char == ',' and not in_quotes:
                    parts.append(''.join(current_part))
                    current_part = []
                else:
                    current_part.append(char)
            
            if current_part:
                parts.append(''.join(current_part))
            
            # 恢复转义的双引号
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
            
            # 读取修复后的内容到DataFrame
            try:
                fixed_df = pd.read_csv(io.StringIO(fixed_content))
                st.session_state.fixed_yiche_df = fixed_df
                
                # 提供下载修复后的文件
                st.sidebar.download_button(
                    label="下载修复后的文件",
                    data=fixed_content,
                    file_name=f"fixed_{uploaded_file.name}",
                    mime="text/csv"
                )
                st.sidebar.success(f"文件格式修复完成！共 {len(fixed_df)} 条记录")
                
                # 显示修复后的数据预览
                with st.sidebar.expander("查看修复后的数据预览"):
                    st.dataframe(fixed_df.head(5))
                    
            except Exception as e:
                st.sidebar.error(f"读取修复后的文件失败: {str(e)}")
                
        except Exception as e:
            st.sidebar.error(f"修复失败: {str(e)}")

# 2. 映射规则管理
with st.sidebar.expander("🗺️ 映射规则管理", expanded=False):
    tab1, tab2, tab3 = st.tabs(["🚗 车系映射", "📊 来源分类", "🔍 线索来源"])
    
    with tab1:
        st.write("车系名称映射规则：")
        car_mapping_df = pd.DataFrame(st.session_state.car_series_mapping)
        edited_car_df = st.data_editor(
            car_mapping_df,
            column_config={
                "原始模式": st.column_config.TextColumn("原始模式(支持正则)", width="large", required=True, help="使用正则表达式匹配原始车系名称"),
                "目标车系": st.column_config.TextColumn("目标车系", width="medium", required=True),
                "是否启用": st.column_config.CheckboxColumn("是否启用", default=True)
            },
            num_rows="dynamic",
            key="car_mapping_editor"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 保存车系规则", use_container_width=True, key="save_car_mapping"):
                st.session_state.car_series_mapping = edited_car_df.to_dict('records')
                st.success("车系映射规则已更新！")
        
        with col2:
            if st.button("🔄 恢复默认", use_container_width=True, key="reset_car_mapping"):
                st.session_state.car_series_mapping = [
                    {"原始模式": r".*GL8.*陆尊.*", "目标车系": "GL8 豪华商务车", "是否启用": True},
                    {"原始模式": r".*GL8.*陆上公务舱.*", "目标车系": "GL8 陆上公务舱", "是否启用": True},
                    {"原始模式": r".*GL8.*陆尚.*", "目标车系": "GL8陆尚", "是否启用": True},
                    {"原始模式": r".*GL8.*Avenir.*", "目标车系": "GL8 Avenir", "是否启用": True},
                    {"原始模式": r".*GL8.*豪华商务车.*", "目标车系": "GL8 豪华商务车", "是否启用": True},
                    {"原始模式": r".*君越.*", "目标车系": "全新一代君越", "是否启用": True},
                    {"原始模式": r".*君威.*", "目标车系": "全新一代君威", "是否启用": True},
                    {"原始模式": r".*新君威.*", "目标车系": "全新一代君威", "是否启用": True},
                    {"原始模式": r".*昂科威Plus.*", "目标车系": "昂科威PLUS", "是否启用": True},
                    {"原始模式": r".*昂科威PLUS.*", "目标车系": "昂科威PLUS", "是否启用": True},
                    {"原始模式": r".*昂科威S.*", "目标车系": "昂科威S", "是否启用": True},
                    {"原始模式": r".*威朗.*", "目标车系": "威朗Pro", "是否启用": True},
                    {"原始模式": r".*微蓝6.*", "目标车系": "VELITE 6", "是否启用": True},
                    {"原始模式": r".*VELITE 6.*", "目标车系": "VELITE 6", "是否启用": True},
                    {"原始模式": r".*E5.*", "目标车系": "E 5", "是否启用": True},
                    {"原始模式": r".*E 5.*", "目标车系": "E 5", "是否启用": True},
                    {"原始模式": r".*世纪.*", "目标车系": "世纪", "是否启用": True},
                    {"原始模式": r".*世家.*", "目标车系": "至境世家", "是否启用": True},
                    {"原始模式": r".*L7.*", "目标车系": "至境L7", "是否启用": True},
                    {"原始模式": r".*昂科旗.*", "目标车系": "昂科威PLUS", "是否启用": True},
                    {"原始模式": r".*别克.*", "目标车系": "昂科威PLUS", "是否启用": True},
                    {"原始模式": r".*E7.*", "目标车系": "至境E7", "是否启用": True},
                ]
                st.success("已恢复默认车系映射规则！")
    
    with tab2:
        st.write("来源分类映射规则：")
        st.markdown("""
        **特殊规则说明：**
        设置目标分类为`排除`时，系统会自动剔除该来源的线索
        """)
        category_mapping_df = pd.DataFrame(st.session_state.source_category_mapping)
        edited_category_df = st.data_editor(
            category_mapping_df,
            column_config={
                "原始来源": st.column_config.TextColumn("原始来源", width="large", required=True),
                "目标分类": st.column_config.TextColumn("目标分类", width="medium", required=True, help="设置为'排除'会剔除该来源的线索"),
                "是否启用": st.column_config.CheckboxColumn("是否启用", default=True)
            },
            num_rows="dynamic",
            key="category_mapping_editor"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 保存分类规则", use_container_width=True, key="save_category_mapping"):
                st.session_state.source_category_mapping = edited_category_df.to_dict('records')
                st.success("来源分类映射规则已更新！")
        
        with col2:
            if st.button("🔄 恢复默认", use_container_width=True, key="reset_category_mapping"):
                st.session_state.source_category_mapping = [
                    {"原始来源": "车商汇", "目标分类": "垂媒", "是否启用": True},
                    {"原始来源": "车商汇（集客号）", "目标分类": "垂媒", "是否启用": True},
                    {"原始来源": "车商汇（IM会话）", "目标分类": "垂媒", "是否启用": True},
                    {"原始来源": "车商汇（分期）", "目标分类": "垂媒", "是否启用": True},
                    {"原始来源": "车商汇（平台活动）", "目标分类": "垂媒", "是否启用": True},
                    {"原始来源": "智能产品（智能展厅）", "目标分类": "垂媒", "是否启用": True},
                    {"原始来源": "抖音", "目标分类": "自媒", "是否启用": True},
                    {"原始来源": "本地通-经销商号", "目标分类": "自媒", "是否启用": True},
                    {"原始来源": "本地通异地-经销商号", "目标分类": "自媒", "是否启用": True},
                    {"原始来源": "本地通", "目标分类": "自媒", "是否启用": True},
                    {"原始来源": "易车网", "目标分类": "垂媒", "是否启用": True},
                    {"原始来源": "汽车之家", "目标分类": "垂媒", "是否启用": True},
                    {"原始来源": "别克私域", "目标分类": "主机厂下发", "是否启用": True},
                    {"原始来源": "iBuick", "目标分类": "主机厂下发", "是否启用": True},
                    {"原始来源": "总部矩阵号", "目标分类": "主机厂下发", "是否启用": True},
                    {"原始来源": "经销商市场活动", "目标分类": "排除", "是否启用": True},
                    {"原始来源": "高德地图", "目标分类": "主机厂下发", "是否启用": True},
                    {"原始来源": "矩阵号", "目标分类": "主机厂下发", "是否启用": True},
                    {"原始来源": "总部", "目标分类": "主机厂下发", "是否启用": True},
                    {"原始来源": "本地", "目标分类": "自媒", "是否启用": True},
                    {"原始来源": "官方", "目标分类": "主机厂下发", "是否启用": True},
                    {"原始来源": "别克", "目标分类": "主机厂下发", "是否启用": True},
                ]
                st.success("已恢复默认来源分类映射规则！")
    
    with tab3:
        st.write("线索来源映射规则：")
        st.markdown("""
        **特殊规则说明：**
        - 设置目标线索来源为`排除`时，系统会自动剔除该来源的线索
        """)
        detail_mapping_df = pd.DataFrame(st.session_state.source_detail_mapping)
        edited_detail_df = st.data_editor(
            detail_mapping_df,
            column_config={
                "原始来源": st.column_config.TextColumn("原始来源", width="large", required=True),
                "目标线索来源": st.column_config.TextColumn("目标线索来源", width="medium", required=True, help="设置为'排除'会剔除该来源的线索"),
                "是否启用": st.column_config.CheckboxColumn("是否启用", default=True)
            },
            num_rows="dynamic",
            key="detail_mapping_editor"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 保存线索规则", use_container_width=True, key="save_detail_mapping"):
                st.session_state.source_detail_mapping = edited_detail_df.to_dict('records')
                st.success("线索来源映射规则已更新！")
        
        with col2:
            if st.button("🔄 恢复默认", use_container_width=True, key="reset_detail_mapping"):
                st.session_state.source_detail_mapping = [
                    {"原始来源": "车商汇", "目标线索来源": "汽车之家", "是否启用": True},
                    {"原始来源": "车商汇(集客号)", "目标线索来源": "汽车之家", "是否启用": True},
                    {"原始来源": "车商汇（IM会话）", "目标线索来源": "汽车之家", "是否启用": True},
                    {"原始来源": "车商汇（分期）", "目标线索来源": "汽车之家", "是否启用": True},
                    {"原始来源": "车商汇（平台活动）", "目标线索来源": "汽车之家", "是否启用": True},
                    {"原始来源": "智能产品（智能展厅）", "目标线索来源": "汽车之家", "是否启用": True},
                    {"原始来源": "抖音", "目标线索来源": "抖音", "是否启用": True},
                    {"原始来源": "本地通-经销商号", "目标线索来源": "抖音", "是否启用": True},
                    {"原始来源": "本地通异地-经销商号", "目标线索来源": "抖音", "是否启用": True},
                    {"原始来源": "本地", "目标线索来源": "抖音", "是否启用": True},
                    {"原始来源": "易车网", "目标线索来源": "易车", "是否启用": True},
                    {"原始来源": "汽车之家", "目标线索来源": "汽车之家", "是否启用": True},
                    {"原始来源": "别克私域", "目标线索来源": "", "是否启用": True},
                    {"原始来源": "iBuick", "目标线索来源": "", "是否启用": True},
                    {"原始来源": "总部矩阵号", "目标线索来源": "", "是否启用": True},
                    {"原始来源": "经销商市场活动", "目标线索来源": "排除", "是否启用": True},
                    {"原始来源": "高德地图", "目标线索来源": "", "是否启用": True},
                    {"原始来源": "矩阵号", "目标线索来源": "", "是否启用": True},
                    {"原始来源": "总部", "目标线索来源": "", "是否启用": True},
                    {"原始来源": "本地", "目标线索来源": "抖音", "是否启用": True},
                    {"原始来源": "官方", "目标线索来源": "", "是否启用": True},
                    {"原始来源": "别克", "目标线索来源": "", "是否启用": True},
                ]
                st.success("已恢复默认线索来源映射规则！")
    
    # 导入/导出功能
    st.write("---")
    st.write("导入/导出映射规则：")
    
    col3, col4 = st.columns(2)
    with col3:
        # 导出所有映射规则
        all_mappings = {
            "car_series_mapping": st.session_state.car_series_mapping,
            "source_category_mapping": st.session_state.source_category_mapping,
            "source_detail_mapping": st.session_state.source_detail_mapping
        }
        settings_json = json.dumps(all_mappings, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 导出所有规则",
            data=settings_json,
            file_name="映射规则配置.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col4:
        # 导入映射规则
        uploaded_mappings = st.file_uploader("导入规则文件", type=['json'], key="mappings_upload", label_visibility="collapsed")
        if uploaded_mappings:
            try:
                new_mappings = json.load(uploaded_mappings)
                if "car_series_mapping" in new_mappings:
                    st.session_state.car_series_mapping = new_mappings["car_series_mapping"]
                if "source_category_mapping" in new_mappings:
                    st.session_state.source_category_mapping = new_mappings["source_category_mapping"]
                if "source_detail_mapping" in new_mappings:
                    st.session_state.source_detail_mapping = new_mappings["source_detail_mapping"]
                st.success("映射规则导入成功！")
            except Exception as e:
                st.error(f"导入失败: {str(e)}")

# 3. 销售人员管理
with st.sidebar.expander("👥 销售人员管理", expanded=False):
    st.write("修改销售人员名单和对应单位：")
    
    # 显示当前销售人员名单
    st.write("当前销售人员名单：")
    consultant_df = pd.DataFrame(st.session_state.consultant_settings)
    edited_df = st.data_editor(
        consultant_df,
        column_config={
            "姓名": st.column_config.TextColumn("姓名", width="medium", required=True),
            "单位": st.column_config.TextColumn("单位", width="large", required=True),
            "是否启用": st.column_config.CheckboxColumn("是否启用", default=True)
        },
        num_rows="dynamic",
        key="consultant_editor"
    )
    
    # 保存修改按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存修改", use_container_width=True, key="save_consultants"):
            # 更新销售人员名单
            st.session_state.consultant_settings = edited_df.to_dict('records')
            st.success("销售人员名单已更新！")
    
    with col2:
        if st.button("🔄 恢复默认", use_container_width=True, key="reset_consultants"):
            # 恢复默认设置
            st.session_state.consultant_settings = [
                {"姓名": "陈婷", "单位": "上海安吉名流汽车服务有限公司", "是否启用": True},
                {"姓名": "张理平", "单位": "上海安吉名流汽车服务有限公司", "是否启用": True},
                {"姓名": "邵振艺", "单位": "上海安吉名流汽车服务有限公司", "是否启用": True},
                {"姓名": "耿佶", "单位": "上海安吉名流汽车服务有限公司", "是否启用": True},
                {"姓名": "翁佳跃", "单位": "安吉名流销售部", "是否启用": False},
                {"姓名": "陈杰", "单位": "安吉名流销售部", "是否启用": False}
            ]
            st.success("已恢复默认设置！")

# 4. 销售线索合并配置
st.sidebar.subheader("2. 合并配置")

# 文件上传部分（交换类型）
col1, col2 = st.sidebar.columns(2)

with col1:
    yiche_file = st.file_uploader("易车网文件 (CSV)", type=['csv'], key="yiche_file")
    
with col2:
    autohome_file = st.file_uploader("汽车之家文件 (Excel)", type=['xlsx', 'xls'], key="autohome_file")

# 销售顾问选择
st.sidebar.subheader("销售顾问分配")

# 从设置中生成销售顾问选择列表
consultants = {}
for consultant in st.session_state.consultant_settings:
    consultants[consultant["姓名"]] = st.sidebar.checkbox(
        f"{consultant['姓名']} ({consultant['单位']})",
        value=consultant["是否启用"],
        key=f"consultant_{consultant['姓名']}"
    )

# 获取选中的顾问列表
selected_consultants = [name for name, selected in consultants.items() if selected]

# 第一条线索指定顾问 - 动态生成选项
if selected_consultants:
    first_consultant_options = ["自动分配"] + selected_consultants
    first_consultant = st.sidebar.selectbox(
        "第一条线索指定顾问",
        first_consultant_options,
        key="first_consultant"
    )
    
    if first_consultant == "自动分配":
        first_consultant = ""
else:
    st.sidebar.warning("请至少选择一个销售顾问")
    first_consultant = ""

# 复制原脚本的处理函数
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
    # 从设置中查找单位
    for consultant in st.session_state.consultant_settings:
        if consultant["姓名"] == consultant_name:
            return consultant["单位"]
    return ""

def normalize_car_series(car_series, default_value="昂科威PLUS", original_source=None):
    """标准化车系名称 - 使用可配置的映射规则"""
    if pd.isna(car_series) or str(car_series).strip() == '':
        return default_value
    
    original = str(car_series).strip()
    
    # 使用可配置的映射规则
    for mapping_rule in st.session_state.car_series_mapping:
        if mapping_rule["是否启用"]:
            pattern = mapping_rule["原始模式"]
            try:
                if re.search(pattern, original, re.IGNORECASE):
                    return mapping_rule["目标车系"]
            except re.error:
                # 如果正则表达式无效，尝试字符串包含匹配
                if pattern in original or original in pattern:
                    return mapping_rule["目标车系"]
    
    return default_value

def map_source_category(source_value):
    """映射来源分类 - 使用可配置的映射规则"""
    if pd.isna(source_value):
        return "其他"
    
    source_str = str(source_value).strip()
    if not source_str:
        return "其他"
    
    # 使用可配置的映射规则
    for mapping_rule in st.session_state.source_category_mapping:
        if mapping_rule["是否启用"]:
            original_source = mapping_rule["原始来源"]
            # 精确匹配或模糊匹配
            if original_source == source_str or original_source in source_str or source_str in original_source:
                target = mapping_rule["目标分类"]
                # 如果目标分类为"排除"，返回特殊标记
                if target == "排除":
                    return "排除"
                return target
    
    return "其他"

def map_source_detail(source_value):
    """映射线索来源 - 使用可配置的映射规则"""
    if pd.isna(source_value):
        return ""
    
    source_str = str(source_value).strip()
    if not source_str:
        return ""
    
    # 使用可配置的映射规则
    for mapping_rule in st.session_state.source_detail_mapping:
        if mapping_rule["是否启用"]:
            original_source = mapping_rule["原始来源"]
            # 精确匹配或模糊匹配
            if original_source == source_str or original_source in source_str or source_str in original_source:
                target = mapping_rule["目标线索来源"]
                # 如果目标线索来源为"排除"，返回特殊标记
                if target == "排除":
                    return "排除"
                return target
    
    return ""

def fair_allocate_consultants(records, selected_consultants_dict, first_consultant=None):
    """公平分配销售顾问"""
    # 获取选中的顾问列表
    available_consultants = [name for name, selected in selected_consultants_dict.items() if selected]
    
    if not available_consultants:
        return records
    
    # 初始化计数器
    consultant_counts = {consultant: 0 for consultant in available_consultants}
    
    # 如果指定了第一条线索的顾问，调整队列
    if first_consultant and first_consultant in available_consultants:
        first_index = available_consultants.index(first_consultant)
        consultant_queue = available_consultants[first_index:] + available_consultants[:first_index]
    else:
        consultant_queue = available_consultants.copy()
    
    # 为每条记录分配顾问
    for i, record in enumerate(records):
        # 选择分配最少的顾问
        available_counts = {c: consultant_counts[c] for c in consultant_queue}
        min_count = min(available_counts.values())
        min_consultants = [c for c, count in available_counts.items() if count == min_count]
        
        # 选择在队列中位置靠前的
        selected_consultant = consultant_queue[0]  # 默认选择第一个
        for consultant in consultant_queue:
            if consultant in min_consultants:
                selected_consultant = consultant
                break
        
        # 更新分配数量
        consultant_counts[selected_consultant] += 1
        
        # 分配顾问和单位
        record['销售顾问'] = selected_consultant
        record['单位'] = get_consultant_unit(selected_consultant)
    
    return records

def process_merge(df_yiche, df_autohome, selected_consultants_dict, first_consultant):
    """处理合并逻辑 - 汽车之家来源固定为垂媒/汽车之家"""
    results = []
    excluded_count = 0
    
    # 处理易车网数据
    if df_yiche is not None:
        st.info(f"处理易车网数据: {len(df_yiche)} 条记录")
        for idx, row in df_yiche.iterrows():
            name = remove_after_slash(row.get('客户姓名', ''))
            phone = remove_after_slash(row.get('客户号码', ''))
            
            if pd.isna(name) or pd.isna(phone) or name == '' or phone == '':
                continue
            
            # 标准化车系
            original_car_series = row.get('线索意向车型车系', '')
            car_series = normalize_car_series(original_car_series, default_value="昂科威PLUS", original_source="易车网")
            
            # 来源信息
            source = row.get('商业产品来源', '')
            if pd.isna(source):
                source = row.get('来源', '')
            
            source_category = map_source_category(source)
            source_detail = map_source_detail(source)
            
            # 检查是否需要排除（来源分类或线索来源为"排除"）
            if source_category == "排除" or source_detail == "排除":
                excluded_count += 1
                continue
            
            results.append({
                '姓名': name,
                '手机号': phone,
                '性别': '',
                '来源分类': source_category,
                '线索来源': source_detail,
                '备注': '',
                '意向品牌': '别克',
                '意向车系': car_series,
                '销售顾问': '',
                '单位': '',
                '跟进内容': ''
            })
    
    # 处理汽车之家数据
    if df_autohome is not None:
        st.info(f"处理汽车之家数据: {len(df_autohome)} 条记录")
        for idx, row in df_autohome.iterrows():
            name = remove_after_slash(row.get('客户姓名', ''))
            phone = remove_after_slash(row.get('客户号码', ''))
            
            if pd.isna(name) or pd.isna(phone) or name == '' or phone == '':
                continue
            
            # 标准化车系（使用新的列名：意向车系车型）
            original_car_series = row.get('意向车系车型', '')
            car_series = normalize_car_series(original_car_series, default_value="昂科威PLUS", original_source="汽车之家")
            
            # 来源信息 - 固定为垂媒和汽车之家（不再从文件中读取）
            source_category = "垂媒"
            source_detail = "汽车之家"
            
            results.append({
                '姓名': name,
                '手机号': phone,
                '性别': '',
                '来源分类': source_category,
                '线索来源': source_detail,
                '备注': '',
                '意向品牌': '别克',
                '意向车系': car_series,
                '销售顾问': '',
                '单位': '',
                '跟进内容': ''
            })
    
    # 合并结果
    if excluded_count > 0:
        add_log(f"排除了 {excluded_count} 条被标记为'排除'的线索")
    
    if not results:
        st.error("没有找到有效数据")
        return None
    
    df = pd.DataFrame(results)
    
    # 去重
    before_dedup = len(df)
    df = df.drop_duplicates(subset=['手机号'], keep='first')
    after_dedup = len(df)
    
    add_log(f"去重: {before_dedup} -> {after_dedup} 条记录")
    
    # 检查并修复空车系
    empty_car_series_count = df['意向车系'].isna().sum() + (df['意向车系'] == '').sum()
    if empty_car_series_count > 0:
        df['意向车系'] = df['意向车系'].apply(lambda x: "昂科威PLUS" if pd.isna(x) or str(x).strip() == '' else x)
    
    # 公平分配销售顾问
    records = df.to_dict('records')
    records = fair_allocate_consultants(records, selected_consultants_dict, first_consultant)
    
    # 转换回DataFrame
    df = pd.DataFrame(records)
    
    # 确保数据列的顺序
    final_columns = [
        '姓名', '手机号', '性别', '来源分类', '线索来源', '备注',
        '意向品牌', '意向车系', '销售顾问', '单位', '跟进内容'
    ]
    
    # 确保DataFrame只包含我们需要的列
    df = df[final_columns]
    
    return df

# 主功能区
tab1, tab2, tab3 = st.tabs(["📁 数据上传", "⚙️ 数据处理", "📊 结果分析"])

with tab1:
    st.header("数据文件上传")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("易车网文件 (CSV)")
        if yiche_file:
            try:
                # 尝试多种编码读取CSV
                try:
                    df_yiche = pd.read_csv(yiche_file, encoding='utf-8')
                except:
                    try:
                        df_yiche = pd.read_csv(yiche_file, encoding='gbk')
                    except:
                        content = yiche_file.getvalue()
                        try:
                            content_str = content.decode('utf-8-sig')
                        except:
                            content_str = content.decode('utf-8', errors='ignore')
                        df_yiche = pd.read_csv(io.StringIO(content_str))
                
                st.success(f"✅ 成功读取易车网文件，共 {len(df_yiche)} 条记录")
                st.dataframe(df_yiche.head(), use_container_width=True)
                
                # 显示列名
                with st.expander("查看文件列名"):
                    st.write("列名列表:", list(df_yiche.columns))
            except Exception as e:
                st.error(f"读取失败: {str(e)}")
                st.info("如果文件格式有问题，请尝试使用左侧的'文件格式修复'功能")
        else:
            st.info("请上传易车网CSV文件")
    
    with col2:
        st.subheader("汽车之家文件 (Excel)")
        if autohome_file:
            try:
                df_autohome = pd.read_excel(autohome_file)
                st.success(f"✅ 成功读取汽车之家文件，共 {len(df_autohome)} 条记录")
                st.dataframe(df_autohome.head(), use_container_width=True)
                
                # 显示列名
                with st.expander("查看文件列名"):
                    st.write("列名列表:", list(df_autohome.columns))
                    
            except Exception as e:
                st.error(f"读取失败: {str(e)}")
        else:
            st.info("请上传汽车之家Excel文件")
    
    # 显示修复后的易车网数据（如果存在）
    if st.session_state.fixed_yiche_df is not None:
        st.subheader("修复后的易车网数据")
        st.dataframe(st.session_state.fixed_yiche_df.head(), use_container_width=True)
        st.success(f"修复后的数据共 {len(st.session_state.fixed_yiche_df)} 条记录")

with tab2:
    st.header("数据处理")
    
    # 显示当前映射规则统计
    with st.expander("查看当前映射规则统计", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            enabled_car = sum(1 for rule in st.session_state.car_series_mapping if rule["是否启用"])
            total_car = len(st.session_state.car_series_mapping)
            st.metric("车系映射规则", f"{enabled_car}/{total_car} 条启用")
        
        with col2:
            enabled_category = sum(1 for rule in st.session_state.source_category_mapping if rule["是否启用"])
            total_category = len(st.session_state.source_category_mapping)
            st.metric("来源分类规则", f"{enabled_category}/{total_category} 条启用")
        
        with col3:
            enabled_detail = sum(1 for rule in st.session_state.source_detail_mapping if rule["是否启用"])
            total_detail = len(st.session_state.source_detail_mapping)
            st.metric("线索来源规则", f"{enabled_detail}/{total_detail} 条启用")
    
    # 检查是否有选中的销售顾问
    if not selected_consultants:
        st.warning("⚠️ 请先在侧边栏选择至少一个销售顾问")
    
    # 检查是否上传了文件
    files_available = (yiche_file is not None) or (autohome_file is not None) or (st.session_state.fixed_yiche_df is not None)
    
    if files_available and selected_consultants:
        if st.button("🚀 开始合并处理", type="primary"):
            with st.spinner("正在处理数据..."):
                try:
                    # 读取数据
                    df_yiche = None
                    df_autohome = None
                    
                    # 优先使用修复后的易车网数据
                    if st.session_state.fixed_yiche_df is not None:
                        df_yiche = st.session_state.fixed_yiche_df
                    elif yiche_file:
                        # 尝试多种编码读取CSV
                        try:
                            df_yiche = pd.read_csv(yiche_file, encoding='utf-8')
                        except:
                            try:
                                df_yiche = pd.read_csv(yiche_file, encoding='gbk')
                            except:
                                content = yiche_file.getvalue()
                                try:
                                    content_str = content.decode('utf-8-sig')
                                except:
                                    content_str = content.decode('utf-8', errors='ignore')
                                df_yiche = pd.read_csv(io.StringIO(content_str))
                    
                    # 读取汽车之家Excel
                    if autohome_file:
                        df_autohome = pd.read_excel(autohome_file)
                    
                    # 处理合并
                    if df_yiche is not None or df_autohome is not None:
                        df_result = process_merge(df_yiche, df_autohome, consultants, first_consultant)
                        
                        if df_result is not None:
                            # 保存到session state
                            st.session_state.df_merged = df_result
                            
                            # 显示处理日志
                            st.success(f"✅ 数据处理完成！共合并 {len(df_result)} 条记录")
                            
                            # 显示分配统计
                            st.subheader("销售顾问分配统计")
                            allocation_counts = {}
                            for consultant in selected_consultants:
                                count = len(df_result[df_result['销售顾问'] == consultant])
                                allocation_counts[consultant] = count
                                
                                # 获取单位
                                unit = get_consultant_unit(consultant)
                                st.write(f"**{consultant}** ({unit}): {count}条")
                            
                            # 检查分配均匀度
                            counts = list(allocation_counts.values())
                            if counts:
                                max_count = max(counts)
                                min_count = min(counts)
                                if max_count - min_count > 1:
                                    st.warning(f"⚠️ 分配不均匀，最大差值 {max_count - min_count}")
                                else:
                                    st.success(f"✓ 分配均匀，最大差值 {max_count - min_count}")
                    else:
                        st.error("没有可处理的数据文件")
                        
                except Exception as e:
                    st.error(f"处理失败: {str(e)}")
                    st.info("错误详情:")
                    st.code(str(e))
    else:
        st.info("请先上传需要处理的文件，并确保已选择至少一个销售顾问")

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
            
            # 车系统计
            car_stats = df['意向车系'].value_counts()
            st.metric("车型种类", len(car_stats))
            
            # 来源统计
            source_stats = df['线索来源'].value_counts()
            st.metric("来源渠道", len(source_stats))
            
            # 显示车系统计详情
            with st.expander("查看车系统计详情"):
                for car, count in car_stats.items():
                    st.write(f"{car}: {count}条")
            
        with col2:
            st.subheader("🔍 车系统计图表")
            if not df['意向车系'].empty:
                car_stats = df['意向车系'].value_counts()
                st.bar_chart(car_stats)
            
            # 显示前5大车型
            st.subheader("🏆 前5大车型")
            top5 = car_stats.head(5)
            for i, (car, count) in enumerate(top5.items(), 1):
                percentage = (count / len(df)) * 100
                st.write(f"{i}. {car}: {count}条 ({percentage:.1f}%)")
        
        # 显示线索来源统计
        st.subheader("📈 线索来源统计")
        col3, col4 = st.columns(2)
        
        with col3:
            if not df['线索来源'].empty:
                source_stats = df['线索来源'].value_counts()
                st.bar_chart(source_stats)
        
        with col4:
            with st.expander("查看来源统计详情"):
                for source, count in source_stats.items():
                    st.write(f"{source}: {count}条")
        
        # 显示销售顾问统计
        st.subheader("👥 销售顾问统计")
        consultant_stats = df['销售顾问'].value_counts()
        col5, col6 = st.columns(2)
        
        with col5:
            st.bar_chart(consultant_stats)
        
        with col6:
            with st.expander("查看销售顾问统计详情"):
                for consultant, count in consultant_stats.items():
                    unit = df[df['销售顾问'] == consultant]['单位'].iloc[0] if len(df[df['销售顾问'] == consultant]) > 0 else ""
                    st.write(f"{consultant} ({unit}): {count}条")
        
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
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        
        # 提供CSV格式下载
        csv_output = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📄 下载CSV文件",
            data=csv_output,
            file_name=f"CRS线索_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("请先处理数据以查看结果")

# 页脚
st.markdown("---")
st.caption("销售线索合并工具 v0.5.8 | 支持自定义映射规则和排除规则 | All by Eric & deepseek")