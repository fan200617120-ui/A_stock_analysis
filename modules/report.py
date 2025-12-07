import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# ==================== 现代化配色方案 ====================
COLOR_SCHEME = {
    'primary': '#6366f1',      # 靛蓝色
    'secondary': '#8b5cf6',    # 紫色
    'accent': '#06b6d4',       # 青色
    'success': '#10b981',      # 绿色
    'warning': '#f59e0b',      # 琥珀色
    'error': '#ef4444',        # 红色
    'info': '#3b82f6',         # 蓝色
    'hot': '#dc2626',          # 深红
    'warm': '#ea580c',         # 橙色
    'neutral': '#16a34a',      # 绿色
    'cool': '#0891b2',         # 青色
    'cold': '#4f46e5',         # 靛蓝
    'dark': '#0f172a',         # 深蓝黑
    'light': '#f8fafc',        # 浅灰
    'muted': '#64748b',        # 灰蓝色
    'gradient_start': '#667eea',
    'gradient_end': '#764ba2',
    'text': '#1f2937'          # 添加文本颜色
}

# ==================== 辅助函数 ====================
def get_quantile_level(value, thresholds):
    """根据阈值获取等级和颜色"""
    sorted_thresholds = sorted(thresholds.keys(), reverse=True)
    for threshold in sorted_thresholds:
        if value >= threshold:
            level_name = thresholds[threshold]
            color = COLOR_SCHEME.get(level_name, COLOR_SCHEME['muted'])
            return level_name, color
    min_threshold = min(thresholds.keys())
    level_name = thresholds[min_threshold]
    color = COLOR_SCHEME.get(level_name, COLOR_SCHEME['muted'])
    return level_name, color

# 添加中文解释映射
LEVEL_CHINESE_MAP = {
    'hot': '🔥 火热',
    'warm': '💪 活跃', 
    'neutral': '⚖️ 中性',
    'cool': '😐 冷静',
    'cold': '🥶 冷清',
    'success': '📈 积极',
    'warning': '⚠️ 谨慎',
    'info': '🌀 中性',
    'error': '💀 危险',
    'unknown': '❓ 未知'
}

def get_chinese_level(english_level):
    """将英文等级转换为中文解释"""
    return LEVEL_CHINESE_MAP.get(english_level, english_level)

# ==================== 六维核心分析 ====================
def analyze_turnover(df):
    """成交额分析"""
    if len(df) < 5:
        return {'value': 0, 'ratio': 1, 'level': '未知', 'color': COLOR_SCHEME['muted']}
    
    latest = df.iloc[-1]
    avg5 = df['全天总额'].tail(5).mean()
    ratio = latest['全天总额'] / avg5 if avg5 != 0 else 1
    level, color = get_quantile_level(ratio, {1.3: 'hot', 1.1: 'warm', 0.9: 'neutral', 0.7: 'cool'})
    return {'value': latest['全天总额'], 'ratio': ratio, 'level': level, 'color': color}

def analyze_north(df):
    """北向资金分析"""
    if len(df) == 0:
        return {'value': 0, 'level': '未知', 'color': COLOR_SCHEME['muted']}
    
    latest = df.iloc[-1]
    flow = latest.get('北向净值', 0)
    if flow > 50:
        level, color = '积极', COLOR_SCHEME['success']
    elif flow < -30:
        level, color = '谨慎', COLOR_SCHEME['warning']
    else:
        level, color = '中性', COLOR_SCHEME['info']
    return {'value': flow, 'level': level, 'color': color}

def analyze_up_down(df):
    """涨跌分析"""
    if len(df) == 0:
        return {'up': 0, 'down': 0, 'ratio': 0.5, 'level': '未知', 'color': COLOR_SCHEME['muted']}
    
    latest = df.iloc[-1]
    up = latest.get('上涨', 0)
    down = latest.get('下跌', 0)
    adv_ratio = up / (up + down + 1e-8)
    level, color = get_quantile_level(adv_ratio, {0.7: 'hot', 0.55: 'warm', 0.45: 'neutral', 0.3: 'cool'})
    return {'up': up, 'down': down, 'ratio': adv_ratio, 'level': level, 'color': color}

def analyze_limit_up(df):
    """涨停分析"""
    if len(df) == 0:
        return {'limit_up': 0, 'limit_down': 0, 'ratio': 1, 'level': '未知', 'color': COLOR_SCHEME['muted']}
    
    latest = df.iloc[-1]
    lu = latest.get('全天涨停', 0)
    ld = latest.get('全天跌停', 0)
    ratio = lu / (ld + 1e-8)
    level, color = get_quantile_level(ratio, {10: 'hot', 3: 'warm', 1: 'neutral', 0.5: 'cool'})
    return {'limit_up': lu, 'limit_down': ld, 'ratio': ratio, 'level': level, 'color': color}

def analyze_cap_dist(df):
    """市值分布分析"""
    cols = ['涨停板>100亿(全天）', '50亿<涨停板<100亿(全天）', '20亿<涨停板<50亿(全天）', '涨停板<20亿(全天）']
    if not all(c in df.columns for c in cols):
        return None
    latest = df[cols].iloc[-1].fillna(0)
    total = latest.sum()
    if total == 0:
        return None
    return latest.to_dict()

def analyze_sector_rotation(df):
    """板块轮动分析"""
    if '行业涨停榜' not in df.columns:
        return None
    latest = df['行业涨停榜'].iloc[-1]
    if pd.isna(latest):
        return None
    sectors = [s.split('\\') for s in str(latest).split('\\') if s]
    return [{'name': s[0], 'count': int(s[1]) if len(s) > 1 else 0} for s in sectors[:8]]

# ==================== 基础情绪指标 ====================
def analyze_market_sentiment(df):
    """综合分析市场情绪"""
    if len(df) < 2:
        return {'score': 50, 'level': '中性', 'trend': '平稳', 'color': COLOR_SCHEME['neutral']}
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 情绪因子计算
    factors = []
    
    # 1. 涨停情绪
    if '全天涨停' in df.columns:
        limit_up = latest.get('全天涨停', 0)
        if limit_up > 80:
            factors.append(20)
        elif limit_up > 50:
            factors.append(15)
        elif limit_up > 30:
            factors.append(10)
        elif limit_up < 10:
            factors.append(-10)
        else:
            factors.append(5)
    
    # 2. 资金情绪
    if '北向净值' in df.columns:
        north_flow = latest.get('北向净值', 0)
        if north_flow > 50:
            factors.append(20)
        elif north_flow > 20:
            factors.append(15)
        elif north_flow < -30:
            factors.append(-15)
        elif north_flow < -10:
            factors.append(-10)
        else:
            factors.append(5)
    
    # 3. 广度情绪
    if all(col in df.columns for col in ['上涨', '下跌']):
        up_ratio = latest['上涨'] / (latest['上涨'] + latest['下跌'] + 1)
        if up_ratio > 0.7:
            factors.append(20)
        elif up_ratio > 0.6:
            factors.append(15)
        elif up_ratio < 0.3:
            factors.append(-15)
        elif up_ratio < 0.4:
            factors.append(-10)
        else:
            factors.append(5)
    
    # 4. 量能情绪
    if '全天总额' in df.columns and len(df) >= 5:
        volume_trend = (latest['全天总额'] - prev['全天总额']) / prev['全天总额']
        if volume_trend > 0.1:
            factors.append(15)
        elif volume_trend > 0.05:
            factors.append(10)
        elif volume_trend < -0.1:
            factors.append(-10)
        else:
            factors.append(5)
    
    # 计算综合情绪得分
    sentiment_score = max(0, min(100, 50 + sum(factors)))
    
    # 确定情绪等级
    if sentiment_score >= 80:
        level, color, trend = '狂热', COLOR_SCHEME['hot'], '极度乐观'
    elif sentiment_score >= 70:
        level, color, trend = '乐观', COLOR_SCHEME['warning'], '积极'
    elif sentiment_score >= 60:
        level, color, trend = '偏暖', COLOR_SCHEME['neutral'], '温和'
    elif sentiment_score >= 40:
        level, color, trend = '中性', COLOR_SCHEME['info'], '平稳'
    elif sentiment_score >= 30:
        level, color, trend = '谨慎', COLOR_SCHEME['cool'], '偏冷'
    else:
        level, color, trend = '恐慌', COLOR_SCHEME['cold'], '悲观'
    
    return {
        'score': sentiment_score,
        'level': level,
        'trend': trend,
        'color': color,
        'factors': {
            '涨停情绪': factors[0] if len(factors) > 0 else 0,
            '资金情绪': factors[1] if len(factors) > 1 else 0,
            '广度情绪': factors[2] if len(factors) > 2 else 0,
            '量能情绪': factors[3] if len(factors) > 3 else 0
        }
    }

def create_sentiment_gauge(sentiment_data):
    """创建情绪指标仪表盘"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=sentiment_data['score'],
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"市场情绪 · {sentiment_data['level']}", 'font': {'size': 16}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': sentiment_data['color']},
            'steps': [
                {'range': [0, 20], 'color': 'rgba(79, 70, 229, 0.1)'},
                {'range': [20, 40], 'color': 'rgba(99, 102, 241, 0.2)'},
                {'range': [40, 60], 'color': 'rgba(139, 92, 246, 0.3)'},
                {'range': [60, 80], 'color': 'rgba(236, 72, 153, 0.4)'},
                {'range': [80, 100], 'color': 'rgba(239, 68, 68, 0.5)'}
            ],
        }
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# ==================== 综合评分系统 ====================
class MarketScoringSystem:
    def __init__(self):
        self.weights = {
            'volume': 0.15,
            'north_money': 0.15,
            'advance_decline': 0.15,
            'limit_up': 0.15,
            'market_cap': 0.15,
            'sector_rotation': 0.15,
            'sentiment': 0.10
        }
    
    def calculate_volume_score(self, df):
        if '全天总额' not in df.columns or len(df) < 5:
            return 50
        latest = df.iloc[-1]
        current_volume = latest['全天总额']
        volume_ma5 = df['全天总额'].tail(5).mean()
        volume_ratio = current_volume / volume_ma5
        
        if volume_ratio > 1.3:
            return 85
        elif volume_ratio > 1.1:
            return 70
        elif volume_ratio < 0.8:
            return 30
        elif volume_ratio < 0.6:
            return 15
        return 50
    
    def calculate_north_money_score(self, df):
        if '北向净值' not in df.columns or len(df) < 3:
            return 50
        
        latest = df.iloc[-1]
        north_flow = latest['北向净值']
        recent_north = df['北向净值'].tail(3)
        
        trend_score = 0
        if all(x > 0 for x in recent_north):
            trend_score = 15
        elif all(x < 0 for x in recent_north):
            trend_score = -15
        
        if north_flow > 80:
            flow_score = 30
        elif north_flow > 50:
            flow_score = 20
        elif north_flow > 20:
            flow_score = 10
        elif north_flow < -50:
            flow_score = -25
        elif north_flow < -20:
            flow_score = -15
        else:
            flow_score = 0
            
        return max(0, min(100, 50 + flow_score + trend_score))
    
    def calculate_advance_decline_score(self, df):
        if not all(col in df.columns for col in ['上涨', '下跌']):
            return 50
        
        latest = df.iloc[-1]
        up = latest['上涨']
        down = latest['下跌']
        total = up + down
        
        if total == 0:
            return 50
            
        advance_ratio = up / total
        
        if advance_ratio > 0.7:
            return 85
        elif advance_ratio > 0.6:
            return 70
        elif advance_ratio < 0.3:
            return 25
        elif advance_ratio < 0.4:
            return 35
        return 50
    
    def calculate_limit_up_score(self, df):
        if '全天涨停' not in df.columns or len(df) < 3:
            return 50
        
        latest = df.iloc[-1]
        limit_up = latest['全天涨停']
        score = 50
        
        if limit_up > 100:
            score += 25
        elif limit_up > 80:
            score += 15
        elif limit_up > 60:
            score += 5
        elif limit_up < 20:
            score -= 20
        elif limit_up < 10:
            score -= 30
            
        if '全天封板率' in df.columns:
            board_rate = latest['全天封板率']
            if board_rate > 0.8:
                score += 15
            elif board_rate > 0.6:
                score += 5
            elif board_rate < 0.4:
                score -= 10
                
        if '全天跌停' in df.columns:
            limit_down = latest['全天跌停']
            if limit_down > 50:
                score -= 20
            elif limit_down > 30:
                score -= 10
                
        return max(0, min(100, score))
    
    def calculate_market_cap_score(self, df):
        capital_columns = [
            '涨停板>100亿(全天）', 
            '50亿<涨停板<100亿(全天）', 
            '20亿<涨停板<50亿(全天）', 
            '涨停板<20亿(全天）'
        ]
        
        available_cols = [col for col in capital_columns if col in df.columns]
        if not available_cols or len(df) == 0:
            return 50
            
        latest = df.iloc[-1]
        capital_data = [latest.get(col, 0) for col in available_cols]
        total_capital = sum(capital_data)
        
        if total_capital == 0:
            return 50
            
        large_cap_ratio = capital_data[0] / total_capital if len(capital_data) > 0 else 0
        small_cap_ratio = capital_data[-1] / total_capital if len(capital_data) > 3 else 0
        
        score = 50
        
        if large_cap_ratio > 0.4:
            score += 15
        elif small_cap_ratio > 0.6:
            score -= 15
        elif 0.2 <= large_cap_ratio <= 0.4 and small_cap_ratio <= 0.4:
            score += 10
            
        return max(0, min(100, score))
    
    def calculate_sector_rotation_score(self, df):
        score = 50
        
        if all(col in df.columns for col in ['主板涨停数', '创业板涨停数']):
            latest = df.iloc[-1]
            main_limit = latest['主板涨停数']
            gem_limit = latest['创业板涨停数']
            total_limit = main_limit + gem_limit
            
            if total_limit > 0:
                main_ratio = main_limit / total_limit
                if 0.3 <= main_ratio <= 0.7:
                    score += 10
                elif main_ratio > 0.8 or main_ratio < 0.2:
                    score -= 5
                    
        return max(0, min(100, score))
    
    def calculate_sentiment_score(self, df):
        if len(df) == 0:
            return 50
            
        latest = df.iloc[-1]
        score = 50
        factors = []
        
        if '全天涨停' in df.columns:
            limit_up = latest['全天涨停']
            if limit_up > 80:
                factors.append(15)
            elif limit_up > 50:
                factors.append(8)
            elif limit_up < 20:
                factors.append(-10)
                
        if '北向净值' in df.columns:
            north_flow = latest['北向净值']
            if north_flow > 50:
                factors.append(12)
            elif north_flow > 20:
                factors.append(6)
            elif north_flow < -30:
                factors.append(-8)
                
        if all(col in df.columns for col in ['上涨', '下跌']):
            up_ratio = latest['上涨'] / (latest['上涨'] + latest['下跌'] + 1)
            if up_ratio > 0.7:
                factors.append(10)
            elif up_ratio < 0.3:
                factors.append(-8)
                
        if '全天总额' in df.columns and len(df) >= 5:
            volume_trend = (latest['全天总额'] - df['全天总额'].tail(5).mean()) / df['全天总额'].tail(5).mean()
            if volume_trend > 0.1:
                factors.append(8)
            elif volume_trend < -0.1:
                factors.append(-6)
                
        if factors:
            score += sum(factors) / len(factors) * 2
            
        return max(0, min(100, score))
    
    def calculate_comprehensive_score(self, df):
        scores = {}
        total_weight = 0
        weighted_score = 0
        
        for factor, weight in self.weights.items():
            method_name = f'calculate_{factor}_score'
            if hasattr(self, method_name):
                score_method = getattr(self, method_name)
                score = score_method(df)
                scores[factor] = score
                weighted_score += score * weight
                total_weight += weight
            else:
                scores[factor] = 50
                weighted_score += 50 * weight
                total_weight += weight
            
        if total_weight > 0:
            comprehensive_score = weighted_score / total_weight
        else:
            comprehensive_score = 50
            
        return max(0, min(100, comprehensive_score)), scores

# ==================== 可视化组件 ====================
def create_score_gauge(score, title, color):
    """创建评分仪表盘"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 16}},
        delta={'reference': 50},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 30], 'color': 'rgba(79, 70, 229, 0.2)'},
                {'range': [30, 70], 'color': 'rgba(99, 102, 241, 0.2)'},
                {'range': [70, 100], 'color': 'rgba(139, 92, 246, 0.2)'}
            ],
            'threshold': {
                'line': {'color': COLOR_SCHEME['hot'], 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(
        height=250, 
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def create_market_cap_analysis(df):
    """创建市值分布饼图"""
    capital_columns = [
        '涨停板>100亿(全天）', 
        '50亿<涨停板<100亿(全天）', 
        '20亿<涨停板<50亿(全天）', 
        '涨停板<20亿(全天）'
    ]
    
    available_cols = [col for col in capital_columns if col in df.columns]
    if not available_cols or len(df) == 0:
        return None
        
    latest = df.iloc[-1]
    labels = ['>100亿', '50-100亿', '20-50亿', '<20亿']
    values = [latest.get(col, 0) for col in available_cols]
    
    colors = [
        COLOR_SCHEME['primary'], 
        COLOR_SCHEME['secondary'], 
        COLOR_SCHEME['accent'], 
        COLOR_SCHEME['warning']
    ]
    
    fig = go.Figure(data=[
        go.Pie(
            labels=labels[:len(available_cols)],
            values=values,
            hole=0.4,
            marker=dict(colors=colors[:len(available_cols)])
        )
    ])
    
    fig.update_layout(
        title_text="涨停板市值分布",
        height=300,
        showlegend=True,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

# ==================== 现代化雷达图设计 ====================
def create_modern_radar_chart(scores, categories):
    """创建现代化雷达图 - 更时尚的设计"""
    
    # 转换数据格式
    categories_ch = list(categories.values())
    scores_values = [scores.get(k, 50) for k in categories.keys()]
    
    # 闭合雷达图
    categories_ch.append(categories_ch[0])
    scores_values.append(scores_values[0])
    
    fig = go.Figure()
    
    # 背景同心圆
    for i in range(20, 101, 20):
        fig.add_trace(go.Scatterpolar(
            r=[i] * (len(categories_ch)),
            theta=categories_ch,
            fill='toself',
            fillcolor=f'rgba(99, 102, 241, {0.02*(i/20)})',
            line=dict(color='rgba(99, 102, 241, 0.1)', width=1),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # 主雷达区域 - 使用渐变填充和3D效果
    fig.add_trace(go.Scatterpolar(
        r=scores_values,
        theta=categories_ch,
        fill='toself',
        fillcolor='rgba(99, 102, 241, 0.4)',  # 改为主色调
        line=dict(
            color=COLOR_SCHEME['primary'],
            width=3,
            shape='spline',  # 平滑曲线
            smoothing=0.8
        ),
        marker=dict(
            size=8,
            color=COLOR_SCHEME['primary'],
            line=dict(width=2, color='white')
        ),
        name='维度评分',
        hovertemplate='<b>%{theta}</b><br>评分: %{r:.1f}<extra></extra>'
    ))
    
    # 添加数据点标签
    for i, (cat, score) in enumerate(zip(categories_ch[:-1], scores_values[:-1])):
        fig.add_annotation(
            x=cat,
            y=score,
            text=f'{score:.0f}',
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor=COLOR_SCHEME['primary'],
            ax=0,
            ay=-20 if score > 50 else 20,
            bgcolor='white',
            bordercolor=COLOR_SCHEME['primary'],
            borderwidth=1,
            font=dict(size=10, color=COLOR_SCHEME['primary'])
        )
    
    # 现代化布局
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[0, 20, 40, 60, 80, 100],
                ticktext=['0', '20', '40', '60', '80', '100'],
                tickfont=dict(size=10, color=COLOR_SCHEME['muted']),
                gridcolor='rgba(99, 102, 241, 0.2)',
                linecolor='rgba(99, 102, 241, 0.3)',
            ),
            angularaxis=dict(
                tickfont=dict(size=11, color=COLOR_SCHEME['text']),
                gridcolor='rgba(99, 102, 241, 0.2)',
                linecolor='rgba(99, 102, 241, 0.3)',
                rotation=90  # 从顶部开始
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=False,
        height=450,
        margin=dict(l=60, r=60, t=80, b=60),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        title=dict(
            text='📊 多维度市场分析雷达图',
            x=0.5,
            font=dict(size=16,)
        )
    )
    
    return fig

# ==================== 市值分布与板块热点 ====================
def create_market_cap_bubble(df):
    """创建市值分布气泡图"""
    capital_columns = [
        '涨停板>100亿(全天）', 
        '50亿<涨停板<100亿(全天）', 
        '20亿<涨停板<50亿(全天）', 
        '涨停板<20亿(全天）'
    ]
    
    available_cols = [col for col in capital_columns if col in df.columns]
    if not available_cols or len(df) == 0:
        return None
        
    latest = df.iloc[-1]
    
    # 创建气泡图数据
    sizes = [latest.get(col, 0) for col in available_cols]
    labels = ['>100亿', '50-100亿', '20-50亿', '<20亿']
    colors = [COLOR_SCHEME['hot'], COLOR_SCHEME['warning'], COLOR_SCHEME['neutral'], COLOR_SCHEME['cool']]
    
    # 创建气泡图
    fig = go.Figure()
    
    for i, (label, size, color) in enumerate(zip(labels, sizes, colors)):
        fig.add_trace(go.Scatter(
            x=[i],  # X轴位置
            y=[size],  # Y轴数值
            mode='markers',
            marker=dict(
                size=size * 2 + 20,  # 气泡大小
                color=color,
                sizemode='diameter',
                sizeref=2.*max(sizes)/(40.**2),
                sizemin=4
            ),
            name=label,
            text=f"{label}: {size}",
            hovertemplate="<b>%{text}</b><extra></extra>"
        ))
    
    fig.update_layout(
        title="💰 涨停市值分布气泡图",
        xaxis=dict(
            title="市值区间",
            tickvals=list(range(len(labels))),
            ticktext=labels
        ),
        yaxis=dict(title="涨停数量"),
        height=300,
        showlegend=True,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_sector_concept_heatmap(df):
    """创建行业概念热点图"""
    if len(df) == 0:
        return None
        
    latest = df.iloc[-1]
    
    # 检查是否有行业和概念数据
    if '行业涨停榜' not in latest or '概念涨停榜' not in latest:
        return None
        
    industry_data = latest['行业涨停榜']
    concept_data = latest['概念涨停榜']
    
    if pd.isna(industry_data) or pd.isna(concept_data):
        return None
    
    # 解析行业和概念数据
    def parse_sector_data(s):
        try:
            items = []
            for item in str(s).split('\\'):
                if '+' in item:
                    name, count = item.split('+')
                    items.append((name.strip(), int(count)))
                else:
                    items.append((item.strip(), 1))
            return items
        except:
            return []
    
    industries = parse_sector_data(industry_data)[:6]  # 取前6个行业
    concepts = parse_sector_data(concept_data)[:6]     # 取前6个概念
    
    if not industries or not concepts:
        return None
    
    # 创建热力图数据
    heat_data = []
    industry_names = [ind[0] for ind in industries]
    concept_names = [con[0] for con in concepts]
    
    # 简单模拟热度数据（实际应该基于真实关联）
    for industry, ind_count in industries:
        row = []
        for concept, con_count in concepts:
            # 热度 = 行业热度 × 概念热度 × 随机因子
            heat_value = ind_count * con_count * (0.5 + 0.5 * np.random.random())
            row.append(heat_value)
        heat_data.append(row)
    
    fig = go.Figure(go.Heatmap(
        z=heat_data,
        x=concept_names,
        y=industry_names,
        colorscale='Reds',
        hoverongaps=False,
        hovertemplate='<b>%{y} × %{x}</b><br>热度: %{z:.1f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="🔥 行业×概念热点矩阵",
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title="概念板块",
        yaxis_title="行业板块",
        xaxis_tickangle=-45,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

# ==================== 智能分析函数 ====================
def generate_comprehensive_analysis(df, scoring_system):
    """生成综合分析"""
    if len(df) == 0:
        return "暂无有效数据"
    
    latest = df.iloc[-1]
    analysis_parts = []
    
    # 量价分析
    if '全天总额' in df.columns and len(df) >= 5:
        volume = latest['全天总额']
        volume_ma5 = df['全天总额'].tail(5).mean()
        volume_ratio = volume / volume_ma5
        
        if volume_ratio > 1.3:
            analysis_parts.append(f"🚀 **量能充沛**：成交{volume:,.0f}亿，较5日均值放大{volume_ratio-1:.0%}")
        elif volume_ratio > 1.1:
            analysis_parts.append(f"📈 **温和放量**：成交{volume:,.0f}亿，资金参与积极")
        elif volume_ratio < 0.8:
            analysis_parts.append(f"📉 **量能萎缩**：成交{volume:,.0f}亿，观望情绪浓厚")
        else:
            analysis_parts.append(f"📊 **量能平稳**：成交{volume:,.0f}亿，市场运行稳健")
    
    # 资金面分析
    if '北向净值' in df.columns:
        north_flow = latest['北向净值']
        if len(df) >= 3:
            if all(x > 0 for x in df['北向净值'].tail(3)):
                north_trend = "持续流入"
            elif all(x < 0 for x in df['北向净值'].tail(3)):
                north_trend = "持续流出"
            else:
                north_trend = "震荡"
        else:
            north_trend = "未知"
            
        if north_flow > 50:
            analysis_parts.append(f"💰 **外资抢筹**：北向净流入{north_flow:.0f}亿，{north_trend}")
        elif north_flow > 20:
            analysis_parts.append(f"🌊 **外资看好**：北向净流入{north_flow:.0f}亿，{north_trend}")
        elif north_flow < -30:
            analysis_parts.append(f"💨 **外资撤离**：北向净流出{abs(north_flow):.0f}亿，{north_trend}")
    
    # 市场广度分析
    if all(col in df.columns for col in ['上涨', '下跌']):
        up_ratio = latest['上涨'] / (latest['上涨'] + latest['下跌'] + 1)
        if up_ratio > 0.7:
            analysis_parts.append(f"🌞 **普涨格局**：上涨家数占比{up_ratio:.0%}")
        elif up_ratio < 0.3:
            analysis_parts.append(f"🌧️ **普跌格局**：下跌家数占比{1-up_ratio:.0%}")
        else:
            analysis_parts.append(f"⚖️ **分化格局**：涨跌家数相对均衡")
    
    # 涨停板分析
    if '全天涨停' in df.columns:
        limit_up = latest['全天涨停']
        board_rate = latest.get('全天封板率', 0)
        
        if limit_up > 80:
            analysis_parts.append(f"🔥 **涨停潮现**：{limit_up}家涨停，封板率{board_rate:.1%}")
        elif limit_up > 50:
            analysis_parts.append(f"🎯 **涨停活跃**：{limit_up}家涨停，赚钱效应良好")
        elif limit_up < 20:
            analysis_parts.append(f"💤 **涨停稀少**：仅{limit_up}家涨停，市场谨慎")
    
    return " | ".join(analysis_parts)

def generate_ai_strategy_recommendation(total_score, factor_scores):
    """生成AI策略建议"""
    recommendations = []
    
    # 总体策略
    if total_score >= 80:
        recommendations.append(("🎯 **积极进攻**", "市场多因素向好，可适度提高仓位参与主线", COLOR_SCHEME['success']))
    elif total_score >= 65:
        recommendations.append(("📈 **适度乐观**", "市场表现稳健，可均衡配置优质标的", COLOR_SCHEME['info']))
    elif total_score >= 45:
        recommendations.append(("⚖️ **稳健平衡**", "市场多空交织，建议精选个股控制仓位", COLOR_SCHEME['neutral']))
    elif total_score >= 30:
        recommendations.append(("🛡️ **谨慎防御**", "市场风险上升，建议降低仓位等待时机", COLOR_SCHEME['warning']))
    else:
        recommendations.append(("💀 **极度保守**", "市场环境恶劣，严格控制风险保持现金", COLOR_SCHEME['error']))
    
    # 具体因子建议
    factor_names = {
        'volume': '成交额', 
        'north_money': '北向资金', 
        'advance_decline': '涨跌家数',
        'limit_up': '涨停板', 
        'market_cap': '市值分布',
        'sector_rotation': '板块轮动', 
        'sentiment': '市场情绪'
    }
    
    weak_factors = [k for k, v in factor_scores.items() if v < 40]
    strong_factors = [k for k, v in factor_scores.items() if v > 70]
    
    if weak_factors:
        weak_list = [factor_names.get(f, f) for f in weak_factors]
        recommendations.append(("⚠️ **关注短板**", f"需关注: {', '.join(weak_list)}", COLOR_SCHEME['warning']))
    
    if strong_factors:
        strong_list = [factor_names.get(f, f) for f in strong_factors if f in factor_names]
        if strong_list:
            recommendations.append(("💡 **优势明显**", f"亮点: {', '.join(strong_list)}", COLOR_SCHEME['success']))
    
    return recommendations

# ==================== 主界面 ====================
def show_daily_report(df):
    """主报告界面"""
    if df.empty:
        st.warning('暂无数据')
        return
        
    df = df.sort_values('日期').reset_index(drop=True)
    latest = df.iloc[-1]
    
    # 初始化评分系统
    scoring_system = MarketScoringSystem()
    total_score, factor_scores = scoring_system.calculate_comprehensive_score(df)
    
    # 报告头部
    st.markdown(f"##  智能市场日报 · {latest['日期'].strftime('%Y-%m-%d')}")
    st.markdown("---")
    
    # 1. 综合评分与多维度分析并列显示    
    col_score, col_radar = st.columns([1, 1])

    with col_score:
        score_fig = create_score_gauge(total_score, "综合评分", COLOR_SCHEME['primary'])
        st.plotly_chart(score_fig, use_container_width=True)

    with col_radar:
        # 雷达图展示各维度评分
        categories = {
            'volume': '成交额',
            'north_money': '北向资金', 
            'advance_decline': '涨跌家数',
            'limit_up': '涨停板',
            'market_cap': '市值分布',
            'sector_rotation': '板块轮动',
            'sentiment': '市场情绪'
        }
        radar_fig = create_modern_radar_chart(factor_scores, categories)
        st.plotly_chart(radar_fig, use_container_width=True)
    
    # 2. 六维市场透视    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        to = analyze_turnover(df)
        st.metric(label='💰 成交额', value=f"{to['value']:,.0f}亿", 
                 delta=f"{to['ratio']:.1%} vs 5日均")
        st.caption(f"状态：{get_chinese_level(to['level'])}")
    
    with col2:
        no = analyze_north(df)
        st.metric(label='🌊 北向净值', value=f"{no['value']:+.1f}亿", 
                 delta=get_chinese_level(no['level']))
        st.caption(f"状态：{get_chinese_level(no['level'])}")
    
    with col3:
        ud = analyze_up_down(df)
        st.metric(label='📈 涨跌比', value=f"{ud['up']}↑ {ud['down']}↓", 
                 delta=f"{ud['ratio']:.1%}")
        st.caption(f"状态：{get_chinese_level(ud['level'])}")

    col4, col5, col6 = st.columns(3)
    
    with col4:
        lu = analyze_limit_up(df)
        st.metric(label='🎯 涨停/跌停', value=f"{lu['limit_up']}/{lu['limit_down']}", 
                 delta=f"{lu['ratio']:.1f}")
        st.caption(f"状态：{get_chinese_level(lu['level'])}")
    
    with col5:
        cap = analyze_cap_dist(df)
        if cap:
            st.markdown('🏦 市值分布（涨停）')
            st.caption(' | '.join([f"{k.replace('涨停板','')}: {int(v)}" for k, v in cap.items()]))
        else:
            st.caption('暂无市值分布')
    
    with col6:
        rot = analyze_sector_rotation(df)
        if rot:
            st.markdown('🔄 行业涨停前3')
            st.caption(' | '.join([f"{d['name']}({d['count']})" for d in rot[:3]]))
        else:
            st.caption('暂无板块数据')
    
    # 3. 市场情绪指标（新增板块）
    st.markdown("###  市场情绪指标")
    
    # 计算情绪指标
    sentiment_data = analyze_market_sentiment(df)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        sentiment_fig = create_sentiment_gauge(sentiment_data)
        st.plotly_chart(sentiment_fig, use_container_width=True)
    
    with col2:
        st.markdown(f"#### 情绪状态: **{sentiment_data['level']}**")
        st.markdown(f"**趋势判断**: {sentiment_data['trend']}")
        st.markdown("**关键因子**:")
        
        factors = sentiment_data['factors']
        for factor, value in factors.items():
            delta_symbol = "📈" if value > 0 else "📉" if value < 0 else "➖"
            st.write(f"{delta_symbol} {factor}: {'+' if value > 0 else ''}{value}分")
        
        st.progress(sentiment_data['score']/100)
        st.caption(f"情绪综合得分: {sentiment_data['score']:.1f}/100")
    
    # 4. 详细分析
    st.markdown("### 🔍 详细市场分析")
    analysis = generate_comprehensive_analysis(df, scoring_system)
    st.info(analysis)
    
    # 5. AI策略建议
    st.markdown("### 💡 AI策略建议")
    recommendations = generate_ai_strategy_recommendation(total_score, factor_scores)
    
    for title, desc, color in recommendations:
        st.markdown(
            f'<div style="background-color: {color}; color: white; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0;">'
            f'<h4 style="margin:0; color:white;">{title}</h4>'
            f'<p style="margin:0.5rem 0 0 0; color:white;">{desc}</p>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    # 6. 市值分布与板块热点
    st.markdown("###  市值分布与板块热点")

    col1, col2 = st.columns(2)

    with col1:
        # 市值分布气泡图
        bubble_fig = create_market_cap_bubble(df)
        if bubble_fig:
            st.plotly_chart(bubble_fig, use_container_width=True)
        else:
            st.info("暂无市值分布数据")

    with col2:
        # 行业概念热点图
        heatmap_fig = create_sector_concept_heatmap(df)
        if heatmap_fig:
            st.plotly_chart(heatmap_fig, use_container_width=True)
        else:
            st.info("暂无板块热点数据")
    
    # 7. 特色分析图表
    st.markdown("###  特色分析")
    col1, col2 = st.columns(2)
    
    with col1:        
        cap_fig = create_market_cap_analysis(df)
        if cap_fig:
            st.plotly_chart(cap_fig, use_container_width=True)
        else:
            st.info("暂无市值分布数据")
    
    with col2:
                
        # 创建评分条状图 - 红涨绿跌配色
        score_df = pd.DataFrame({
            '维度': list(categories.values()),
            '评分': [factor_scores.get(k, 50) for k in categories.keys()]
        })
        
        # 根据评分高低设置颜色：高于50分用红色系，低于50分用绿色系
        colors = []
        color_scale = []  # 用于颜色条
        for score in score_df['评分']:
            if score >= 70:
                colors.append(COLOR_SCHEME['hot'])      # 深红 - 优秀
                color_scale.append(4)
            elif score >= 60:
                colors.append(COLOR_SCHEME['warning'])  # 橙色 - 良好
                color_scale.append(3)
            elif score >= 50:
                colors.append(COLOR_SCHEME['neutral'])  # 绿色 - 中性
                color_scale.append(2)
            elif score >= 40:
                colors.append(COLOR_SCHEME['cool'])     # 青色 - 偏弱
                color_scale.append(1)
            else:
                colors.append(COLOR_SCHEME['cold'])     # 靛蓝 - 弱势
                color_scale.append(0)
        
        # 按评分排序，让高分在上方
        score_df = score_df.sort_values('评分', ascending=True)
        colors = [colors[i] for i in score_df.index]  # 重新排列颜色
        color_scale = [color_scale[i] for i in score_df.index]  # 重新排列颜色等级
        
        # 使用连续颜色映射来显示颜色条
        fig = px.bar(
            score_df, 
            x='评分', 
            y='维度', 
            orientation='h',
            text='评分',
            color=color_scale,  # 使用颜色等级
            color_continuous_scale=[COLOR_SCHEME['cold'], COLOR_SCHEME['cool'], 
                                   COLOR_SCHEME['neutral'], COLOR_SCHEME['warning'], 
                                   COLOR_SCHEME['hot']],
            range_color=[0, 4]
        )
        
        # 更新颜色条设置
        fig.update_traces(
            texttemplate='%{x:.1f}',
            textposition='outside'
        )
        
        fig.update_layout(
            height=300,
            showlegend=False,
            xaxis_range=[0, 100],
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis={'categoryorder': 'total ascending'},
            coloraxis_colorbar=dict(
                title="评分等级",
                tickvals=[0, 1, 2, 3, 4],
                ticktext=['弱势', '偏弱', '中性', '良好', '优秀'],
                len=0.8,
                y=0.1,
                yanchor='bottom'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 添加颜色说明
        st.caption("🎨 颜色说明：红色系表示表现优秀，绿色系表示表现中性，蓝色系表示需要关注")
    
    # 8. 最近8日明细
    st.markdown("### 📋 最近8日明细")
    cols_to_show = ['日期', '全天总额', '今昨差额', '北向净值', '全天涨停', '全天跌停', '全天封板率', '上涨', '下跌', '平盘']

    # 检查哪些列实际存在
    available_cols = [c for c in cols_to_show if c in df.columns]

    if available_cols:
        recent = df[available_cols].tail(8).iloc[::-1]  # 反转，让最新的在顶部
        
        # 格式化数字显示
        def format_numbers(val):
            if isinstance(val, (int, float)):
                if '总额' in str(val) or '差额' in str(val):
                    return f'{val:,.0f}'
                elif '净值' in str(val):
                    return f'{val:+.1f}'
                elif '率' in str(val):
                    return f'{val:.1%}'
            return val
        
        # 创建样式化的DataFrame
        styled_df = recent.copy()
        for col in styled_df.columns:
            if col != '日期':
                styled_df[col] = styled_df[col].apply(format_numbers)
        
        st.dataframe(
            styled_df,
            use_container_width=True, 
            height=350
        )
    else:
        st.warning("暂无明细数据可用")
        # 显示可用的列供参考
        st.info(f"数据集中存在的列: {list(df.columns)}")

    # 9. 交互功能
    st.markdown("---")
    with st.expander("🔧 高级分析工具", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 更新分析", use_container_width=True):
                st.rerun()
        
        with col2:
            if st.button("📊 评分详情", use_container_width=True):
                st.write("### 各维度评分详情")
                for factor, score in factor_scores.items():
                    st.write(f"- {categories.get(factor, factor)}: {score:.1f}分")
        
        with col3:
            if st.button("💾 导出报告", use_container_width=True):
                st.info("报告导出功能开发中...")

    st.markdown('---')
    st.caption('报告基于历史数据，投资有风险，决策需谨慎。')

# ==================== 兼容函数 ====================
def generate_market_summary(df):
    """生成市场摘要"""
    scoring_system = MarketScoringSystem()
    return generate_comprehensive_analysis(df, scoring_system)

def generate_trading_advice(df):
    """生成交易建议"""
    scoring_system = MarketScoringSystem()
    total_score, factor_scores = scoring_system.calculate_comprehensive_score(df)
    recommendations = generate_ai_strategy_recommendation(total_score, factor_scores)
    
    if recommendations:
        return recommendations[0][1]
    return "市场表现平稳，建议均衡配置"