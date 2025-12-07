# modules/data_processing.py (完整修复版)
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta
import streamlit as st

def export_to_excel(df, export_type="当前视图数据"):
    """
    导出数据到Excel文件
    """
    try:
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Sheet 1: 原始数据
            df.to_excel(writer, sheet_name='原始数据', index=False)
            
            # Sheet 2: 技术指标摘要
            technical_summary = generate_technical_summary(df)
            technical_summary.to_excel(writer, sheet_name='技术指标', index=False)
            
            # Sheet 3: 关键指标统计
            key_stats = generate_key_statistics(df)
            key_stats.to_excel(writer, sheet_name='关键指标', index=True)
            
            # Sheet 4: 最近交易日详情
            if len(df) > 0:
                latest_data = pd.DataFrame([df.iloc[-1]]).T
                latest_data.columns = ['最新数值']
                latest_data.to_excel(writer, sheet_name='最新数据')
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        st.error(f"导出Excel时出错: {str(e)}")
        return None

def generate_technical_summary(df):
    """生成技术指标摘要"""
    summary_data = []
    
    # 基础统计
    if '全天总额' in df.columns:
        summary_data.append({
            '指标': '成交额均值',
            '数值': f"{df['全天总额'].mean():,.0f}",
            '单位': '亿元'
        })
    
    if '北向净值' in df.columns:
        summary_data.append({
            '指标': '北向资金均值', 
            '数值': f"{df['北向净值'].mean():.2f}",
            '单位': '亿元'
        })
    
    if '全天涨停' in df.columns:
        summary_data.append({
            '指标': '涨停均值',
            '数值': f"{df['全天涨停'].mean():.0f}",
            '单位': '家'
        })
    
    return pd.DataFrame(summary_data)

def generate_key_statistics(df):
    """生成关键指标统计"""
    stats_data = {}
    
    numeric_columns = df.select_dtypes(include=['number']).columns
    
    for col in numeric_columns[:10]:  # 限制前10个数值列
        if col in df.columns:
            stats_data[col] = {
                '平均值': df[col].mean(),
                '最大值': df[col].max(),
                '最小值': df[col].min(),
                '标准差': df[col].std()
            }
    
    return pd.DataFrame(stats_data).T


# 数据清洗日志记录
cleaning_logs = []

def add_cleaning_log(log_type, count, details):
    """添加数据清洗日志"""
    cleaning_logs.append({
        "清洗类型": log_type,
        "涉及条数": count,
        "具体内容": details,
        "处理时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

def load_and_clean(uploaded_file):
    """加载Excel文件并优化日期解析"""
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0)
        if '日期' in df.columns:
            # 强制解析日期并修复年份
            original_date_count = len(df)
            df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
            # 修复年份（小于2020年的加15年）
            mask = df['日期'].dt.year < 2020
            corrected_year_count = mask.sum()
            if corrected_year_count > 0:
                df.loc[mask, '日期'] = df.loc[mask, '日期'] + pd.DateOffset(years=15)
                add_cleaning_log(
                    "日期年份修复", 
                    corrected_year_count, 
                    f"将{corrected_year_count}条年份<2020的日期加15年"
                )
            # 过滤无效日期（NaT）
            invalid_dates = df['日期'].isna().sum()
            if invalid_dates > 0:
                df = df[df['日期'].notna()].copy()
                add_cleaning_log(
                    "无效日期过滤", 
                    invalid_dates, 
                    f"过滤{invalid_dates}条无法解析的无效日期"
                )
            # 修改：按日期升序排列（从早到晚）
            df = df.sort_values('日期', ascending=True).reset_index(drop=True)
        
        # 处理空值
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        null_count = df[numeric_columns].isna().sum().sum()
        if null_count > 0:
            df[numeric_columns] = df[numeric_columns].fillna(0)
            add_cleaning_log(
                "数值空值填充", 
                null_count, 
                f"将{null_count}个数值型字段空值填充为0"
            )
        return df
    except Exception as e:
        st.error(f"读取文件时出错: {e}")
        add_cleaning_log("文件读取失败", 0, f"错误信息：{str(e)}")
        return None

def filter_non_trading_days(df):
    """过滤非交易日（关键指标全为0的日期）"""
    if df is None or len(df) == 0:
        return df
    
    # 关键交易指标列（用于判断是否为交易日）
    key_columns = ['全天总额', '北向净值', '上涨', '下跌', '全天涨停']
    existing_keys = [col for col in key_columns if col in df.columns]
    
    if not existing_keys:
        add_cleaning_log("非交易日过滤", 0, "未找到关键交易指标列，跳过过滤")
        return df
    
    # 判断是否为交易日：关键指标不全为0
    df['is_trading_day'] = df[existing_keys].apply(
        lambda row: not (row == 0).all(), axis=1
    )
    
    # 统计并显示过滤的非交易日数量
    non_trading_days = df[~df['is_trading_day']].copy()
    non_trading_count = len(non_trading_days)
    if non_trading_count > 0:
        non_trading_days['日期_str'] = non_trading_days['日期'].dt.strftime('%Y-%m-%d').fillna('无效日期')
        non_trading_dates = ', '.join(non_trading_days['日期_str'].tolist())
        add_cleaning_log(
            "非交易日过滤", 
            non_trading_count, 
            f"过滤日期：{non_trading_dates}"
        )
    
    # 返回仅包含交易日的数据（保持升序排列）
    return df[df['is_trading_day']].drop(columns=['is_trading_day']).copy()

def validate_and_clean_data(df):
    """验证数据并确保今昨差额正确计算 """
    # 确保数据按日期升序排列（从早到晚）
    df = df.sort_values('日期', ascending=True).reset_index(drop=True)
    
    # 修正封板率
    if '全天封板率' in df.columns:
        board_rate = df['全天封板率']
        if (board_rate > 1).any():
            corrected_count = (board_rate > 1).sum()
            df['全天封板率'] = df['全天封板率'] / 100
            add_cleaning_log(
                "封板率数值修正", 
                corrected_count, 
                f"将{corrected_count}条>1的封板率数值除以100"
            )
    
    # 补全今昨差额 - 增强计算逻辑
    if '今昨差额' not in df.columns and '全天总额' in df.columns:
        # 按日期升序排列计算差额（正确的时序）
        df_sorted = df.sort_values('日期', ascending=True).copy()
        df_sorted['今昨差额'] = df_sorted['全天总额'].diff()
        df = df_sorted.sort_values('日期', ascending=True).reset_index(drop=True)
        add_cleaning_log(
            "今昨差额补全", 
            len(df), 
            "基于'全天总额'字段计算并补全'今昨差额'列"
        )
    elif '今昨差额' in df.columns:
        # 确保今昨差额不为0（如果数据异常）
        zero_count = (df['今昨差额'] == 0).sum()
        if zero_count > len(df) * 0.8:  # 如果80%以上的数据都是0，重新计算
            df_sorted = df.sort_values('日期', ascending=True).copy()
            df_sorted['今昨差额'] = df_sorted['全天总额'].diff()
            df = df_sorted.sort_values('日期', ascending=True).reset_index(drop=True)
            add_cleaning_log(
                "今昨差额重新计算", 
                zero_count, 
                f"重新计算{zero_count}条为0的今昨差额数据"
            )
    
    # 补全全天总跌停
    if '全天跌停' not in df.columns:
        df['全天跌停'] = 0
        if '主板跌停数' in df.columns:
            df['全天跌停'] += df['主板跌停数'].fillna(0)
        if '创业板跌停数' in df.columns:
            df['全天跌停'] += df['创业板跌停数'].fillna(0)
        if '北证跌停数' in df.columns:
            df['全天跌停'] += df['北证跌停数'].fillna(0)
        
        # 检查是否成功计算了跌停数据
        if (df['全天跌停'] > 0).any():
            add_cleaning_log(
                "全天跌停补全", 
                len(df), 
                "基于各板块跌停数计算全天总跌停"
            )
        else:
            add_cleaning_log(
                "全天跌停初始化", 
                len(df), 
                "初始化全天跌停列为0（无板块跌停数据）"
            )    
   
    
    # 确保涨停板市值分布列存在且为数值
    capital_columns = ['涨停板>100亿', '50亿<涨停板<100亿', '20亿<涨停板<50亿', '涨停板<20亿']
    for col in capital_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            # 如果列不存在，初始化为0
            df[col] = 0
    
    return df

def filter_data_by_days(df, time_range_str):
    """根据时间范围字符串过滤数据 - 修复版本"""
    if df is None or len(df) == 0:
        return df
    
    # 确保数据按日期升序排列
    df = df.sort_values('日期', ascending=True).reset_index(drop=True)
    
    if time_range_str == "全部数据":
        return df
    
    days_map = {
        "最近5天": 5,
        "最近10天": 10, 
        "最近20天": 20,
        "最近30天": 30
    }
    
    days = days_map.get(time_range_str, 10)
    
    if len(df) <= days:
        return df
    
    # 取最新的日期（最后一行）并向前计算天数
    latest_date = df['日期'].iloc[-1]
    start_date = latest_date - timedelta(days=days-1)
    filtered_df = df[df['日期'] >= start_date].copy()
    
    return filtered_df.sort_values('日期', ascending=True).reset_index(drop=True)

def safe_get_value(df, column, default=0):
    """安全获取数据值 - 修复版本"""
    if column not in df.columns:
        return default
    
    # 确保数据是按日期升序排列的（最新的在最后）
    if len(df) == 0:
        return default
    
    # 获取最新值（最后一行，因为数据是按日期升序排列的）
    latest_value = df[column].iloc[-1]
    
    # 处理空值
    if pd.isna(latest_value):
        return default
    
    return latest_value

def create_trading_alerts(df):
    """智能预警系统 - 修复时间轴版本"""
    alerts = []
    
    if len(df) < 5:
        return alerts
    
    # 确保使用正确的最新数据（数据是按日期升序排列的，最新数据在最后一行）
    latest_data = df.iloc[-1]
    
    # 成交量异常
    volume_avg = df['全天总额'].tail(20).mean()
    current_volume = latest_data['全天总额']
    if current_volume > volume_avg * 1.5:
        alerts.append({
            "type": "warning",
            "message": f"📈 成交量异常放大: 较20日均值增加{(current_volume/volume_avg-1)*100:.1f}%",
            "value": f"{current_volume:,.0f} vs 均值{volume_avg:,.0f}"
        })
    elif current_volume < volume_avg * 0.7:
        alerts.append({
            "type": "info", 
            "message": f"📉 成交量萎缩: 较20日均值减少{(1-current_volume/volume_avg)*100:.1f}%",
            "value": f"{current_volume:,.0f} vs 均值{volume_avg:,.0f}"
        })
    
    # 涨停家数异常
    if '全天涨停' in df.columns:
        limit_up_avg = df['全天涨停'].tail(10).mean()
        current_limit_up = latest_data['全天涨停']
        if current_limit_up > limit_up_avg * 2 and limit_up_avg > 0:
            alerts.append({
                "type": "warning",
                "message": f"🔥 涨停家数异常活跃: 达到{current_limit_up}家",
                "value": f"较10日均值增加{(current_limit_up/limit_up_avg-1)*100:.1f}%"
            })
    
    # 北向资金异常
    if '北向净值' in df.columns:
        north_avg = df['北向净值'].tail(10).mean()
        current_north = latest_data['北向净值']
        if abs(current_north) > abs(north_avg) * 3 and north_avg != 0:
            direction = "流入" if current_north > 0 else "流出"
            alerts.append({
                "type": "warning" if abs(current_north) > 100 else "info",
                "message": f"🌊 北向资金大幅{direction}: {current_north:+.0f}亿",
                "value": f"较10日均值放大{abs(current_north/north_avg):.1f}倍"
            })
    
    # 封板率异常
    if '全天封板率' in df.columns:
        board_rate = latest_data['全天封板率'] * 100
        if board_rate < 50:
            alerts.append({
                "type": "warning",
                "message": f"📊 封板率偏低: {board_rate:.1f}%",
                "value": "市场打板情绪较差"
            })
        elif board_rate > 80:
            alerts.append({
                "type": "success",
                "message": f"📊 封板率优秀: {board_rate:.1f}%", 
                "value": "市场打板情绪高涨"
            })
    
    return alerts
# modules/data_processing.py (添加数据质量监控)
def add_data_quality_monitor(df):
    """数据质量监控面板"""
    st.markdown("###  数据质量")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # 数据完整率
        completeness = (1 - df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100
        st.metric("数据完整率", f"{completeness:.1f}%", 
                 delta="优秀" if completeness > 95 else "良好" if completeness > 85 else "需关注")
    
    with col2:
        # 关键指标完整率
        key_columns = ['全天总额', '北向净值', '全天涨停', '上涨', '下跌']
        available_keys = [col for col in key_columns if col in df.columns]
        if available_keys:
            key_completeness = (1 - df[available_keys].isnull().sum().sum() / (len(df) * len(available_keys))) * 100
            st.metric("关键指标完整率", f"{key_completeness:.1f}%",
                     delta="优秀" if key_completeness > 98 else "良好" if key_completeness > 90 else "需关注")
        else:
            st.metric("关键指标", "未找到")
    
    with col3:
        # 日期连续性
        if '日期' in df.columns:
            date_diff = df['日期'].diff().dt.days
            gap_days = (date_diff > 1).sum()
            continuity = (1 - gap_days / len(df)) * 100
            st.metric("日期连续性", f"{continuity:.1f}%",
                     delta=f"{gap_days}个间隔" if gap_days > 0 else "连续")
        else:
            st.metric("日期连续性", "无日期列")
    
    with col4:
        # 数据时效性
        if '日期' in df.columns:
            latest_date = df['日期'].iloc[-1]
            days_since_update = (pd.Timestamp.now() - latest_date).days
            st.metric("最新数据", latest_date.strftime('%m-%d'),
                     delta=f"{days_since_update}天前")
        else:
            st.metric("数据时效", "未知")

def calculate_risk_level(df):
    """计算综合风险等级"""
    if len(df) < 5:
        return "数据不足"
    
    risk_score = 0
    latest = df.iloc[-1]
    
    # 成交额风险（缩量）
    if '全天总额' in df.columns:
        volume_ma5 = df['全天总额'].tail(5).mean()
        current_volume = latest['全天总额']
        if current_volume < volume_ma5 * 0.7:
            risk_score += 2
        elif current_volume < volume_ma5 * 0.8:
            risk_score += 1
    
    # 北向资金风险（大幅流出）
    if '北向净值' in df.columns:
        if latest['北向净值'] < -50:
            risk_score += 2
        elif latest['北向净值'] < -20:
            risk_score += 1
    
    # 市场情绪风险（跌停增多）
    if '全天跌停' in df.columns and '全天涨停' in df.columns:
        if latest['全天跌停'] > 30:
            risk_score += 2
        elif latest['全天跌停'] > 20:
            risk_score += 1
        # 涨停跌停比
        if latest['全天涨停'] > 0:
            limit_ratio = latest['全天跌停'] / latest['全天涨停']
            if limit_ratio > 1:
                risk_score += 1
    
    # 封板率风险
    if '全天封板率' in df.columns:
        if latest['全天封板率'] < 0.5:
            risk_score += 1
    
    # 确定风险等级
    if risk_score >= 4:
        return "高风险"
    elif risk_score >= 2:
        return "中风险"
    else:
        return "低风险"

# modules/data_processing.py (修复波动率计算)
def calculate_volatility(df, window=20):
    """计算波动率指标 - 修复版本"""
    if '全天总额' in df.columns and len(df) >= window:
        # 使用成交额的变化率来计算波动率
        df_sorted = df.sort_values('日期', ascending=True).copy()
        returns = df_sorted['全天总额'].pct_change().dropna()
        
        if len(returns) >= window:
            # 计算滚动波动率（使用最新数据）
            recent_returns = returns.tail(window)
            volatility = recent_returns.std() * np.sqrt(252)  # 年化波动率
            return float(volatility)
    
    # 如果数据不足，使用简单方法估算
    if '全天总额' in df.columns and len(df) > 1:
        df_sorted = df.sort_values('日期', ascending=True).copy()
        returns = df_sorted['全天总额'].pct_change().dropna()
        if len(returns) > 0:
            volatility = returns.std() * np.sqrt(252) * (len(returns) / 252)  # 调整后的年化波动率
            return float(volatility)
    
    return None

def calculate_max_drawdown(df):
    """计算最大回撤 - 修复版本"""
    if '全天总额' in df.columns and len(df) > 1:
        df_sorted = df.sort_values('日期', ascending=True).copy()
        
        # 计算累计收益率（模拟价格序列）
        # 假设初始价格为100，用成交额变化率模拟价格变化
        initial_price = 100
        returns = df_sorted['全天总额'].pct_change().fillna(0)
        cumulative_returns = (1 + returns).cumprod()
        price_series = initial_price * cumulative_returns
        
        # 计算回撤
        peak = price_series.expanding().max()
        drawdown = (price_series - peak) / peak
        max_dd = drawdown.min()
        
        return float(max_dd) if not pd.isna(max_dd) else 0.0
    
    return 0.0

def calculate_risk_level(df):
    """计算综合风险等级 - 修复版本"""
    if len(df) < 5:
        return "数据不足"
    
    risk_score = 0
    latest = df.iloc[-1]  # 使用最后一行（最新数据）
    
    # 1. 成交额风险（缩量）
    if '全天总额' in df.columns:
        volume_ma5 = df['全天总额'].tail(5).mean()
        current_volume = latest['全天总额']
        if current_volume < volume_ma5 * 0.7:
            risk_score += 2
            st.sidebar.warning("⚠️ 成交额显著萎缩")
        elif current_volume < volume_ma5 * 0.8:
            risk_score += 1
    
    # 2. 北向资金风险（大幅流出）
    if '北向净值' in df.columns:
        current_north = latest['北向净值']
        if current_north < -50:
            risk_score += 2
            st.sidebar.warning("⚠️ 北向资金大幅流出")
        elif current_north < -20:
            risk_score += 1
    
    # 3. 市场情绪风险（跌停增多）
    if '全天跌停' in df.columns and '全天涨停' in df.columns:
        current_limit_down = latest['全天跌停']
        current_limit_up = latest['全天涨停']
        
        if current_limit_down > 30:
            risk_score += 2
            st.sidebar.warning("⚠️ 跌停家数过多")
        elif current_limit_down > 20:
            risk_score += 1
        
        # 涨停跌停比
        if current_limit_up > 0:
            limit_ratio = current_limit_down / current_limit_up
            if limit_ratio > 1:
                risk_score += 1
                st.sidebar.info("ℹ️ 跌停多于涨停")
    
    # 4. 封板率风险
    if '全天封板率' in df.columns:
        current_board_rate = latest['全天封板率']
        if current_board_rate < 0.5:
            risk_score += 1
            st.sidebar.info("ℹ️ 封板率偏低")
    
    # 5. 波动率风险
    volatility = calculate_volatility(df)
    if volatility and volatility > 0.3:  # 30%以上年化波动率
        risk_score += 1
        st.sidebar.warning("⚠️ 市场波动率较高")
    
    # 确定风险等级
    if risk_score >= 4:
        return "高风险"
    elif risk_score >= 2:
        return "中风险"
    else:
        return "低风险"

def get_cleaning_logs():
    """获取数据清洗日志"""
    return cleaning_logs