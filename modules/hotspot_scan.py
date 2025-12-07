# modules/hotspot_scan.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta
from modules import data_processing

# ==================== 第一阶段：基础解析和共现矩阵 ====================

def parse_hot_limit_enhanced(s: str):
    """增强解析：把 '元器件10+6' 拆成 ('元器件', 10, 6)"""
    items = []
    try:
        for item in s.split("\\"):
            item = item.strip()
            if not item:
                continue
                
            if "+" in item:
                # 分离名称和数字部分
                name_part = item.rsplit("+", 1)[0]
                num_part = item.rsplit("+", 1)[1]
                
                # 提取名称（去除末尾数字）
                import re
                name = re.sub(r'\d+$', '', name_part).strip()
                
                # 提取涨停数和涨幅大于10%数
                limit_up_match = re.findall(r'\d+', name_part)
                limit_up = int(limit_up_match[-1]) if limit_up_match else 0
                rise_over_10 = int(num_part) if num_part.isdigit() else 0
                
                items.append((name, limit_up, rise_over_10))
            else:
                # 没有+的情况，尝试提取名称和数字
                import re
                matches = re.findall(r'(\D+)(\d+)', item)
                if matches:
                    name = matches[0][0].strip()
                    limit_up = int(matches[0][1])
                    items.append((name, limit_up, 0))
                else:
                    items.append((item.strip(), 1, 0))
    except Exception as e:
        st.error(f"解析热点数据时出错: {str(e)}")
        return [("解析错误", 1, 0)]
    
    return items

def create_cooccurrence_heatmap(industry_str: str, concept_str: str, method="combined_strength"):
    """创建基于共现原理的热力图"""
    try:
        ind_list = parse_hot_limit_enhanced(industry_str or "")
        conc_list = parse_hot_limit_enhanced(concept_str or "")
        
        if not ind_list or not conc_list:
            return None
            
        # 构建共现矩阵
        heat_data = []
        hover_text = []
        
        for industry_name, ind_limit, ind_rise in ind_list:
            row = []
            hover_row = []
            for concept_name, conc_limit, conc_rise in conc_list:
                if method == "geometric_mean":
                    # 几何平均 - 更合理的关联度计算
                    value = (ind_limit * conc_limit) ** 0.5
                elif method == "min_normalized":
                    # 最小值归一化
                    value = min(ind_limit, conc_limit)
                elif method == "combined_strength":
                    # 综合强度：考虑涨停数和涨幅大于10%的数量
                    total_ind = ind_limit + ind_rise * 0.5  # 涨幅大于10%给予0.5的权重
                    total_conc = conc_limit + conc_rise * 0.5
                    value = (total_ind * total_conc) ** 0.5
                elif method == "jaccard_similarity":
                    # 近似Jaccard相似度
                    union = ind_limit + conc_limit - min(ind_limit, conc_limit)
                    value = min(ind_limit, conc_limit) / union if union > 0 else 0
                else:
                    # 默认使用综合强度
                    total_ind = ind_limit + ind_rise * 0.5
                    total_conc = conc_limit + conc_rise * 0.5
                    value = (total_ind * total_conc) ** 0.5
                
                row.append(round(value, 2))
                hover_row.append(
                    f"行业: {industry_name}<br>" +
                    f"概念: {concept_name}<br>" +
                    f"行业涨停: {ind_limit}+{ind_rise}<br>" +
                    f"概念涨停: {conc_limit}+{conc_rise}<br>" +
                    f"共现强度: {value:.2f}"
                )
            
            heat_data.append(row)
            hover_text.append(hover_row)
        
        # 创建DataFrame
        heat_df = pd.DataFrame(
            heat_data,
            index=[i[0] for i in ind_list],
            columns=[c[0] for c in conc_list]
        )
        
        # 创建热力图
        fig = go.Figure(go.Heatmap(
            z=heat_df.values,
            x=heat_df.columns,
            y=heat_df.index,
            colorscale="Reds",
            text=heat_df.values,
            texttemplate="%{z:.1f}",
            customdata=hover_text,
            hovertemplate="%{customdata}<extra></extra>"
        ))
        
        method_names = {
            "geometric_mean": "几何平均",
            "min_normalized": "最小值归一化", 
            "combined_strength": "综合强度",
            "jaccard_similarity": "相似度"
        }
        
        fig.update_layout(
            height=400,
            margin=dict(l=50, r=50, t=50, b=50),
            xaxis_title="概念",
            yaxis_title="行业",
            xaxis_tickangle=-45,
            title=f"涨停榜热力图 - 共现矩阵分析 ({method_names.get(method, '综合强度')})"
        )
        
        return fig
    except Exception as e:
        st.error(f"创建共现热力图时出错: {str(e)}")
        return None

def create_rank_cooccurrence_heatmap(industry_str: str, concept_str: str, title: str = "涨幅榜热力图"):
    """创建基于排名的共现热力图（用于涨幅榜）"""
    try:
        # 解析行业和概念列表（涨幅榜只有名称，没有数字）
        industries = [item.strip() for item in industry_str.split('\\') if item.strip()]
        concepts = [item.strip() for item in concept_str.split('\\') if item.strip()]
        
        if not industries or not concepts:
            return None
        
        # 创建基于排名的共现矩阵
        heat_data = []
        hover_text = []
        
        for i, industry in enumerate(industries):
            row = []
            hover_row = []
            for j, concept in enumerate(concepts):
                # 使用排名衰减因子：排名越靠前，关联度越高
                industry_rank_factor = 1.0 / (i + 1)  # 第1名=1.0, 第2名=0.5, 第3名=0.33...
                concept_rank_factor = 1.0 / (j + 1)
                
                # 共现强度 = 行业排名因子 × 概念排名因子
                cooccurrence_strength = industry_rank_factor * concept_rank_factor * 10
                
                row.append(round(cooccurrence_strength, 2))
                hover_row.append(
                    f"行业: {industry} (排名{i+1})<br>" +
                    f"概念: {concept} (排名{j+1})<br>" +
                    f"共现强度: {cooccurrence_strength:.2f}"
                )
            
            heat_data.append(row)
            hover_text.append(hover_row)
        
        # 创建热力图
        fig = go.Figure(go.Heatmap(
            z=heat_data,
            x=concepts,
            y=industries,
            colorscale="Reds",
            text=[[f"{cooccurrence_strength:.1f}" for cooccurrence_strength in row] for row in heat_data],
            texttemplate="%{text}",
            customdata=hover_text,
            hovertemplate="%{customdata}<extra></extra>"
        ))
        
        fig.update_layout(
            height=400,
            margin=dict(l=50, r=50, t=50, b=50),
            xaxis_title="概念",
            yaxis_title="行业",
            xaxis_tickangle=-45,
            title=f"{title} - 排名共现分析"
        )
        
        return fig
    except Exception as e:
        st.error(f"创建排名共现热力图时出错: {str(e)}")
        return None

# ==================== 第二阶段：时间序列分析 ====================

def temporal_cooccurrence_analysis(recent_df, min_strength=2.0, min_days=2):
    """时间序列共现分析 - 发现持续性热点"""
    
    # 收集所有交易日的数据
    temporal_data = []
    
    for _, row in recent_df.iterrows():
        date = row['日期'] if '日期' in row else "未知日期"
        
        # 解析当日的行业和概念涨停数据
        if pd.notna(row.get('行业涨停榜')) and pd.notna(row.get('概念涨停榜')):
            industries = parse_hot_limit_enhanced(str(row['行业涨停榜']))
            concepts = parse_hot_limit_enhanced(str(row['概念涨停榜']))
            
            # 计算当日的共现强度
            for industry_name, ind_limit, ind_rise in industries:
                for concept_name, conc_limit, conc_rise in concepts:
                    # 计算综合强度
                    total_ind = ind_limit + ind_rise * 0.5
                    total_conc = conc_limit + conc_rise * 0.5
                    strength = (total_ind * total_conc) ** 0.5
                    
                    if strength >= min_strength:
                        temporal_data.append({
                            'date': date,
                            'industry': industry_name,
                            'concept': concept_name,
                            'industry_limit': ind_limit,
                            'industry_rise': ind_rise,
                            'concept_limit': conc_limit,
                            'concept_rise': conc_rise,
                            'strength': round(strength, 2),
                            'industry_concept': f"{industry_name}×{concept_name}"
                        })
    
    if not temporal_data:
        return None, None, None, None
    
    # 创建时间序列DataFrame
    temporal_df = pd.DataFrame(temporal_data)
    
    # 分析持续性热点
    persistence_analysis = analyze_persistence(temporal_df, min_days)
    
    # 生成时间序列可视化
    timeline_fig = create_timeline_chart(temporal_df)
    persistence_fig = create_persistence_chart(persistence_analysis)
    heatmap_fig = create_temporal_heatmap(temporal_df)
    
    return temporal_df, timeline_fig, persistence_fig, heatmap_fig

def analyze_persistence(temporal_df, min_days=2):
    """分析热点持续性"""
    
    # 计算每个行业-概念组合的出现天数
    persistence_stats = temporal_df.groupby('industry_concept').agg({
        'date': 'nunique',
        'strength': ['mean', 'max', 'min'],
        'industry': 'first',
        'concept': 'first'
    }).round(2)
    
    # 扁平化列名
    persistence_stats.columns = ['days_count', 'strength_mean', 'strength_max', 'strength_min', 'industry', 'concept']
    persistence_stats = persistence_stats.reset_index()
    
    # 过滤出持续出现的热点
    persistent_hotspots = persistence_stats[persistence_stats['days_count'] >= min_days].copy()
    persistent_hotspots = persistent_hotspots.sort_values(['days_count', 'strength_mean'], ascending=[False, False])
    
    return persistent_hotspots

def create_timeline_chart(temporal_df):
    """创建时间序列趋势图"""
    
    # 选择强度最高的几个组合来显示，避免过于拥挤
    top_combinations = temporal_df.groupby('industry_concept')['strength'].max().nlargest(8).index
    
    filtered_df = temporal_df[temporal_df['industry_concept'].isin(top_combinations)]
    
    fig = px.line(
        filtered_df, 
        x='date', 
        y='strength', 
        color='industry_concept',
        title='📈 热点组合强度时间序列',
        labels={'strength': '共现强度', 'date': '日期', 'industry_concept': '行业×概念'}
    )
    
    fig.update_layout(
        height=400,
        xaxis_title="日期",
        yaxis_title="共现强度",
        legend_title="热点组合",
        hovermode='x unified'
    )
    
    return fig

def create_persistence_chart(persistence_df):
    """创建持续性热点图表"""
    
    if persistence_df.empty:
        return None
    
    # 取前15个持续性热点
    top_persistent = persistence_df.head(15)
    
    fig = px.bar(
        top_persistent,
        x='strength_mean',
        y='industry_concept',
        orientation='h',
        title='🔥 持续性热点排行榜',
        labels={'strength_mean': '平均共现强度', 'industry_concept': '行业×概念组合'},
        color='days_count',
        color_continuous_scale='Reds'
    )
    
    fig.update_layout(
        height=500,
        xaxis_title="平均共现强度",
        yaxis_title="",
        showlegend=False
    )
    
    # 添加天数标注
    for i, row in enumerate(top_persistent.itertuples()):
        fig.add_annotation(
            x=row.strength_mean + 0.1,
            y=row.industry_concept,
            text=f"{row.days_count}天",
            showarrow=False,
            font=dict(size=10)
        )
    
    return fig

def create_temporal_heatmap(temporal_df):
    """创建时间序列热力图"""
    
    # 创建数据透视表
    pivot_data = temporal_df.pivot_table(
        index='industry_concept',
        columns='date',
        values='strength',
        aggfunc='mean'
    ).fillna(0)
    
    # 选择出现天数最多的组合
    if len(pivot_data) > 20:
        # 按出现天数排序（非空列数）
        pivot_data['days_count'] = (pivot_data > 0).sum(axis=1)
        pivot_data = pivot_data.nlargest(20, 'days_count')
        pivot_data = pivot_data.drop('days_count', axis=1)
    
    if pivot_data.empty:
        return None
    
    fig = go.Figure(go.Heatmap(
        z=pivot_data.values,
        x=pivot_data.columns.astype(str),
        y=pivot_data.index,
        colorscale="Reds",
        hovertemplate="<b>%{y}</b><br>日期: %{x}<br>强度: %{z:.2f}<extra></extra>"
    ))
    
    fig.update_layout(
        height=600,
        title="📅 热点组合时间序列热力图",
        xaxis_title="日期",
        yaxis_title="行业×概念组合",
        xaxis_tickangle=-45
    )
    
    return fig

def create_sector_rotation_chart(temporal_df):
    """创建板块轮动分析图"""
    
    # 分析行业轮动
    industry_rotation = temporal_df.groupby(['date', 'industry']).agg({
        'strength': 'sum'
    }).reset_index()
    
    # 选择活跃行业
    active_industries = industry_rotation.groupby('industry')['strength'].sum().nlargest(10).index
    filtered_industry = industry_rotation[industry_rotation['industry'].isin(active_industries)]
    
    fig_industry = px.line(
        filtered_industry,
        x='date',
        y='strength',
        color='industry',
        title='🔄 行业轮动分析',
        labels={'strength': '行业总强度', 'date': '日期', 'industry': '行业'}
    )
    
    fig_industry.update_layout(height=400)
    
    # 分析概念轮动
    concept_rotation = temporal_df.groupby(['date', 'concept']).agg({
        'strength': 'sum'
    }).reset_index()
    
    active_concepts = concept_rotation.groupby('concept')['strength'].sum().nlargest(10).index
    filtered_concept = concept_rotation[concept_rotation['concept'].isin(active_concepts)]
    
    fig_concept = px.line(
        filtered_concept,
        x='date',
        y='strength',
        color='concept',
        title='🔄 概念轮动分析',
        labels={'strength': '概念总强度', 'date': '日期', 'concept': '概念'}
    )
    
    fig_concept.update_layout(height=400)
    
    return fig_industry, fig_concept

# ==================== 主界面函数 ====================

def show_daily_analysis(recent_df):
    """显示单日热点分析（第一阶段的功能）"""
    
    st.markdown(
        '<div style="color: #ff6b00 !important; font-size: 16px; font-weight: bold; margin: 20px 0 10px 0;">📋 详细热点排行</div>',
        unsafe_allow_html=True
    )

    # 创建标签页显示不同日期的热点
    if len(recent_df) > 0:
        tab_titles = []
        for _, row in recent_df.iterrows():
            if '日期' in row:
                date_val = row['日期']
                if hasattr(date_val, 'strftime'):
                    tab_titles.append(f"📅 {date_val.strftime('%m-%d')}")
                else:
                    tab_titles.append(f"📅 {str(date_val)[5:10]}")
            else:
                tab_titles.append(f"📅 第{_+1}天")

        date_tabs = st.tabs(tab_titles)

        for tab_idx, (_, row) in enumerate(zip(date_tabs, recent_df.iterrows())):
            _, row_data = row
            with date_tabs[tab_idx]:
                # 显示日期
                if '日期' in row_data:
                    date_str = row_data['日期'].strftime('%Y-%m-%d') if hasattr(row_data['日期'], 'strftime') else str(row_data['日期'])
                    st.markdown(f"#### 🗓️ {date_str} 市场热点分布")
                else:
                    st.markdown(f"#### 🗓️ 交易日 {tab_idx+1} 市场热点分布")

                # 四列布局显示各类榜单
                col1, col2, col3, col4 = st.columns(4)

                # 行业涨幅榜
                with col1:
                    st.markdown("**🏆 行业涨幅榜**")
                    if pd.notna(row_data.get('行业涨幅榜')):
                        industries = str(row_data['行业涨幅榜']).split('\\')
                        for i, industry in enumerate(industries[:8]):
                            if industry.strip():
                                st.markdown(f"<div style='color: #ff6b00; font-size: 14px;'>{i+1}. {industry.strip()}</div>", 
                                          unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='color: #ff6b00;'>暂无数据</div>", unsafe_allow_html=True)

                # 概念涨幅榜
                with col2:
                    st.markdown("**🎯 概念涨幅榜**")
                    if pd.notna(row_data.get('概念涨幅榜')):
                        concepts = str(row_data['概念涨幅榜']).split('\\')
                        for i, concept in enumerate(concepts[:8]):
                            if concept.strip():
                                st.markdown(f"<div style='color: #ff6b00; font-size: 14px;'>{i+1}. {concept.strip()}</div>", 
                                          unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='color: #ff6b00;'>暂无数据</div>", unsafe_allow_html=True)

                # 行业涨停榜（带详细数据）
                with col3:
                    st.markdown("**🔥 行业涨停榜**")
                    if pd.notna(row_data.get('行业涨停榜')):
                        limit_industries = str(row_data['行业涨停榜']).split('\\')
                        for i, industry in enumerate(limit_industries[:8]):
                            if industry.strip():
                                industry_data = parse_hot_limit_enhanced(industry)
                                if industry_data:
                                    name, limit_up, rise_over_10 = industry_data[0]
                                    display_text = f"{name} ({limit_up}+{rise_over_10})"
                                else:
                                    display_text = industry.strip()
                                st.markdown(f"<div style='color: #ff6b00; font-size: 14px;'>{i+1}. {display_text}</div>", 
                                          unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='color: #ff6b00;'>暂无数据</div>", unsafe_allow_html=True)

                # 概念涨停榜（带详细数据）
                with col4:
                    st.markdown("**💥 概念涨停榜**")
                    if pd.notna(row_data.get('概念涨停榜')):
                        limit_concepts = str(row_data['概念涨停榜']).split('\\')
                        for i, concept in enumerate(limit_concepts[:8]):
                            if concept.strip():
                                concept_data = parse_hot_limit_enhanced(concept)
                                if concept_data:
                                    name, limit_up, rise_over_10 = concept_data[0]
                                    display_text = f"{name} ({limit_up}+{rise_over_10})"
                                else:
                                    display_text = concept.strip()
                                st.markdown(f"<div style='color: #ff6b00; font-size: 14px;'>{i+1}. {display_text}</div>", 
                                          unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='color: #ff6b00;'>暂无数据</div>", unsafe_allow_html=True)

            
                # 热力图部分
                st.markdown("---")
                st.markdown("#### 🔥 热点关联分析 - 共现矩阵")
                
                # 共现算法选择
                col_method1, col_method2 = st.columns(2)
                with col_method1:
                    rank_method = st.selectbox(
                        "涨幅榜算法", 
                        ["排名衰减", "几何平均", "综合强度"],
                        index=0,
                        key=f"rank_method_{tab_idx}"
                    )
                with col_method2:
                    limit_method = st.selectbox(
                        "涨停榜算法",
                        ["综合强度", "几何平均", "最小值归一化", "相似度"],
                        index=0,
                        key=f"limit_method_{tab_idx}"
                    )

                # 两列热力图布局
                col1, col2 = st.columns(2)

                # 涨幅榜热力图
                with col1:
                    if pd.notna(row_data.get('行业涨幅榜')) and pd.notna(row_data.get('概念涨幅榜')):
                        if rank_method == "排名衰减":
                            fig_rank = create_rank_cooccurrence_heatmap(
                                str(row_data['行业涨幅榜']),
                                str(row_data['概念涨幅榜']),
                                title="涨幅榜热力图"
                            )
                        else:
                            fig_rank = create_cooccurrence_heatmap(
                                str(row_data['行业涨幅榜']),
                                str(row_data['概念涨幅榜']),
                                method=rank_method.lower().replace(" ", "_")
                            )
                        
                        if fig_rank:
                            st.plotly_chart(fig_rank, use_container_width=True)
                    else:
                        st.markdown("<div style='color: #ff6b00;'>涨幅榜数据不完整</div>", unsafe_allow_html=True)

                # 涨停榜热力图
                with col2:
                    if pd.notna(row_data.get('行业涨停榜')) and pd.notna(row_data.get('概念涨停榜')):
                        fig_limit = create_cooccurrence_heatmap(
                            str(row_data['行业涨停榜']),
                            str(row_data['概念涨停榜']),
                            method=limit_method.lower().replace(" ", "_")
                        )
                        if fig_limit:
                            st.plotly_chart(fig_limit, use_container_width=True)
                    else:
                        st.markdown("<div style='color: #ff6b00;'>涨停榜数据不完整</div>", unsafe_allow_html=True)

    else:
        st.markdown("<div style='color: #ff6b00;'>没有足够的数据显示热点扫描</div>", unsafe_allow_html=True)

def show_temporal_analysis(recent_df, display_days):
    """显示时间序列分析"""
    
    st.markdown(
        '<div style="color: #ff6b00 !important; font-size: 16px; font-weight: bold; margin: 20px 0 10px 0;">📈 时间序列共现分析</div>',
        unsafe_allow_html=True
    )
    
    # 参数设置
    col1, col2, col3 = st.columns(3)
    with col1:
        min_strength = st.slider("最小强度阈值", 0.0, 10.0, 2.0, 0.5, key="min_strength")
    with col2:
        min_days = st.slider("最小持续天数", 1, display_days, 2, 1, key="min_days")
    with col3:
        analysis_type = st.selectbox(
            "分析类型",
            ["持续性热点", "轮动分析", "时间序列热力图"],
            key="analysis_type"
        )
    
    # 执行时间序列分析
    with st.spinner("进行时间序列共现分析..."):
        temporal_df, timeline_fig, persistence_fig, heatmap_fig = temporal_cooccurrence_analysis(
            recent_df, min_strength, min_days
        )
    
    if temporal_df is None:
        st.warning("没有找到符合条件的时间序列数据，请调整筛选参数。")
        return
    
    # 显示分析结果
    if analysis_type == "持续性热点":
        st.markdown("#### 🔥 持续性热点排行榜")
        if persistence_fig:
            st.plotly_chart(persistence_fig, use_container_width=True)
        else:
            st.info("没有找到持续性热点")
        
        # 显示时间序列趋势
        if timeline_fig:
            st.markdown("#### 📈 热点组合强度变化")
            st.plotly_chart(timeline_fig, use_container_width=True)
    
    elif analysis_type == "轮动分析":
        st.markdown("#### 🔄 板块轮动分析")
        industry_fig, concept_fig = create_sector_rotation_chart(temporal_df)
        
        if industry_fig:
            st.plotly_chart(industry_fig, use_container_width=True)
        if concept_fig:
            st.plotly_chart(concept_fig, use_container_width=True)
    
    elif analysis_type == "时间序列热力图":
        st.markdown("#### 📅 时间序列热力图")
        if heatmap_fig:
            st.plotly_chart(heatmap_fig, use_container_width=True)
        else:
            st.info("无法生成时间序列热力图")
    
    # 显示原始数据
    with st.expander("📊 查看详细数据"):
        st.dataframe(temporal_df, use_container_width=True)
        
        # 统计信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总记录数", len(temporal_df))
        with col2:
            st.metric("独特组合数", temporal_df['industry_concept'].nunique())
        with col3:
            avg_strength = temporal_df['strength'].mean()
            st.metric("平均强度", f"{avg_strength:.2f}")

def show_hotspot_scan(df, uploaded_file, load_data_with_cache):
    """显示热点扫描功能 - 完整版本（包含两个阶段）"""
    
    st.markdown(
        '<div style="color: #ff6b00 !important; font-size: 18px; font-weight: bold; margin-bottom: 20px;">📊 热点扫描与时间序列分析</div>',
        unsafe_allow_html=True
    )

    # 设置显示的交易天数
    col1, col2 = st.columns([1, 3])
    with col1:
        display_days = st.selectbox("显示天数", [5, 10, 15, 20, 30], index=1, key="hotspot_days")

    # 重新加载原始数据
    with st.spinner("加载完整数据中..."):
        raw_df = load_data_with_cache(uploaded_file)
        raw_df = data_processing.filter_non_trading_days(raw_df)
        raw_df = data_processing.validate_and_clean_data(raw_df)

    # 确保数据按日期排序
    if '日期' in raw_df.columns:
        df_sorted = raw_df.sort_values('日期').copy()
    else:
        df_sorted = raw_df.copy()

    # 获取最近的数据并按日期倒序
    recent_df = df_sorted.tail(display_days).copy()
    if '日期' in recent_df.columns:
        recent_df = recent_df.sort_values('日期', ascending=False)
    else:
        recent_df = recent_df.sort_index(ascending=False)

    # 创建主选项卡：单日分析 vs 时间序列分析
    tab1, tab2 = st.tabs(["📅 单日热点分析", "📈 时间序列分析"])

    with tab1:
        show_daily_analysis(recent_df)

    with tab2:
        show_temporal_analysis(recent_df, display_days)