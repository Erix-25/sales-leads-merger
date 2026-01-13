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
if 'fixed_autohome_df' not in st.session_state:
    st.session_state.fixed_autohome_df = None

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
    help="上传需要修复格式的汽车之家CSV文件",
    key="autohome_original"
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
                st.session_state.fixed_autohome_df = fixed_df
                
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

# 2. 销售线索合并配置
st.sidebar.subheader("2. 合并配置")

# 文件上传部分
col1, col2 = st.sidebar.columns(2)

with col1:
    yiche_file = st.file_uploader("易车网文件", type=['xlsx', 'xls'], key="yiche_file")
    
with col2:
    autohome_file = st.file_uploader("汽车之家文件", type=['csv'], key="autohome_file")

# 销售顾问选择
st.sidebar.subheader("销售顾问分配")
consultants = {
    "陈婷": st.sidebar.checkbox("陈婷", value=True, key="chen_ting"),
    "张理平": st.sidebar.checkbox("张理平", value=True, key="zhang_liping"),
    "邵振艺": st.sidebar.checkbox("邵振艺", value=True, key="shao_zhenyi"),
    "耿佶": st.sidebar.checkbox("耿佶", value=True, key="geng_ji"),
    "翁佳跃": st.sidebar.checkbox("翁佳跃", value=False, key="weng_jiayue"),
    "陈杰": st.sidebar.checkbox("陈杰", value=False, key="chen_jie")
}

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

# 车系名称映射规则（从原脚本复制）
car_series_mapping = {
    r".*GL8.*陆尊.*": "GL8 豪华商务车",
    r".*GL8.*陆上公务舱.*": "GL8 陆上公务舱",
    r".*GL8.*陆尚.*": "GL8陆尚",
    r".*GL8.*Avenir.*": "GL8 Avenir",
    r".*GL8.*豪华商务车.*": "GL8 豪华商务车",
    r".*君越.*": "全新一代君越",
    r".*君威.*": "全新一代君威",
    r".*新君威.*": "全新一代君威",
    r".*昂科威Plus.*": "昂科威PLUS",
    r".*昂科威PLUS.*": "昂科威PLUS",
    r".*昂科威S.*": "昂科威S",
    r".*威朗.*": "威朗Pro",
    r".*微蓝6.*": "VELITE 6",
    r".*VELITE 6.*": "VELITE 6",
    r".*E5.*": "E 5",
    r".*E 5.*": "E 5",
    r".*世纪.*": "世纪",
    r".*至境.*": "至境世家",
    r".*昂科旗.*": "昂科威PLUS",
    r".*别克.*": "昂科威PLUS",
}

source_category_mapping = {
    "车商汇": "垂媒", "车商汇(集客号)": "垂媒", "车商汇（IM会话）": "垂媒", "车商汇（分期）": "垂媒", "车商汇（平台活动）": "垂媒",
    "智能产品（智能展厅）": "垂媒", "抖音": "自媒", "本地通-经销商号": "自媒", "本地通异地-经销商号": "自媒",
    "易车网": "垂媒", "汽车之家": "垂媒"
}

source_detail_mapping = {
    "车商汇": "汽车之家", "车商汇(集客号)": "汽车之家", "车商汇（IM会话）": "汽车之家", "车商汇（分期）": "汽车之家", "车商汇（平台活动）": "汽车之家",
    "智能产品（智能展厅）": "汽车之家", "抖音": "抖音", "本地通-经销商号": "抖音", "本地通异地-经销商号": "抖音",
    "易车网": "易车", "汽车之家": "汽车之家"
}

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
    if consultant_name in ["张理平", "邵振艺", "耿佶", "陈婷"]:
        return "上海安吉名流汽车服务有限公司"
    elif consultant_name in ["翁佳跃", "陈杰"]:
        return "安吉名流销售部"
    return ""

def normalize_car_series(car_series, default_value="昂科威PLUS", original_source=None):
    """标准化车系名称"""
    if pd.isna(car_series) or str(car_series).strip() == '':
        return default_value
    
    original = str(car_series).strip()
    
    for pattern, replacement in car_series_mapping.items():
        if re.search(pattern, original, re.IGNORECASE):
            return replacement
    
    return default_value

def map_source(source_value, mapping_dict, field_name="来源"):
    """映射来源字段"""
    if pd.isna(source_value):
        return "其他"
    
    source_str = str(source_value).strip()
    if not source_str:
        return "其他"
    
    # 尝试精确匹配
    if source_str in mapping_dict:
        return mapping_dict[source_str]
    
    # 尝试模糊匹配
    for key, value in mapping_dict.items():
        if key in source_str or source_str in key:
            return value
    
    return "其他"

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
    """处理合并逻辑"""
    results = []
    
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
            
            source_category = map_source(source, source_category_mapping, "来源分类")
            source_detail = map_source(source, source_detail_mapping, "线索来源")
            
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
                '跟进内容': '',
                # 注释掉原始车系和原始来源字段
                # '原始车系': str(original_car_series),
                # '原始来源': str(source)
            })
    
    # 处理汽车之家数据
    if df_autohome is not None:
        st.info(f"处理汽车之家数据: {len(df_autohome)} 条记录")
        for idx, row in df_autohome.iterrows():
            name = remove_after_slash(row.get('客户姓名', ''))
            phone = remove_after_slash(row.get('客户手机', ''))
            
            if pd.isna(name) or pd.isna(phone) or name == '' or phone == '':
                continue
            
            # 标准化车系
            original_car_series = row.get('意向车系', '')
            car_series = normalize_car_series(original_car_series, default_value="昂科威PLUS", original_source="汽车之家")
            
            # 来源信息
            bmd_source = row.get('BMD二级渠道', '')
            source_category = map_source(bmd_source, source_category_mapping, "来源分类")
            source_detail = map_source(bmd_source, source_detail_mapping, "线索来源")
            
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
                '跟进内容': '',
                # 注释掉原始车系和原始来源字段
                # '原始车系': str(original_car_series),
                # '原始来源': str(bmd_source)
            })
    
    # 合并结果
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
    
    # 确保数据列的顺序（去除不需要的列）
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
        st.subheader("易车网文件")
        if yiche_file:
            try:
                df_yiche = pd.read_excel(yiche_file)
                st.success(f"✅ 成功读取易车网文件，共 {len(df_yiche)} 条记录")
                st.dataframe(df_yiche.head(), use_container_width=True)
                
                # 显示列名
                with st.expander("查看文件列名"):
                    st.write("列名列表:", list(df_yiche.columns))
            except Exception as e:
                st.error(f"读取失败: {str(e)}")
        else:
            st.info("请上传易车网Excel文件")
    
    with col2:
        st.subheader("汽车之家文件")
        if autohome_file:
            try:
                # 尝试多种编码读取
                try:
                    df_autohome = pd.read_csv(autohome_file, encoding='utf-8')
                except:
                    try:
                        df_autohome = pd.read_csv(autohome_file, encoding='gbk')
                    except:
                        # 如果都不行，尝试读取原始字节并手动处理
                        content = autohome_file.getvalue()
                        try:
                            content_str = content.decode('utf-8-sig')
                        except:
                            content_str = content.decode('utf-8', errors='ignore')
                        
                        # 使用StringIO包装
                        df_autohome = pd.read_csv(io.StringIO(content_str))
                
                st.success(f"✅ 成功读取汽车之家文件，共 {len(df_autohome)} 条记录")
                st.dataframe(df_autohome.head(), use_container_width=True)
                
                # 显示列名
                with st.expander("查看文件列名"):
                    st.write("列名列表:", list(df_autohome.columns))
                    
            except Exception as e:
                st.error(f"读取失败: {str(e)}")
                st.info("建议先使用左侧的'文件格式修复'功能处理此文件")
        else:
            st.info("请上传汽车之家CSV文件")
    
    # 显示修复后的数据（如果存在）
    if st.session_state.fixed_autohome_df is not None:
        st.subheader("修复后的汽车之家数据")
        st.dataframe(st.session_state.fixed_autohome_df.head(), use_container_width=True)
        st.success(f"修复后的数据共 {len(st.session_state.fixed_autohome_df)} 条记录")

with tab2:
    st.header("数据处理")
    
    # 检查是否有选中的销售顾问
    if not selected_consultants:
        st.warning("⚠️ 请先在侧边栏选择至少一个销售顾问")
    
    # 检查是否上传了文件
    files_available = (yiche_file is not None) or (autohome_file is not None) or (st.session_state.fixed_autohome_df is not None)
    
    if files_available and selected_consultants:
        if st.button("🚀 开始合并处理", type="primary"):
            with st.spinner("正在处理数据..."):
                try:
                    # 读取数据
                    df_yiche = None
                    df_autohome = None
                    
                    if yiche_file:
                        df_yiche = pd.read_excel(yiche_file)
                    
                    # 优先使用修复后的数据
                    if st.session_state.fixed_autohome_df is not None:
                        df_autohome = st.session_state.fixed_autohome_df
                    elif autohome_file:
                        try:
                            df_autohome = pd.read_csv(autohome_file, encoding='utf-8')
                        except:
                            try:
                                df_autohome = pd.read_csv(autohome_file, encoding='gbk')
                            except:
                                content = autohome_file.getvalue()
                                content_str = content.decode('utf-8', errors='ignore')
                                df_autohome = pd.read_csv(io.StringIO(content_str))
                    
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
                                st.write(f"**{consultant}**: {count}条")
                            
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
st.caption("销售线索合并工具 v1.0 | 技术支持")