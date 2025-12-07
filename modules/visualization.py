# visualization.py - 完整版（支持亮/暗主题自动适配）
# 功能：与 app.py 的主题切换兼容，所有图表自动响应 st.session_state.theme
# ------------------------------

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ==========================
# 1. 动态主题适配
# ==========================

def get_plot_style():
    """根据当前主题返回 Plotly 样式"""
    theme = st.session_state.get("theme", "dark")
    if theme == "light":
        return {
            "title_color": "#1e293b",
            "axis_color": "#334155",
            "grid_color": "#e2e8f0",
            "line_color": "#94a3b8",
            "plot_bgcolor": "#ffffff",
            "paper_bgcolor": "#ffffff",
            "legend_bg": "rgba(255,255,255,0.5)"
        }
    else:
        return {
            "title_color": "#ffffff",
            "axis_color": "#e2e8f0",
            "grid_color": "#334155",
            "line_color": "#475569",
            "plot_bgcolor": "#0f172a",
            "paper_bgcolor": "#0f172a",
            "legend_bg": "rgba(30,41,59,0.8)"
        }

PLOTLY_CONFIG = {
    "scrollZoom": True,
    "displayModeBar": "hover",
    "toImageButtonOptions": {"format": "png", "filename": "chart"},
    "modeBarButtonsToRemove": ["zoom2d", "pan2d"]
}

def find_column(df, target_column):
    """容错匹配列名"""
    if target_column in df.columns:
        return target_column
    variants = [
        target_column,
        target_column.replace('（', '(').replace('）', ')'),
        target_column.replace('(', '（').replace(')', '）'),
        target_column.replace(' ', '')
    ]
    for v in variants:
        if v in df.columns:
            return v
    for col in df.columns:
        if target_column.replace('(', '').replace(')', '') in col:
            return col
    return None

# ==========================
# 2. 基础图表函数
# ==========================

def create_grouped_bar_chart(df, am_column, full_column, title):
    """分组柱状图：上午 vs 全天"""
    style = get_plot_style()
    am_actual = find_column(df, am_column)
    full_actual = find_column(df, full_column)
    
    if not am_actual or not full_actual:
        return None
        
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)
    
    fig = go.Figure()
    
    # 上午数据（橙色）
    fig.add_trace(go.Bar(
        x=df.index, y=df[am_actual].fillna(0),
        name='上午', marker_color='#f97316', opacity=0.9, width=0.4,
        hovertemplate=f'<b>上午 {am_actual}</b><br>日期: %{{customdata}}<br>数值: %{{y:,.0f}}<extra></extra>',
        customdata=df['日期_str']
    ))
    
    # 全天数据（红色）
    fig.add_trace(go.Bar(
        x=df.index, y=df[full_actual].fillna(0),
        name='全天', marker_color='#dc2626', opacity=0.9, width=0.4,
        hovertemplate=f'<b>全天 {full_actual}</b><br>日期: %{{customdata}}<br>数值: %{{y:,.0f}}<extra></extra>',
        customdata=df['日期_str']
    ))
    
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16, color=style["title_color"])),
        barmode='group', height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            title='日期', tickvals=df.index, ticktext=df['日期_str'], type='category',
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='金额', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    return fig

# 成交额柱子
def create_stacked_daily_chart(df, am_column, full_column, title):
    style = get_plot_style()
    am_actual  = find_column(df, am_column)
    full_actual = find_column(df, full_column)
    if not am_actual or not full_actual:
        return None

    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)

    am_data  = df[am_actual].fillna(0)
    full_data = df[full_actual].fillna(0)
    pm_data  = (full_data - am_data).clip(lower=0)

    fig = go.Figure()

    # 上午柱
    fig.add_trace(go.Bar(x=df.index, y=am_data, name='上午',
                         marker_color='#f97316', opacity=0.9, width=0.4,
                         hovertemplate='上午<br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
                         customdata=df['日期_str']))

    # 下午柱
    fig.add_trace(go.Bar(x=df.index, y=pm_data, name='下午',
                         marker_color='#dc2626', opacity=0.9, width=0.4,
                         hovertemplate='下午<br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
                         customdata=df['日期_str']))

       # 全天折线：总成交额用湖蓝，其余按市场
    if '总额' in full_actual and '全天' in full_actual:      # ← 关键判断
        line_color = '#06b6d4'      # 湖蓝色
    else:
        line_color = '#e11d48' if '沪' in full_actual else \
                     '#f97316' if '深' in full_actual else \
                     '#7c3aed'      # 创业/创额
    fig.add_trace(go.Scatter(
        x=df.index, y=full_data,
        mode='lines+markers', name='全天',
        line=dict(color=line_color, width=1.5),
        marker=dict(size=4, color=line_color),
        hovertemplate='全天<br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
        customdata=df['日期_str']
    ))

    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(color=style["title_color"], size=16)),
        barmode='stack', height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(type='category', tickvals=df.index, ticktext=df['日期_str'],
                   gridcolor=style["grid_color"], linecolor=style["line_color"],
                   tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])),
        yaxis=dict(title='金额', gridcolor=style["grid_color"], linecolor=style["line_color"],
                   tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                    bgcolor=style["legend_bg"], font=dict(color=style["axis_color"]))
    )
    return fig

def create_professional_line_chart(df, columns, title, colors=None):
    """专业折线图"""
    style = get_plot_style()
    if colors is None:
        colors = ['#e11d48', '#f97316', '#7c3aed', '#06b6d4', '#10b981']

    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)
    fig = go.Figure()

    for i, col in enumerate(columns):
        actual_col = find_column(df, col)
        if actual_col:
            data = df[actual_col].fillna(0)
            hover_template = f'<b>{actual_col}</b><br>日期: %{{customdata}}<br>数值: %{{y:,.0f}}<extra></extra>'
            if '封板率' in actual_col:
                hover_template = f'<b>{actual_col}</b><br>日期: %{{customdata}}<br>数值: %{{y:.1%}}<extra></extra>'
            
            fig.add_trace(go.Scatter(
                x=df.index, y=data, mode='lines+markers', name=actual_col,
                line=dict(color=colors[i % len(colors)], width=3), marker=dict(size=6),
                hovertemplate=hover_template, customdata=df['日期_str']
            ))

    yaxis_title = '数值'
    yaxis_tickformat = ',.0f'
    if any('封板率' in col for col in columns if find_column(df, col)):
        yaxis_title = '百分比'
        yaxis_tickformat = '.0%'

    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16, color=style["title_color"])),
        height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title=yaxis_title, gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"]),
            tickformat=yaxis_tickformat
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    return fig

# ==========================
# 3. 涨停板市值分布与趋势
# ==========================

def create_full_limit_up_capital_chart(df):
    """全天涨停板市值分布：只保留堆叠柱状图"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)

    columns_map = {
        '涨停板>100亿(全天）': '#e11d48',
        '50亿<涨停板<100亿(全天）': '#f97316',
        '20亿<涨停板<50亿(全天）': '#7c3aed',
        '涨停板<20亿(全天）': '#06b6d4'
    }

    fig = go.Figure()
    # 只保留柱状部分，删除趋势线部分
    for col, color in columns_map.items():
        actual = find_column(df, col)
        if actual:
            fig.add_trace(go.Bar(
                x=df.index, y=df[actual].fillna(0),
                name=col.replace('(全天）', ''),
                marker_color=color, opacity=0.8, width=0.4,
                hovertemplate=f'<b>{col.replace("(全天）", "")}</b><br>日期: %{{customdata}}<br>数量: %{{y:,.0f}}<extra></extra>',
                customdata=df['日期_str']
            ))

    fig.update_layout(
        title=dict(text='全天涨停板市值分布', x=0.5,  # 修改标题
                   font=dict(size=14, color=style["title_color"])),
        barmode='stack', height=420, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='涨停数量', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(size=10, color=style["axis_color"])
        )
    )
    return fig

def create_morning_limit_up_capital_chart(df):
    """上午涨停板市值分布：只保留堆叠柱状图"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)

    columns_map = {
        '涨停板>100亿(上午）': '#e11d48',
        '50亿<涨停板<100亿(上午）': '#f97316',
        '20亿<涨停板<50亿(上午）': '#7c3aed',
        '涨停板<20亿(上午）': '#06b6d4'
    }

    fig = go.Figure()
    # 只保留柱状部分，删除趋势线部分
    for col, color in columns_map.items():
        actual = find_column(df, col)
        if actual:
            fig.add_trace(go.Bar(
                x=df.index, y=df[actual].fillna(0),
                name=col.replace('(上午）', ''),
                marker_color=color, opacity=0.8, width=0.4,
                hovertemplate=f'<b>{col.replace("(上午）", "")}</b><br>日期: %{{customdata}}<br>数量: %{{y:,.0f}}<extra></extra>',
                customdata=df['日期_str']
            ))

    fig.update_layout(
        title=dict(text='上午涨停板市值分布', x=0.5,  # 修改标题
                   font=dict(size=14, color=style["title_color"])),
        barmode='stack', height=420, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='涨停数量', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(size=10, color=style["axis_color"])
        )
    )
    return fig

def create_full_limit_up_capital_trend_chart(df):
    """全天涨停板市值分布趋势（折线）"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)

    columns_map = {
        '涨停板>100亿(全天）': '#e11d48',
        '50亿<涨停板<100亿(全天）': '#f97316',
        '20亿<涨停板<50亿(全天）': '#7c3aed',
        '涨停板<20亿(全天）': '#06b6d4'
    }

    fig = go.Figure()
    for col, color in columns_map.items():
        actual = find_column(df, col)
        if actual:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[actual].fillna(0),
                mode='lines+markers', name=col.replace('(全天）', ''),
                line=dict(color=color, width=3), marker=dict(size=6, color=color),
                hovertemplate=f'<b>{col.replace("(全天）", "")}</b><br>日期: %{{customdata}}<br>数量: %{{y:,.0f}}<extra></extra>',
                customdata=df['日期_str']
            ))

    fig.update_layout(
        title=dict(text='全天涨停板市值分布趋势', x=0.5,
                   font=dict(size=14, color=style["title_color"])),
        height=420, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='涨停数量', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(size=10, color=style["axis_color"])
        )
    )
    return fig

def create_limit_up_capital_comparison_chart(df):
    """涨停板市值分布对比（全天 vs 上午）"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)

    categories = {
        'large': {'full': '涨停板>100亿(全天）', 'morning': '涨停板>100亿(上午）', 'color': '#e11d48', 'name': '>100亿'},
        'mid_large': {'full': '50亿<涨停板<100亿(全天）', 'morning': '50亿<涨停板<100亿(上午）', 'color': '#f97316', 'name': '50-100亿'},
        'mid_small': {'full': '20亿<涨停板<50亿(全天）', 'morning': '20亿<涨停板<50亿(上午）', 'color': '#7c3aed', 'name': '20-50亿'},
        'small': {'full': '涨停板<20亿(全天）', 'morning': '涨停板<20亿(上午）', 'color': '#06b6d4', 'name': '<20亿'}
    }

    fig = go.Figure()
    for k, v in categories.items():
        fcol, mcol = find_column(df, v['full']), find_column(df, v['morning'])
        if fcol:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[fcol].fillna(0),
                mode='lines+markers', name=f'全天 {v["name"]}',
                line=dict(color=v['color'], width=3), marker=dict(size=6, color=v['color']),
                hovertemplate=f'<b>全天 {v["name"]}</b><br>日期: %{{customdata}}<br>数量: %{{y:,.0f}}<extra></extra>',
                customdata=df['日期_str']
            ))
        if mcol:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[mcol].fillna(0),
                mode='lines+markers', name=f'上午 {v["name"]}',
                line=dict(color=v['color'], width=2, dash='dash'), marker=dict(size=4, color=v['color']),
                hovertemplate=f'<b>上午 {v["name"]}</b><br>日期: %{{customdata}}<br>数量: %{{y:,.0f}}<extra></extra>',
                customdata=df['日期_str']
            ))

    fig.update_layout(
        title=dict(text='涨停板市值分布对比（全天 实线 vs 上午 虚线）', x=0.5,
                   font=dict(size=14, color=style["title_color"])),
        height=440, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='涨停数量', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(size=10, color=style["axis_color"])
        )
    )
    return fig

# ==========================
# 4. 其他核心图表函数
# ==========================

def create_index_open_chart(df):
    """指数开盘图表"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)
    
    fig = go.Figure()
    
    index_columns = {
        '沪指开盘': '#e11d48',
        '深综开盘': '#f97316', 
        '创开盘金额': '#7c3aed'
    }
    
    for col, color in index_columns.items():
        actual = find_column(df, col)
        if actual:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[actual].fillna(0), mode='lines+markers',
                name=actual, line=dict(color=color, width=3), marker=dict(size=6),
                hovertemplate=f'<b>{actual}</b><br>日期: %{{customdata}}<br>数值: %{{y:,.0f}}<extra></extra>',
                customdata=df['日期_str']
            ))
    
    fig.update_layout(
        title=dict(text='三大指数开盘额对比', x=0.5, font=dict(size=16, color=style["title_color"])),
        height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='开盘金额', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    return fig

def create_margin_balance_chart(df):
    """融资余额图表 - 柱状图+趋势线"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)
    
    balance_col = find_column(df, '两融资余额')
    if not balance_col:
        return None
        
    balance_data = df[balance_col].fillna(0)
    
    fig = go.Figure()
    
    # 柱状图
    fig.add_trace(go.Bar(
        x=df.index, y=balance_data, name='两融资余额',
        marker_color='#10b981', opacity=0.85, width=0.4,
        hovertemplate='<b>两融资余额</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
        customdata=df['日期_str']
    ))
    
    # 趋势线
    fig.add_trace(go.Scatter(
        x=df.index, y=balance_data, mode='lines+markers', name='融资余额趋势线',
        line=dict(color='#7c3aed', width=2), marker=dict(size=6, color='#7c3aed'),
        hovertemplate='<b>融资余额趋势</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
        customdata=df['日期_str']
    ))
    
    fig.update_layout(
        title=dict(text='融资余额分析（柱状图+趋势线）', x=0.5, 
                   font=dict(size=16, color=style["title_color"])),
        height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='两融资余额', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    return fig

def create_margin_net_chart(df):
    """融资净买入：折线+涨跌柱（宽0.4）"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)

    net_col = find_column(df, '融资净买入')
    if not net_col:
        return None
    net_data = df[net_col].fillna(0)

    fig = go.Figure()

    # 1. 涨跌柱子（宽0.4）
    colors = ['#16a34a' if v < 0 else '#e11d48' for v in net_data]
    fig.add_trace(go.Bar(
        x=df.index, y=net_data,
        name='融资净买入', width=0.4,
        marker_color=colors, opacity=0.8,
        hovertemplate='<b>融资净买入</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
        customdata=df['日期_str']
    ))

    # 2. 折线（细线+圆点）
    fig.add_trace(go.Scatter(
        x=df.index, y=net_data, mode='lines+markers', name='趋势线',
        line=dict(color='#f59e0b', width=1.58),
        marker=dict(size=5, line=dict(width=1, color='white')),
        hovertemplate='<b>趋势</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
        customdata=df['日期_str']
    ))

    # 0 轴参考线
    fig.add_hline(y=0, line_dash='dash', line_color=style['line_color'], line_width=1.5)

    fig.update_layout(
        title=dict(text='融资净买入（红涨绿跌）', x=0.5, font=dict(size=16, color=style["title_color"])),
        height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='融资净买入', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    return fig

def create_daily_diff_chart(df):
    """今昨差额：折线+涨跌柱（宽0.4）"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)

    diff_col = find_column(df, '今昨差额')
    if not diff_col:
        total_col = find_column(df, '全天总额')
        if total_col:
            df_sorted = df.sort_values('日期' if '日期' in df.columns else df.index)
            df_sorted['今昨差额'] = df_sorted[total_col].diff().fillna(0)
            df = df_sorted.sort_index(ascending=False)
            diff_col = '今昨差额'
        else:
            return None

    diff_data = df[diff_col].fillna(0)

    fig = go.Figure()

    # 1. 涨跌柱子（宽0.4）
    colors = ['#16a34a' if v < 0 else '#e11d48' for v in diff_data]
    fig.add_trace(go.Bar(
        x=df.index, y=diff_data,
        name='今昨差额', width=0.4,
        marker_color=colors, opacity=0.8,
        hovertemplate='<b>今昨差额</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
        customdata=df['日期_str']
    ))

    # 2. 折线（细线+圆点）
    fig.add_trace(go.Scatter(
        x=df.index, y=diff_data, mode='lines+markers', name='趋势线',
        line=dict(color='#06b6d4', width=1.58),
        marker=dict(size=5, line=dict(width=1, color='white')),
        hovertemplate='<b>趋势</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
        customdata=df['日期_str']
    ))

    # 0 轴参考线
    fig.add_hline(y=0, line_dash='dash', line_color=style['line_color'], line_width=1.5)

    fig.update_layout(
        title=dict(text='全天总额今昨差额（红涨绿跌）', x=0.5, font=dict(size=16, color=style["title_color"])),
        height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='差额金额', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    return fig

def create_index_turnover_chart(df):
    """指数成交额图表"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)
    
    fig = go.Figure()
    
    turnover_columns = {
        '沪额全天': '#e11d48',
        '深综全天': '#f97316',
        '创额全天': '#7c3aed'
    }
    
    for col, color in turnover_columns.items():
        actual = find_column(df, col)
        if actual:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[actual].fillna(0), mode='lines+markers',
                name=actual, line=dict(color=color, width=3), marker=dict(size=6),
                hovertemplate=f'<b>{actual}</b><br>日期: %{{customdata}}<br>数值: %{{y:,.0f}}<extra></extra>',
                customdata=df['日期_str']
            ))
    
    fig.update_layout(
        title=dict(text='三大指数成交额对比', x=0.5, font=dict(size=16, color=style["title_color"])),
        height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='成交额', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    return fig

def create_up_down_flat_chart(df):
    """涨跌平家数图表"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)
    
    fig = go.Figure()
    
    # 上涨（红色）
    up_col = find_column(df, '上涨')
    if up_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[up_col].fillna(0), mode='lines+markers', name='上涨家数',
            line=dict(color='#e11d48', width=3), marker=dict(size=6, color='#e11d48'),
            hovertemplate='<b>上涨家数</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    # 下跌（绿色）
    down_col = find_column(df, '下跌')
    if down_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[down_col].fillna(0), mode='lines+markers', name='下跌家数',
            line=dict(color='#16a34a', width=3), marker=dict(size=6, color='#16a34a'),
            hovertemplate='<b>下跌家数</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    # 平盘/停牌（灰色）
    flat_col = find_column(df, '平盘/停牌') or find_column(df, '平盘停牌')
    if flat_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[flat_col].fillna(0), mode='lines+markers', name='平盘/停牌家数',
            line=dict(color='#94a3b8', width=3), marker=dict(size=6, color='#94a3b8'),
            hovertemplate='<b>平盘/停牌家数</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    fig.update_layout(
        title=dict(text='市场涨跌平家数分布', x=0.5, font=dict(size=16, color=style["title_color"])),
        height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='家数', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    return fig

def create_four_line_chart(df):
    """四线图表（涨停跌停等）"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)
    
    fig = go.Figure()
    
    # 全天涨停 - 红色实线
    up_col = find_column(df, '全天涨停')
    if up_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[up_col].fillna(0), mode='lines+markers', name='全天涨停',
            line=dict(color='#e11d48', width=3), marker=dict(size=6, color='#e11d48'),
            hovertemplate='<b>全天涨停</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    # 全天跌停 - 绿色实线
    down_col = find_column(df, '全天跌停')
    if down_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[down_col].fillna(0), mode='lines+markers', name='全天跌停',
            line=dict(color='#16a34a', width=3), marker=dict(size=6, color='#16a34a'),
            hovertemplate='<b>全天跌停</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    # 涨幅大于10% - 红色虚线
    up_10_col = find_column(df, '涨幅大于10%')
    if up_10_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[up_10_col].fillna(0), mode='lines+markers', name='涨幅大于10%',
            line=dict(color='#e11d48', width=2, dash='dash'), marker=dict(size=4, color='#e11d48'),
            hovertemplate='<b>涨幅大于10%</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    # 跌幅大于10% - 绿色虚线
    down_10_col = find_column(df, '跌幅于大于10%') or find_column(df, '跌幅大于10%')
    if down_10_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[down_10_col].fillna(0), mode='lines+markers', name='跌幅大于10%',
            line=dict(color='#16a34a', width=2, dash='dash'), marker=dict(size=4, color='#16a34a'),
            hovertemplate='<b>跌幅大于10%</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    fig.update_layout(
        title=dict(text='涨停跌停与大幅波动分析', x=0.5, font=dict(size=16, color=style["title_color"])),
        height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='数量', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    return fig

def create_limit_down_chart(df):
    """跌停细分图表"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)
    
    fig = go.Figure()
    
    # 主板跌停数 - 亮绿色
    main_col = find_column(df, '主板跌停数')
    if main_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[main_col].fillna(0), mode='lines+markers', name='主板跌停数',
            line=dict(color='#22c55e', width=3), marker=dict(size=6, color='#22c55e'),
            hovertemplate='<b>主板跌停数</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    # 创业板跌停数 - 暗绿色
    gem_col = find_column(df, '创业板跌停数')
    if gem_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[gem_col].fillna(0), mode='lines+markers', name='创业板跌停数',
            line=dict(color='#15803d', width=3), marker=dict(size=6, color='#15803d'),
            hovertemplate='<b>创业板跌停数</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    # 北证跌停数 - 虚线灰色
    bse_col = find_column(df, '北证跌停数')
    if bse_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[bse_col].fillna(0), mode='lines+markers', name='北证跌停数',
            line=dict(color='#94a3b8', width=2, dash='dash'), marker=dict(size=4, color='#94a3b8'),
            hovertemplate='<b>北证跌停数</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    fig.update_layout(
        title=dict(text='跌停数据细分（按板块）', x=0.5, font=dict(size=16, color=style["title_color"])),
        height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='跌停数量', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    return fig

def create_enhanced_limit_up_analysis_chart(df):
    """增强版涨停连板与高度板分析（全天实线 + 上午虚线）"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)
    
    fig = go.Figure()
    
    # 全天数据 - 实线
    full_up_col = find_column(df, '全天涨停')
    if full_up_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[full_up_col].fillna(0), mode='lines+markers', name='全天涨停数',
            line=dict(color='#e11d48', width=3), marker=dict(size=6),
            hovertemplate='<b>全天涨停数</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    full_chain_col = find_column(df, '全天涨停连接板')
    if full_chain_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[full_chain_col].fillna(0), mode='lines+markers', name='全天连板数',
            line=dict(color='#7c3aed', width=3), marker=dict(size=6),
            hovertemplate='<b>全天连板数</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    full_height_col = find_column(df, '全天高度板')
    if full_height_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[full_height_col].fillna(0), mode='lines+markers', name='全天高度板',
            line=dict(color='#fbbf24', width=3), marker=dict(size=6, symbol='diamond'),
            hovertemplate='<b>全天高度板</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    # 上午数据 - 虚线
    morning_up_col = find_column(df, '上午涨停')
    if morning_up_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[morning_up_col].fillna(0), mode='lines+markers', name='上午涨停数',
            line=dict(color='#e11d48', width=2, dash='dash'), marker=dict(size=4),
            hovertemplate='<b>上午涨停数</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    morning_chain_col = find_column(df, '上午涨停连接板')
    if morning_chain_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[morning_chain_col].fillna(0), mode='lines+markers', name='上午连板数',
            line=dict(color='#7c3aed', width=2, dash='dash'), marker=dict(size=4),
            hovertemplate='<b>上午连板数</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    morning_height_col = find_column(df, '上午高度板')
    if morning_height_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[morning_height_col].fillna(0), mode='lines+markers', name='上午高度板',
            line=dict(color='#fbbf24', width=2, dash='dash'), marker=dict(size=4, symbol='diamond'),
            hovertemplate='<b>上午高度板</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    fig.update_layout(
        title=dict(text='涨停连板与高度板分析（全天实线+上午虚线）', x=0.5, 
                   font=dict(size=16, color=style["title_color"])),
        height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='数量', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    return fig

def create_morning_limit_up_chart(df):
    """上午涨停图表"""
    style = get_plot_style()
    df = df.copy()
    df['日期_str'] = df['日期'].dt.strftime('%Y-%m-%d') if '日期' in df.columns else df.index.astype(str)
    
    fig = go.Figure()
    
    morning_up_col = find_column(df, '上午涨停')
    if morning_up_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[morning_up_col].fillna(0), mode='lines+markers', name='上午涨停数',
            line=dict(color='#f97316', width=3), marker=dict(size=6),
            hovertemplate='<b>上午涨停数</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    morning_chain_col = find_column(df, '上午涨停连接板')
    if morning_chain_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[morning_chain_col].fillna(0), mode='lines+markers', name='上午连板数',
            line=dict(color='#ea580c', width=3), marker=dict(size=6),
            hovertemplate='<b>上午连板数</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    morning_height_col = find_column(df, '上午高度板')
    if morning_height_col:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[morning_height_col].fillna(0), mode='lines+markers', name='上午高度板',
            line=dict(color='#dc2626', width=3), marker=dict(size=6, symbol='diamond'),
            hovertemplate='<b>上午高度板</b><br>日期: %{customdata}<br>数值: %{y:,.0f}<extra></extra>',
            customdata=df['日期_str']
        ))
    
    fig.update_layout(
        title=dict(text='上午涨停数量分析', x=0.5, font=dict(size=16, color=style["title_color"])),
        height=400, hovermode='x unified',
        plot_bgcolor=style["plot_bgcolor"], paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            type='category', tickvals=df.index, ticktext=df['日期_str'],
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            title='数量', gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    return fig

# ==========================
# 5. 主要显示函数
# ==========================

def show_fund_flow(df):
    """显示资金流向分析"""
    col1, col2 = st.columns(2)
    
    with col1:
        fig_north = create_professional_line_chart(
            df, ['北向成交额', '北向净值'], 
            '北向资金流向分析', ['#7c3aed', '#06b6d4']
        )
        if fig_north:
            st.plotly_chart(fig_north, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无北向资金数据")
    
    with col2:
        fig_index_open = create_index_open_chart(df)
        if fig_index_open:
            st.plotly_chart(fig_index_open, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无指数开盘数据")
    
    # 两融数据分析
    st.markdown('<div class="section-header">两融数据分析</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        fig_margin_balance = create_margin_balance_chart(df)
        if fig_margin_balance:
            st.plotly_chart(fig_margin_balance, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("数据中暂无两融资余额信息")
    
    with col2:
        fig_margin_net = create_margin_net_chart(df)
        if fig_margin_net:
            st.plotly_chart(fig_margin_net, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("数据中暂无融资净买入信息")

def show_market_turnover(df):
    """显示市场成交趋势分析"""
    # 市场总额与今昨差分析
    st.markdown('<div class="section-header">市场总额与今昨差分析</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        fig_total = create_grouped_bar_chart(df, '上午总额', '全天总额', '市场总成交额对比（上午vs全天）')
        if fig_total:
            st.plotly_chart(fig_total, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无市场总额数据")
    
    with col2:
        fig_diff = create_daily_diff_chart(df)
        if fig_diff:
            st.plotly_chart(fig_diff, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无今昨差额数据")
    
    # 各市场成交趋势
    st.markdown('<div class="section-header">各市场成交趋势</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        fig_sh = create_grouped_bar_chart(df, '沪额上午', '沪额全天', '沪市成交额趋势（上午vs全天）')
        if fig_sh:
            st.plotly_chart(fig_sh, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无沪市成交数据")
    
    with col2:
        fig_sz = create_grouped_bar_chart(df, '深综上午', '深综全天', '深市成交额趋势（上午vs全天）')
        if fig_sz:
            st.plotly_chart(fig_sz, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无深市成交数据")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_cy = create_grouped_bar_chart(df, '创额上午', '创额全天', '创业板成交额趋势（上午vs全天）')
        if fig_cy:
            st.plotly_chart(fig_cy, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无创业板成交数据")
    
    with col2:
        fig_index = create_index_turnover_chart(df)
        if fig_index:
            st.plotly_chart(fig_index, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无指数成交数据")

def show_limit_up_down(df):
    """显示涨跌停分析"""
    # 市场情绪分析
    st.markdown('<div class="section-header">市场情绪分析</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        fig_up_down_flat = create_up_down_flat_chart(df)
        if fig_up_down_flat:
            st.plotly_chart(fig_up_down_flat, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无涨跌平数据")
    
    with col2:
        fig_board_rate = create_professional_line_chart(df, ['全天封板率'], '市场封板率趋势', ['#f97316'])
        if fig_board_rate:
            st.plotly_chart(fig_board_rate, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无封板率数据")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_four_line = create_four_line_chart(df)
        if fig_four_line:
            st.plotly_chart(fig_four_line, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无四线数据")
    
    with col2:
        fig_limit_down = create_limit_down_chart(df)
        if fig_limit_down:
            st.plotly_chart(fig_limit_down, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无跌停细分数据")

    # 涨停板深度分析
    st.markdown('<div class="section-header">涨停板深度分析</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        # 显示主板涨停数、创业板涨停数、北证涨停数
        fig_board_limit = create_professional_line_chart(
            df, ['主板涨停数', '创业板涨停数', '北证涨停数'], 
            '板块全天涨停板：主板涨停数、创业板涨停数、北证涨停数', ['#e11d48', '#f97316', '#7c3aed']
        )
        if fig_board_limit:
            st.plotly_chart(fig_board_limit, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无板块涨停数据")
    
    with col2:
        fig_limit_chain_enhanced = create_enhanced_limit_up_analysis_chart(df)
        if fig_limit_chain_enhanced:
            st.plotly_chart(fig_limit_chain_enhanced, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无涨停连板数据")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_morning_limit = create_morning_limit_up_chart(df)
        if fig_morning_limit:
            st.plotly_chart(fig_morning_limit, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无上午涨停数据")
    
    with col2:
        fig_volatility = create_professional_line_chart(
            df, ['涨幅大于10%', '跌幅于大于10%'], 
            '大幅波动股票数量', ['#e11d48', '#16a34a']
        )
        if fig_volatility:
            st.plotly_chart(fig_volatility, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("暂无大幅波动数据")

    # 涨停板市值分布分析 
    st.markdown('<div class="section-header">涨停板市值分布分析</div>', unsafe_allow_html=True)
    
    # 全天市值分布
    col1, col2 = st.columns(2)
    
    with col1:
        fig_full_capital = create_full_limit_up_capital_chart(df)
        if fig_full_capital:
            st.plotly_chart(fig_full_capital, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("全天涨停板市值分布数据暂不可用")
    
    with col2:
        fig_morning_capital = create_morning_limit_up_capital_chart(df)
        if fig_morning_capital:
            st.plotly_chart(fig_morning_capital, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("上午涨停板市值分布数据暂不可用")
    
    # 趋势和对比分析
    col1, col2 = st.columns(2)
    
    with col1:
        fig_full_trend = create_full_limit_up_capital_trend_chart(df)
        if fig_full_trend:
            st.plotly_chart(fig_full_trend, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("全天涨停板市值分布趋势数据暂不可用")
    
    with col2:
        fig_comparison = create_limit_up_capital_comparison_chart(df)
        if fig_comparison:
            st.plotly_chart(fig_comparison, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("涨停板市值分布对比数据暂不可用")

# ==========================
# 6. 其他功能函数
# ==========================

def show_detailed_analysis(df):
    """显示详细数据分析"""
    # 数据诊断面板
    st.markdown("#### 🔍 数据诊断")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 检查今昨差额
        if find_column(df, '今昨差额'):
            zero_diff = (df[find_column(df, '今昨差额')] == 0).sum()
            if zero_diff > 0:
                st.warning(f"今昨差额为零: {zero_diff}条")
            else:
                st.success("今昨差额数据正常")
        else:
            st.error("缺少今昨差额列")
    
    with col2:
        # 检查跌停数据
        if find_column(df, '全天跌停'):
            st.success("全天跌停数据存在")
        elif any(find_column(df, col) for col in ['主板跌停数', '创业板跌停数', '北证跌停数']):
            st.info("可使用板块跌停数据")
        else:
            st.error("缺少跌停数据")
    
    with col3:
        # 检查基本数据完整性
        required_cols = ['全天总额', '北向净值', '上涨', '下跌']
        missing_cols = [col for col in required_cols if not find_column(df, col)]
        if missing_cols:
            st.error(f"缺失列: {', '.join(missing_cols)}")
        else:
            st.success("基础数据完整")
    
    # 数据统计概览
    st.markdown("#### 数据统计概览")
    
    # 数值列的基本统计
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        st.dataframe(df[numeric_cols].describe(), use_container_width=True)
    
    # 最新交易日数据
    st.markdown("#### 最新交易日详情")
    if len(df) > 0:
        latest_data = df.iloc[0].to_frame().T  # 第一行是最新数据
        st.dataframe(latest_data, use_container_width=True)
        
        # 显示关键指标
        st.markdown("#### 关键指标验证")
        key_metrics = ['全天总额', '今昨差额', '北向净值', '全天涨停', '全天跌停']
        for metric in key_metrics:
            actual_metric = find_column(df, metric)
            if actual_metric:
                value = df[actual_metric].iloc[0]
                st.write(f"{actual_metric}: {value}")

def show_prediction_results(prediction_df, target):
    """显示预测结果"""
    st.markdown("### 📊 预测结果可视化")
    
    style = get_plot_style()
    fig = go.Figure()
    
    if 'actual' in prediction_df.columns and 'predicted' in prediction_df.columns:
        fig.add_trace(go.Scatter(
            x=prediction_df.index,
            y=prediction_df['actual'],
            mode='lines+markers',
            name='实际值',
            line=dict(color='#e11d48', width=3)
        ))
        
        fig.add_trace(go.Scatter(
            x=prediction_df.index,
            y=prediction_df['predicted'],
            mode='lines+markers',
            name='预测值',
            line=dict(color='#06b6d4', width=3, dash='dash')
        ))
    
    fig.update_layout(
        title=f"{target} - 实际值 vs 预测值",
        height=400,
        plot_bgcolor=style["plot_bgcolor"],
        paper_bgcolor=style["paper_bgcolor"],
        xaxis=dict(
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        yaxis=dict(
            gridcolor=style["grid_color"], linecolor=style["line_color"],
            tickfont=dict(color=style["axis_color"]), title_font=dict(color=style["axis_color"])
        ),
        legend=dict(
            bgcolor=style["legend_bg"], font=dict(color=style["axis_color"])
        )
    )
    
    st.plotly_chart(fig, config=PLOTLY_CONFIG, use_container_width=True)