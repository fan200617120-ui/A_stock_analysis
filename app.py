# app.py - A股量化分析看板

import streamlit as st
import pandas as pd
from datetime import datetime
import time
from modules import data_processing, visualization, strategy, ai_prediction, report, data_entry, hotspot_scan

# ==========================
# 主题配置
# ==========================
def apply_theme(theme):
    """应用选定的主题"""
    if theme == "light":
        st.markdown("""
        <div data-theme="light">
        <style>
            @import url('assets/style.css');
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div data-theme="dark">
        <style>
            @import url('assets/style.css');
        </style>
        """, unsafe_allow_html=True)

# ==========================
# 缓存配置
# ==========================
@st.cache_data(ttl=3600)
def load_data_with_cache(uploaded_file):
    return data_processing.load_and_clean(uploaded_file)

@st.cache_data(ttl=1800)
def process_data_with_cache(df, time_range):
    df = data_processing.filter_non_trading_days(df)
    df = data_processing.filter_data_by_days(df, time_range)
    df = data_processing.validate_and_clean_data(df)
    return df

# ==========================
# 页面配置与全局样式
# ==========================

st.set_page_config(
    page_title="股海观澜 每日市相",
    page_icon="📈",
    layout="wide"
)

# 初始化session_state
if 'theme' not in st.session_state:
    st.session_state.theme = "dark"

# 应用主题
apply_theme(st.session_state.theme)

# ==========================
# 侧边栏配置
# ==========================
st.sidebar.markdown("### ⚙️ 分析设置")

# ==========================
# 主页面标题
# ==========================
st.markdown("<h1 style='font-size: 36px; color: #800020;'>📈 股海观澜 每日市相</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='color: #800020;'>盘前预报 盘中察势 盘后悟道 | 投资有风险 决策需谨慎</h3>", unsafe_allow_html=True)
st.markdown("---")

# 主题切换
current_theme = st.sidebar.radio(
    "主题选择",
    ["暗色模式", "亮色模式"],
    index=0 if st.session_state.theme == "dark" else 1,
    key="theme_selector_unique"
)

# 更新主题
if current_theme == "亮色模式":
    new_theme = "light"
else:
    new_theme = "dark"

# 如果主题发生变化，更新并重新运行
if new_theme != st.session_state.theme:
    st.session_state.theme = new_theme
    st.rerun()

# 时间范围选择
time_range = st.sidebar.selectbox(
    "选择分析时间范围",
    ["最近5天", "最近10天", "最近20天", "最近30天", "全部数据"],
    index=1,
    key="time_range_selector"
)

# 自动刷新设置
st.sidebar.markdown("### 🔄 自动刷新")
auto_refresh = st.sidebar.checkbox("启用自动刷新", value=False, key="auto_refresh_checkbox")
if auto_refresh:
    refresh_interval = st.sidebar.selectbox(
        "刷新间隔",
        [30, 60, 300],
        index=1,
        format_func=lambda x: f"{x}秒" if x < 60 else f"{x//60}分钟",
        key="refresh_interval_selector"
    )

# ==========================
# 文件上传
# ==========================
uploaded_file = st.sidebar.file_uploader("上传Excel数据文件", type=["xlsx", "xls"], key="file_uploader")
if not uploaded_file:
    st.info("👆 请上传包含市场数据的Excel文件以开始分析")
    st.stop()

# ==========================
# 数据加载与清洗（带缓存）
# ==========================
with st.spinner("数据加载与清洗中..."):
    df = load_data_with_cache(uploaded_file)

if df is None or df.empty:
    st.error("❌ 数据加载失败，请检查文件格式。")
    st.info("""
    💡 **可能的原因：**
    - 文件格式不正确
    - 数据表不在第一个sheet
    - 日期格式无法识别
    - 文件包含复杂的公式
    """)
    st.stop()

# 数据处理（带缓存）
df = process_data_with_cache(df, time_range)

# ==========================
# 数据质量监控
# ==========================
data_processing.add_data_quality_monitor(df)

# ==========================
# 关键指标概览
# ==========================

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(" 交易天数", len(df), delta=None)

with col2:
    total_value = data_processing.safe_get_value(df, '全天总额', 0)
    st.metric(" 全天总额", f"{total_value:,.0f}")

with col3:
    diff_value = data_processing.safe_get_value(df, '今昨差额', 0)
    st.metric("今昨差额", f"{diff_value:,.0f}")  # 移除了 delta 参数

with col4:
    north_value = data_processing.safe_get_value(df, '北向净值', 0)
    st.metric("北向净流入", f"{north_value:,.0f}亿")  # 移除了 delta 参数
    
with col5:
    limit_up = data_processing.safe_get_value(df, '全天涨停', 0)
    st.metric(" 涨停家数", f"{limit_up}家")

with col6:
    board_rate = data_processing.safe_get_value(df, '全天封板率', 0)
    if board_rate > 1:  # 如果封板率是百分比形式
        board_rate = board_rate / 100
    st.metric(" 封板率", f"{board_rate:.1%}")

# ==========================
# 市场深度洞察 - 高级分析
# ==========================
with st.expander("🔍 市场深度洞察 (技术信号 | 资金轮动 | 市场节奏)", expanded=False):
    
    # 第一行：技术信号
    st.markdown("####  技术信号分析")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # 量价关系信号
        if '全天总额' in df.columns and len(df) >= 5:
            current_volume = df['全天总额'].iloc[-1]
            volume_ma5 = df['全天总额'].tail(5).mean()
            volume_trend = "放量" if current_volume > volume_ma5 else "缩量"
            
            # 简单的价格趋势判断（假设有涨跌数据）
            if '上涨' in df.columns and '下跌' in df.columns:
                advance_ratio = df['上涨'].iloc[-1] / (df['下跌'].iloc[-1] + 1)
                price_trend = "上涨" if advance_ratio > 1.2 else "下跌" if advance_ratio < 0.8 else "震荡"
                
                # 量价配合分析
                if volume_trend == "放量" and price_trend == "上涨":
                    signal = "🔴 量价齐升"
                    color = "#10b981"
                elif volume_trend == "缩量" and price_trend == "下跌":
                    signal = "🔴 缩量调整"
                    color = "#6b7280"
                elif volume_trend == "放量" and price_trend == "下跌":
                    signal = "⚠️ 放量下跌"
                    color = "#ef4444"
                elif volume_trend == "缩量" and price_trend == "上涨":
                    signal = "⚠️ 缩量上涨"
                    color = "#f59e0b"
                else:
                    signal = "➖ 量价背离"
                    color = "#8b5cf6"
                
                st.markdown(f'<div style="background-color: {color}; color: white; padding: 0.5rem; border-radius: 0.5rem; text-align: center; font-weight: bold;">{signal}</div>', unsafe_allow_html=True)
                st.caption(f"{volume_trend} | {price_trend}")
    
    with col2:
        # 北向资金聪明钱信号
        if '北向净值' in df.columns and len(df) >= 3:
            recent_north = df['北向净值'].tail(3)
            north_trend = "持续流入" if all(x > 0 for x in recent_north) else \
                         "持续流出" if all(x < 0 for x in recent_north) else \
                         "震荡"
            
            current_north = df['北向净值'].iloc[-1]
            if north_trend == "持续流入" and current_north > 20:
                signal = "💰 聪明钱进场"
                color = "#10b981"
            elif north_trend == "持续流出" and current_north < -20:
                signal = "💸 聪明钱离场"
                color = "#ef4444"
            else:
                signal = "💼 外资观望"
                color = "#6b7280"
            
            st.markdown(f'<div style="background-color: {color}; color: white; padding: 0.5rem; border-radius: 0.5rem; text-align: center; font-weight: bold;">{signal}</div>', unsafe_allow_html=True)
            st.caption(f"北向: {north_trend}")
    
    with col3:
        # 市场情绪极端化信号
        if '全天涨停' in df.columns and '全天跌停' in df.columns:
            limit_up = df['全天涨停'].iloc[-1]
            limit_down = df['全天跌停'].iloc[-1]
            
            if limit_up > 80 and limit_down < 10:
                signal = "🔥 情绪狂热"
                color = "#ef4444"
            elif limit_down > 30 and limit_up < 20:
                signal = "❄️ 情绪冰点"
                color = "#3b82f6"
            elif limit_up > limit_down * 3:
                signal = "😊 情绪乐观"
                color = "#f59e0b"
            elif limit_down > limit_up * 2:
                signal = "😟 情绪悲观"
                color = "#8b5cf6"
            else:
                signal = "😐 情绪平稳"
                color = "#6b7280"
            
            st.markdown(f'<div style="background-color: {color}; color: white; padding: 0.5rem; border-radius: 0.5rem; text-align: center; font-weight: bold;">{signal}</div>', unsafe_allow_html=True)
            st.caption(f"涨:{limit_up} 跌:{limit_down}")
    
    with col4:
        # 封板质量信号
        if '全天封板率' in df.columns:
            board_rate = df['全天封板率'].iloc[-1]
            if board_rate > 0.8:
                signal = "🎯 封板质量高"
                color = "#10b981"
            elif board_rate > 0.6:
                signal = "✅ 封板质量良好"
                color = "#f59e0b"
            elif board_rate > 0.4:
                signal = "⚠️ 封板质量一般"
                color = "#ef4444"
            else:
                signal = "❌ 封板质量差"
                color = "#dc2626"
            
            st.markdown(f'<div style="background-color: {color}; color: white; padding: 0.5rem; border-radius: 0.5rem; text-align: center; font-weight: bold;">{signal}</div>', unsafe_allow_html=True)
            st.caption(f"封板率: {board_rate:.1%}")
    
    # 第二行：资金轮动分析
    st.markdown("####  资金轮动分析")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 板块资金偏好
        st.markdown("**板块资金偏好**")
        if '主板涨停数' in df.columns and '创业板涨停数' in df.columns:
            main_board = df['主板涨停数'].iloc[-1]
            gem_board = df['创业板涨停数'].iloc[-1]
            
            if main_board > gem_board * 2:
                st.success("📊 偏好主板")
                st.caption(f"主板:{main_board} 创业板:{gem_board}")
            elif gem_board > main_board * 1.5:
                st.info("💡 偏好创业板")
                st.caption(f"主板:{main_board} 创业板:{gem_board}")
            else:
                st.warning("⚖️ 板块均衡")
                st.caption(f"主板:{main_board} 创业板:{gem_board}")
    
    with col2:
        # 市场风格判断
        st.markdown("**市场风格判断**")
        if '上涨' in df.columns and '全天涨停' in df.columns:
            advance_count = df['上涨'].iloc[-1]
            limit_up_count = df['全天涨停'].iloc[-1]
            
            concentration = limit_up_count / (advance_count + 1) * 100
            
            if concentration > 5:
                st.error("🎯 龙头抱团")
                st.caption(f"集中度: {concentration:.1f}%")
            elif concentration > 2:
                st.warning("🌟 局部热点")
                st.caption(f"集中度: {concentration:.1f}%")
            else:
                st.success("🌊 普涨格局")
                st.caption(f"集中度: {concentration:.1f}%")
    
    with col3:
        # 资金效率分析
        st.markdown("**资金使用效率**")
        if '全天总额' in df.columns and '全天涨停' in df.columns:
            volume_per_limit = df['全天总额'].iloc[-1] / (df['全天涨停'].iloc[-1] + 1)
            
            if volume_per_limit < 200:  # 假设单位是亿
                st.success("💰 资金效率高")
                st.caption("少量资金推动多个涨停")
            elif volume_per_limit < 500:
                st.info("💵 资金效率正常")
                st.caption("资金与涨停匹配")
            else:
                st.warning("💸 资金效率低")
                st.caption("大量资金推动较少涨停")
    
    # 第三行：市场节奏建议
    st.markdown("#### 🎵 市场节奏建议")
    
    # 综合节奏判断
    recommendations = []
    
    # 基于量价关系
    if '全天总额' in df.columns and len(df) >= 5:
        volume_change = (df['全天总额'].iloc[-1] - df['全天总额'].tail(5).mean()) / df['全天总额'].tail(5).mean()
        if volume_change > 0.15:
            recommendations.append("📈 适合顺势而为")
        elif volume_change < -0.15:
            recommendations.append("🛑 建议观望等待")
    
    # 基于北向资金
    if '北向净值' in df.columns:
        if df['北向净值'].iloc[-1] > 30:
            recommendations.append("👑 跟随聪明钱")
        elif df['北向净值'].iloc[-1] < -20:
            recommendations.append("🚫 警惕外资流出")
    
    # 基于市场情绪
    if '全天涨停' in df.columns:
        if df['全天涨停'].iloc[-1] > 60:
            recommendations.append("🎯 聚焦主线龙头")
        elif df['全天涨停'].iloc[-1] < 20:
            recommendations.append("💤 保持耐心")

    # 第四行：涨停板市值分布解读
    st.markdown("#### 💰 涨停板市值分布解读")
    
    # 检查市值分布数据
    full_capital_columns = ['涨停板>100亿(全天）', '50亿<涨停板<100亿(全天）', '20亿<涨停板<50亿(全天）', '涨停板<20亿(全天）']
    available_full = any(col in df.columns for col in full_capital_columns)
    
    if available_full and len(df) > 0:
        latest_data = df.iloc[-1]
        
        # 获取最新市值分布数据
        large_cap = latest_data.get('涨停板>100亿(全天）', 0)
        mid_large_cap = latest_data.get('50亿<涨停板<100亿(全天）', 0)
        mid_small_cap = latest_data.get('20亿<涨停板<50亿(全天）', 0)
        small_cap = latest_data.get('涨停板<20亿(全天）', 0)
        
        total_capital = large_cap + mid_large_cap + mid_small_cap + small_cap
        
        if total_capital > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                large_ratio = large_cap / total_capital
                if large_ratio > 0.4:
                    st.success("🏢 大盘股主导")
                    st.caption(f"超大市值占比{large_ratio:.1%}")
                else:
                    st.info("🏢 大盘股参与")
                    st.caption(f"超大市值占比{large_ratio:.1%}")
            
            with col2:
                mid_large_ratio = mid_large_cap / total_capital
                if mid_large_ratio > 0.3:
                    st.success("🏛️ 中大盘活跃")
                    st.caption(f"中大盘占比{mid_large_ratio:.1%}")
                else:
                    st.info("🏛️ 中大盘一般")
                    st.caption(f"中大盘占比{mid_large_ratio:.1%}")
            
            with col3:
                mid_small_ratio = mid_small_cap / total_capital
                if mid_small_ratio > 0.4:
                    st.success("🏠 中小盘主导")
                    st.caption(f"中小盘占比{mid_small_ratio:.1%}")
                else:
                    st.info("🏠 中小盘一般")
                    st.caption(f"中小盘占比{mid_small_ratio:.1%}")
            
            with col4:
                small_ratio = small_cap / total_capital
                if small_ratio > 0.5:
                    st.success("💎 小盘股狂热")
                    st.caption(f"小盘股占比{small_ratio:.1%}")
                else:
                    st.info("💎 小盘股正常")
                    st.caption(f"小盘股占比{small_ratio:.1%}")
            
            # 综合解读
            max_ratio = max(large_ratio, mid_large_ratio, mid_small_ratio, small_ratio)
            if max_ratio == large_ratio and large_ratio > 0.4:
                st.info("📈 **风格判断**: 大盘股行情，资金偏好龙头蓝筹，稳健型机会")
            elif max_ratio == mid_large_ratio and mid_large_ratio > 0.35:
                st.info("📈 **风格判断**: 中大盘股活跃，二线蓝筹受青睐，均衡配置")
            elif max_ratio == mid_small_ratio and mid_small_ratio > 0.4:
                st.info("📈 **风格判断**: 中小盘股主导，成长性机会较多，适度积极")
            elif max_ratio == small_ratio and small_ratio > 0.5:
                st.info("📈 **风格判断**: 小盘股狂热，题材炒作活跃，注意风险控制")
            else:
                st.info("📈 **风格判断**: 市值分布均衡，各类风格均有表现")
        else:
            st.info("📊 当日无涨停板市值分布数据")
    else:
        st.info("📊 暂无涨停板市值分布数据可用于分析")
    
    # 显示建议
    if recommendations:
        for rec in recommendations:
            st.write(f"- {rec}")
    else:
        st.info("📊 市场节奏平稳，均衡配置")

# ==========================
# 智能预警系统
# ==========================
st.markdown("###  智能预警系统")
alerts = data_processing.create_trading_alerts(df)

if alerts:
    for alert in alerts:
        if alert["type"] == "warning":
            st.warning(f"{alert['message']} - {alert['value']}")
        elif alert["type"] == "success":
            st.success(f"{alert['message']} - {alert['value']}")
        else:
            st.info(f"{alert['message']} - {alert['value']}")
else:
    st.info("✅ 当前市场指标处于正常范围内，无异常预警")
    

# ==========================
# 重新排列的Tab布局 - 更合理的用户流程
# ==========================

tabs = st.tabs([
    " 核心分析面板",      # 0 - 主要分析界面
    " 热点扫描",          # 1 - 实时热点分析
    " 智能报告",          # 2 - 报告生成
    " 详细分析",          # 3 - 详细数据
    " AI预测中心",        # 4 - AI功能
    " 策略回测",          # 5 - 策略测试    
    " 数据录入"           # 6 - 数据管理
])

# Tab 1: 核心分析面板
with tabs[0]:
    st.markdown('<div class="section-header"> 市场核心分析面板</div>', unsafe_allow_html=True)
    
    # 使用expander组织内容
    with st.expander(" 资金流向分析", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            fig_north = visualization.create_professional_line_chart(
                df, ['北向成交额', '北向净值'], 
                '北向资金流向分析', ['#7c3aed', '#06b6d4']
            )
            st.plotly_chart(fig_north, use_container_width=True)
        
        with col2:
            fig_index_open = visualization.create_index_open_chart(df)
            st.plotly_chart(fig_index_open, use_container_width=True)
        
        # 两融数据分析
        col1, col2 = st.columns(2)
        with col1:
            if '两融资余额' in df.columns:
                fig_margin_balance = visualization.create_margin_balance_chart(df)
                st.plotly_chart(fig_margin_balance, use_container_width=True)
            else:
                st.info("数据中暂无两融资余额信息")
        
        with col2:
            if '融资净买入' in df.columns:
                fig_margin_net = visualization.create_margin_net_chart(df)
                st.plotly_chart(fig_margin_net, use_container_width=True)
            else:
                st.info("数据中暂无融资净买入信息")

    with st.expander(" 市场成交趋势分析", expanded=True):
        # 市场总额与今昨差分析
        col1, col2 = st.columns(2)
        with col1:
            # 改为堆叠柱状图
            fig_total = visualization.create_stacked_daily_chart(df, '上午总额', '全天总额', '市场总成交额构成')
            if fig_total:
                st.plotly_chart(fig_total, use_container_width=True)
        
        with col2:
            fig_diff = visualization.create_daily_diff_chart(df)
            if fig_diff:
                st.plotly_chart(fig_diff, use_container_width=True)
        
        # 各市场成交趋势
        st.markdown("#### 各市场成交细分")
        col1, col2 = st.columns(2)
        with col1:
            # 改为堆叠柱状图
            fig_sh = visualization.create_stacked_daily_chart(df, '沪额上午', '沪额全天', '沪市成交额构成')
            if fig_sh:
                st.plotly_chart(fig_sh, use_container_width=True)
        
        with col2:
            # 改为堆叠柱状图
            fig_sz = visualization.create_stacked_daily_chart(df, '深综上午', '深综全天', '深市成交额构成')
            if fig_sz:
                st.plotly_chart(fig_sz, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            # 改为堆叠柱状图
            fig_cy = visualization.create_stacked_daily_chart(df, '创额上午', '创额全天', '创业板成交额构成')
            if fig_cy:
                st.plotly_chart(fig_cy, use_container_width=True)
        
        with col2:
            fig_index = visualization.create_index_turnover_chart(df)
            st.plotly_chart(fig_index, use_container_width=True)

    with st.expander(" 涨跌停与市场情绪分析", expanded=True):
        # 市场情绪分析
        col1, col2 = st.columns(2)
        with col1:
            fig_up_down_flat = visualization.create_up_down_flat_chart(df)
            if fig_up_down_flat:
                st.plotly_chart(fig_up_down_flat, use_container_width=True)
        
        with col2:
            fig_board_rate = visualization.create_professional_line_chart(df, ['全天封板率'], '市场封板率趋势', ['#f97316'])
            st.plotly_chart(fig_board_rate, use_container_width=True)
        
        # 涨停跌停与大幅波动分析
        st.markdown("#### 涨停跌停与大幅波动分析")
        col1, col2 = st.columns(2)
        with col1:
            fig_four_line = visualization.create_four_line_chart(df)
            if fig_four_line:
                st.plotly_chart(fig_four_line, use_container_width=True)
        
        with col2:
            fig_limit_down = visualization.create_limit_down_chart(df)
            if fig_limit_down:
                st.plotly_chart(fig_limit_down, use_container_width=True)
        
        # 涨停板深度分析
        st.markdown("#### 涨停板深度分析")
        col1, col2 = st.columns(2)
        with col1:
            fig_full_limit = visualization.create_professional_line_chart(
                df, ['主板涨停数', '创业板涨停数', '北证涨停数'], 
                '板块全天涨停板', ['#e11d48', '#f97316', '#7c3aed']
            )
            st.plotly_chart(fig_full_limit, use_container_width=True)
        
        with col2:
            fig_limit_chain_enhanced = visualization.create_enhanced_limit_up_analysis_chart(df)
            st.plotly_chart(fig_limit_chain_enhanced, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            fig_morning_limit = visualization.create_morning_limit_up_chart(df)
            if fig_morning_limit:
                st.plotly_chart(fig_morning_limit, use_container_width=True)
        
        with col2:
            fig_volatility = visualization.create_professional_line_chart(
                df, ['涨幅大于10%', '跌幅于大于10%'], 
                '大幅波动股票数量', ['#e11d48', '#16a34a']
            )
            st.plotly_chart(fig_volatility, use_container_width=True)

    # ==================== 涨停板市值分布分析（仅在此Tab显示） ====================
    with st.expander(" 涨停板市值分布分析", expanded=True):
        # 检查数据中是否有这些列
        morning_capital_columns = ['涨停板>100亿(上午）', '50亿<涨停板<100亿(上午）', '20亿<涨停板<50亿(上午）', '涨停板<20亿(上午）']
        full_capital_columns = ['涨停板>100亿(全天）', '50亿<涨停板<100亿(全天）', '20亿<涨停板<50亿(全天）', '涨停板<20亿(全天）']

        available_morning = any(col in df.columns for col in morning_capital_columns)
        available_full = any(col in df.columns for col in full_capital_columns)

        if available_morning or available_full:
            # 上排：全天数据
            st.markdown("**全天数据**")
            col1, col2 = st.columns(2)
            
            with col1:
                # 全天涨停市值柱图+折线图
                if available_full:
                    fig_full_capital = visualization.create_full_limit_up_capital_chart(df)
                    st.plotly_chart(fig_full_capital, use_container_width=True)
                else:
                    st.info("📊 数据中暂无全天涨停板市值分布信息")
                    
            with col2:
                # 全天涨停折线图
                if available_full:
                    fig_full_trend = visualization.create_full_limit_up_capital_trend_chart(df)
                    st.plotly_chart(fig_full_trend, use_container_width=True)
                else:
                    st.info("📊 数据中暂无全天涨停板市值分布信息")
            
            # 下排：上午数据和对比数据
            st.markdown("**上午数据与对比**")
            col1, col2 = st.columns(2)
            
            with col1:
                # 上午涨停分布柱图+折线图
                if available_morning:
                    fig_morning_capital = visualization.create_morning_limit_up_capital_chart(df)
                    st.plotly_chart(fig_morning_capital, use_container_width=True)
                else:
                    st.info("📊 数据中暂无上午涨停板市值分布信息")
                    
            with col2:
                # 全天vs上午对比图
                if available_full and available_morning:
                    fig_comparison = visualization.create_limit_up_capital_comparison_chart(df)
                    st.plotly_chart(fig_comparison, use_container_width=True)
                else:
                    st.info("📊 需要同时有全天和上午数据才能显示对比图")
            
            # 添加市值分布说明
            st.markdown("""
            ** 市值分布说明：(自由流通市值）**
            - 🔴 **>100亿**: 超大市值涨停，通常为大蓝筹或行业龙头
            - 🟠 **50-100亿**: 大市值涨停，多为二线蓝筹或细分龙头  
            - 🟣 **20-50亿**: 中市值涨停，活跃的中小盘股
            - 🔵 **<20亿**: 小市值涨停，通常为题材炒作或次新股
            """)
        else:
            st.info("📊 数据中暂无涨停板市值分布信息")

# Tab 2: 热点扫描
with tabs[1]:
    # 热点扫描 - 使用外挂模块
    hotspot_scan.show_hotspot_scan(df, uploaded_file, load_data_with_cache)

# Tab 3: 智能报告
with tabs[2]:
    st.markdown('<div class="section-header"> 每日市场智能报告</div>', unsafe_allow_html=True)
    report.show_daily_report(df)

# Tab 4: 详细分析
with tabs[3]:
    st.markdown('<div class="section-header"> 详细数据分析</div>', unsafe_allow_html=True)
    visualization.show_detailed_analysis(df)

# Tab 5: AI预测中心
with tabs[4]:
    st.markdown('<div class="section-header"> AI智能预测中心</div>', unsafe_allow_html=True)
    
    # AI预测中心主函数调用
    ai_prediction.show_ai_prediction_dashboard(df)

# Tab 6: 策略回测
with tabs[5]:
    st.markdown('<div class="section-header"> 策略回测分析中心</div>', unsafe_allow_html=True)
    strategy.show_backtest_dashboard(df)

# Tab 7: 数据录入
with tabs[6]:
    st.markdown('<div class="section-header"> 数据录入与管理</div>', unsafe_allow_html=True)
    
    # 数据录入表单
    new_data = data_entry.show_data_entry_form()
    
    if new_data:
        # 数据验证和处理
        success = data_entry.save_new_data(df, new_data, uploaded_file)
        if success:
            st.success("✅ 数据保存成功！")
            st.info("💡 请重新上传更新后的文件以查看最新数据")
            
    # 数据管理功能
    st.markdown("---")
    st.markdown("### 🔄 数据管理")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 重新加载数据", use_container_width=True, key="reload_data_button"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        if st.button("🗑️ 清除所有缓存", use_container_width=True, key="clear_all_cache_button"):
            st.cache_data.clear()
            st.success("缓存已清除！")

# ==========================
# 数据导出功能
# ==========================
st.sidebar.markdown("---")
st.sidebar.markdown("### 📤 数据导出")

# 导出选项
export_type = st.sidebar.radio(
    "导出内容:",
    ["📊 当前视图数据", "📈 技术分析报告", "📋 完整数据集"],
    index=0,
    key="export_type_selector_unique"
)

# 导出按钮
if st.sidebar.button("📥 生成Excel文件", type="primary", key="export_button_unique"):
    with st.sidebar:
        with st.spinner("正在生成Excel文件..."):
            excel_data = data_processing.export_to_excel(df, export_type)
            
            if excel_data:
                st.success("✅ Excel文件生成完成！")
                
                # 下载按钮
                st.download_button(
                    label="💾 下载Excel文件",
                    data=excel_data,
                    file_name=f"A股分析报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.ms-excel",
                    use_container_width=True,
                    key="download_button_unique"
                )

# ==========================
# 侧边栏功能
# ==========================

# 清空缓存按钮
if st.sidebar.button("🗑️ 清空数据缓存", type="secondary", key="clear_cache_button_unique"):
    st.cache_data.clear()
    st.sidebar.success("缓存已清空！")
    st.rerun()

# 自动刷新逻辑
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()

st.caption("© 2025 股海观澜 每日市相 Version 1.7.8 | 盘前预报 盘中察势 盘后悟道 | 投资有风险 决策需谨慎")