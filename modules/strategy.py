import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

class StrategyBacktester:
    """策略回测器类"""
    
    def __init__(self, df, initial_capital=100000):
        self.df = df.copy()
        self.initial_capital = initial_capital
        self.results = {}
    
    def calculate_technical_indicators(self):
        """计算技术指标"""
        df = self.df
        
        # 价格相关指标（使用成交额代理）
        if '全天总额' in df.columns:
            # 移动平均
            df['MA5'] = df['全天总额'].rolling(window=5).mean()
            df['MA10'] = df['全天总额'].rolling(window=10).mean()
            df['MA20'] = df['全天总额'].rolling(window=20).mean()
            
            # 布林带
            df['BB_Middle'] = df['全天总额'].rolling(window=20).mean()
            df['BB_Upper'] = df['BB_Middle'] + 2 * df['全天总额'].rolling(window=20).std()
            df['BB_Lower'] = df['BB_Middle'] - 2 * df['全天总额'].rolling(window=20).std()
            df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
            
            # RSI (相对强弱指标)
            delta = df['全天总额'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-8)
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['全天总额'].ewm(span=12).mean()
            exp2 = df['全天总额'].ewm(span=26).mean()
            df['MACD'] = exp1 - exp2
            df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
            df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # 市场情绪指标
        if all(col in df.columns for col in ['上涨', '下跌', '平盘']):
            df['涨跌比'] = (df['上涨'] + 1) / (df['下跌'] + 1)
            df['上涨率'] = df['上涨'] / (df['上涨'] + df['下跌'] + df['平盘'])
        
        # 资金流指标
        if '北向净值' in df.columns:
            df['北向_MA5'] = df['北向净值'].rolling(window=5).mean()
            df['北向_MA10'] = df['北向净值'].rolling(window=10).mean()
        
        # 涨停板指标
        if '全天涨停' in df.columns:
            df['涨停_MA5'] = df['全天涨停'].rolling(window=5).mean()
            df['涨停动量'] = df['全天涨停'] / df['涨停_MA5'] - 1
        
        self.df = df
        return df

    def momentum_strategy(self, window=5, threshold=0.1):
        """动量策略"""
        df = self.calculate_technical_indicators()
        
        # 基于成交额动量
        df['volume_momentum'] = df['全天总额'] / df['全天总额'].rolling(window=window).mean() - 1
        
        # 生成信号
        df['signal'] = 0
        df.loc[df['volume_momentum'] > threshold, 'signal'] = 1  # 买入
        df.loc[df['volume_momentum'] < -threshold, 'signal'] = -1  # 卖出
        
        return df

    def mean_reversion_strategy(self, window=20, z_threshold=2):
        """均值回归策略"""
        df = self.calculate_technical_indicators()
        
        if '全天总额' in df.columns:
            # 计算Z-score
            df['mean'] = df['全天总额'].rolling(window=window).mean()
            df['std'] = df['全天总额'].rolling(window=window).std()
            df['z_score'] = (df['全天总额'] - df['mean']) / (df['std'] + 1e-8)
            
            # 生成信号
            df['signal'] = 0
            df.loc[df['z_score'] < -z_threshold, 'signal'] = 1  # 超卖，买入
            df.loc[df['z_score'] > z_threshold, 'signal'] = -1  # 超买，卖出
        
        return df

    def breakout_strategy(self, window=20, multiplier=1.05):
        """突破策略"""
        df = self.calculate_technical_indicators()
        
        if '全天总额' in df.columns:
            # 计算阻力位和支撑位
            df['resistance'] = df['全天总额'].rolling(window=window).max()
            df['support'] = df['全天总额'].rolling(window=window).min()
            
            # 突破信号
            df['signal'] = 0
            df.loc[df['全天总额'] > df['resistance'].shift(1) * multiplier, 'signal'] = 1  # 向上突破
            df.loc[df['全天总额'] < df['support'].shift(1) / multiplier, 'signal'] = -1  # 向下突破
        
        return df

    def sentiment_strategy(self, extreme_threshold=0.7):
        """市场情绪策略"""
        df = self.calculate_technical_indicators()
        
        if all(col in df.columns for col in ['上涨', '下跌', '全天涨停']):
            # 计算情绪指标
            total_stocks = df['上涨'] + df['下跌'] + df.get('平盘', 0)
            df['advance_ratio'] = df['上涨'] / total_stocks
            df['limit_up_ratio'] = df['全天涨停'] / total_stocks
            
            # 情绪极端化信号
            df['signal'] = 0
            # 情绪冰点买入
            df.loc[(df['advance_ratio'] < (1 - extreme_threshold)) & 
                  (df['limit_up_ratio'] < 0.01), 'signal'] = 1
            # 情绪狂热卖出
            df.loc[(df['advance_ratio'] > extreme_threshold) & 
                  (df['limit_up_ratio'] > 0.03), 'signal'] = -1
        
        return df

    def north_money_strategy(self, window=3, threshold=20):
        """北向资金策略"""
        df = self.calculate_technical_indicators()
        
        if '北向净值' in df.columns:
            # 北向资金连续流入流出
            df['north_trend'] = df['北向净值'].rolling(window=window).sum()
            
            df['signal'] = 0
            # 连续大幅流入买入
            df.loc[df['north_trend'] > threshold, 'signal'] = 1
            # 连续大幅流出卖出
            df.loc[df['north_trend'] < -threshold, 'signal'] = -1
        
        return df

    def backtest(self, strategy_df, transaction_cost=0.001, stop_loss=0.1, take_profit=0.2):
        """专业回测引擎"""
        if 'signal' not in strategy_df.columns:
            return None
        
        capital = self.initial_capital
        position = 0
        trades = []
        equity_curve = []
        max_capital = self.initial_capital
        drawdown = 0
        
        for i, row in strategy_df.iterrows():
            current_date = row['日期'] if '日期' in row else i
            
            # 计算当前权益
            current_equity = capital + position
            equity_curve.append({
                'date': current_date,
                'equity': current_equity,
                'capital': capital,
                'position': position
            })
            
            # 更新最大资本和回撤
            if current_equity > max_capital:
                max_capital = current_equity
            current_drawdown = (max_capital - current_equity) / max_capital
            drawdown = max(drawdown, current_drawdown)
            
            # 止损检查
            if position > 0 and current_drawdown > stop_loss:
                # 止损平仓
                capital = position * (1 - stop_loss - transaction_cost)
                trades.append({
                    'date': current_date, 
                    'action': 'STOP_LOSS', 
                    'capital': capital,
                    'price': 'N/A',
                    'shares': 0
                })
                position = 0
                continue
            
            # 策略信号处理
            signal = row['signal']
            
            if signal == 1 and position == 0:  # 买入
                # 全仓买入
                position = capital * (1 - transaction_cost)
                capital = 0
                trades.append({
                    'date': current_date,
                    'action': 'BUY',
                    'capital': current_equity,
                    'price': 'N/A',
                    'shares': position
                })
                
            elif signal == -1 and position > 0:  # 卖出
                # 计算收益（简化：基于市场情绪）
                if '上涨率' in row and not pd.isna(row['上涨率']):
                    # 根据市场上涨率估算收益
                    pct_change = row['上涨率'] * 0.1  # 简化收益计算
                else:
                    pct_change = 0.02  # 默认2%收益
                
                # 止盈检查
                if pct_change > take_profit:
                    pct_change = take_profit
                
                capital = position * (1 + pct_change - transaction_cost)
                position = 0
                trades.append({
                    'date': current_date,
                    'action': 'SELL',
                    'capital': capital,
                    'price': 'N/A',
                    'pct_change': pct_change
                })
        
        # 最终平仓
        if position > 0:
            capital += position
            position = 0
        
        # 计算绩效指标
        final_equity = capital
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # 年化收益率（假设252个交易日）
        if len(strategy_df) > 1:
            days = len(strategy_df)
            annual_return = (1 + total_return) ** (252 / days) - 1
        else:
            annual_return = total_return
        
        # 夏普比率（简化）
        if len(equity_curve) > 1:
            returns = pd.Series([curve['equity'] for curve in equity_curve]).pct_change().dropna()
            sharpe_ratio = returns.mean() / (returns.std() + 1e-8) * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # 胜率
        if len(trades) >= 2:
            profitable_trades = len([t for t in trades if t.get('pct_change', 0) > 0])
            win_rate = profitable_trades / len([t for t in trades if 'pct_change' in t])
        else:
            win_rate = 0
        
        self.results = {
            'final_capital': final_equity,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'total_trades': len(trades),
            'trades': trades,
            'equity_curve': equity_curve,
            'strategy_df': strategy_df
        }
        
        return self.results

def create_comprehensive_strategy_chart(results):
    """创建综合策略图表"""
    if not results or 'strategy_df' not in results:
        return None
    
    df = results['strategy_df']
    equity_curve = results['equity_curve']
    
    # 创建子图
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('策略信号与成交额', '资金曲线', '回撤分析'),
        vertical_spacing=0.08,
        row_heights=[0.4, 0.3, 0.3]
    )
    
    # 第一子图：策略信号
    if '全天总额' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['日期'], 
                y=df['全天总额'],
                mode='lines',
                name='成交额',
                line=dict(color='#1f77b4', width=2)
            ),
            row=1, col=1
        )
    
    # 买入信号
    buy_signals = df[df['signal'] == 1]
    if len(buy_signals) > 0:
        fig.add_trace(
            go.Scatter(
                x=buy_signals['日期'],
                y=buy_signals.get('全天总额', [1] * len(buy_signals)) * 1.02,
                mode='markers',
                name='买入信号',
                marker=dict(color='green', size=10, symbol='triangle-up')
            ),
            row=1, col=1
        )
    
    # 卖出信号
    sell_signals = df[df['signal'] == -1]
    if len(sell_signals) > 0:
        fig.add_trace(
            go.Scatter(
                x=sell_signals['日期'],
                y=sell_signals.get('全天总额', [1] * len(sell_signals)) * 0.98,
                mode='markers',
                name='卖出信号',
                marker=dict(color='red', size=10, symbol='triangle-down')
            ),
            row=1, col=1
        )
    
    # 第二子图：资金曲线
    if equity_curve:
        dates = [point['date'] for point in equity_curve]
        equity = [point['equity'] for point in equity_curve]
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=equity,
                mode='lines',
                name='资金曲线',
                line=dict(color='#00ff00', width=3)
            ),
            row=2, col=1
        )
        
        # 初始资金线
        initial_capital = equity_curve[0]['equity'] if equity_curve else 0
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=[initial_capital] * len(dates),
                mode='lines',
                name='初始资金',
                line=dict(color='white', width=1, dash='dash')
            ),
            row=2, col=1
        )
    
    # 第三子图：回撤分析
    if equity_curve:
        equity_series = pd.Series([point['equity'] for point in equity_curve])
        rolling_max = equity_series.expanding().max()
        drawdown = (rolling_max - equity_series) / rolling_max
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=drawdown,
                mode='lines',
                name='回撤',
                line=dict(color='#ff6b6b', width=2),
                fill='tozeroy'
            ),
            row=3, col=1
        )
    
    fig.update_layout(
        height=800,
        showlegend=True,
        title_text="策略回测综合分析"
    )
    
    fig.update_xaxes(title_text="日期", row=3, col=1)
    fig.update_yaxes(title_text="成交额", row=1, col=1)
    fig.update_yaxes(title_text="资金", row=2, col=1)
    fig.update_yaxes(title_text="回撤率", row=3, col=1)
    
    return fig

def show_backtest_dashboard(df):
    """显示增强版策略回测仪表板"""
    
    st.markdown('<div class="section-header">🎯 智能策略回测中心</div>', unsafe_allow_html=True)
    
    # 策略选择
    st.markdown("### 📊 策略配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        strategy_type = st.selectbox(
            "选择策略类型",
            [
                "动量策略", 
                "均值回归策略", 
                "突破策略", 
                "市场情绪策略",
                "北向资金策略",
                "多策略组合"
            ],
            index=0
        )
    
    with col2:
        initial_capital = st.number_input(
            "初始资金（元）", 
            10000, 10000000, 100000,
            help="回测起始资金"
        )
    
    # 策略参数
    st.markdown("### ⚙️ 策略参数")
    
    if strategy_type == "动量策略":
        col1, col2 = st.columns(2)
        with col1:
            window = st.slider("动量窗口（天）", 3, 60, 10)
        with col2:
            threshold = st.slider("动量阈值", 0.01, 0.3, 0.1, 0.01)
    
    elif strategy_type == "均值回归策略":
        col1, col2 = st.columns(2)
        with col1:
            window = st.slider("均值窗口（天）", 10, 100, 20)
        with col2:
            z_threshold = st.slider("Z-score阈值", 1.0, 3.0, 2.0, 0.1)
    
    elif strategy_type == "突破策略":
        col1, col2 = st.columns(2)
        with col1:
            window = st.slider("突破窗口（天）", 10, 100, 20)
        with col2:
            multiplier = st.slider("突破倍数", 1.01, 1.2, 1.05, 0.01)
    
    elif strategy_type == "市场情绪策略":
        threshold = st.slider("情绪极端阈值", 0.5, 0.9, 0.7, 0.05)
    
    elif strategy_type == "北向资金策略":
        col1, col2 = st.columns(2)
        with col1:
            window = st.slider("观察窗口（天）", 2, 10, 3)
        with col2:
            threshold = st.slider("资金阈值（亿）", 10, 100, 20)
    
    # 风险控制参数
    st.markdown("### 🛡️ 风险控制")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        transaction_cost = st.slider("交易成本 (%)", 0.0, 1.0, 0.1, 0.05) / 100
    
    with col2:
        stop_loss = st.slider("止损比例 (%)", 1.0, 20.0, 10.0, 1.0) / 100
    
    with col3:
        take_profit = st.slider("止盈比例 (%)", 5.0, 50.0, 20.0, 5.0) / 100
    
    # 回测按钮
    if st.button("🚀 开始策略回测", type="primary", use_container_width=True):
        with st.spinner("正在进行策略回测分析..."):
            try:
                # 初始化回测器
                backtester = StrategyBacktester(df, initial_capital)
                
                # 执行策略
                if strategy_type == "动量策略":
                    strategy_df = backtester.momentum_strategy(window, threshold)
                elif strategy_type == "均值回归策略":
                    strategy_df = backtester.mean_reversion_strategy(window, z_threshold)
                elif strategy_type == "突破策略":
                    strategy_df = backtester.breakout_strategy(window, multiplier)
                elif strategy_type == "市场情绪策略":
                    strategy_df = backtester.sentiment_strategy(threshold)
                elif strategy_type == "北向资金策略":
                    strategy_df = backtester.north_money_strategy(window, threshold)
                else:
                    # 多策略组合（简单平均）
                    strategy_df = backtester.momentum_strategy()
                
                # 执行回测
                results = backtester.backtest(strategy_df, transaction_cost, stop_loss, take_profit)
                
                if results:
                    # 显示关键指标
                    st.markdown("### 📈 回测绩效指标")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        return_color = "normal" if results['total_return'] > 0 else "inverse"
                        st.metric(
                            "总收益率", 
                            f"{results['total_return']:.2%}",
                            delta=f"{results['total_return']:.2%}",
                            delta_color=return_color
                        )
                    
                    with col2:
                        st.metric("年化收益率", f"{results['annual_return']:.2%}")
                    
                    with col3:
                        st.metric("最大回撤", f"{results['max_drawdown']:.2%}")
                    
                    with col4:
                        st.metric("夏普比率", f"{results['sharpe_ratio']:.2f}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("最终资金", f"¥{results['final_capital']:,.2f}")
                    
                    with col2:
                        st.metric("交易次数", results['total_trades'])
                    
                    with col3:
                        st.metric("胜率", f"{results['win_rate']:.2%}")
                    
                    with col4:
                        profit_factor = "待计算"
                        st.metric("盈利因子", profit_factor)
                    
                    # 显示综合图表
                    st.markdown("### 📊 策略分析图表")
                    fig = create_comprehensive_strategy_chart(results)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # 交易记录
                    if results['trades']:
                        st.markdown("### 📋 交易记录")
                        trades_df = pd.DataFrame(results['trades'])
                        st.dataframe(
                            trades_df.style.format({
                                'capital': '{:,.2f}',
                                'pct_change': '{:.2%}' if 'pct_change' in trades_df.columns else None
                            }),
                            use_container_width=True
                        )
                    
                    # 策略评价
                    st.markdown("### 💡 策略评价")
                    
                    evaluation = generate_strategy_evaluation(results)
                    st.info(evaluation)
                    
                else:
                    st.error("回测执行失败，请检查策略参数和数据")
                    
            except Exception as e:
                st.error(f"回测过程出现错误: {str(e)}")

def generate_strategy_evaluation(results):
    """生成策略评价"""
    if not results:
        return "无法生成策略评价"
    
    total_return = results['total_return']
    max_drawdown = results['max_drawdown']
    sharpe_ratio = results['sharpe_ratio']
    win_rate = results['win_rate']
    
    # 风险评估
    if max_drawdown < 0.05:
        risk_level = "低风险"
        risk_emoji = "🟢"
    elif max_drawdown < 0.15:
        risk_level = "中风险"
        risk_emoji = "🟡"
    else:
        risk_level = "高风险"
        risk_emoji = "🔴"
    
    # 收益评价
    if total_return > 0.2:
        return_rating = "优秀"
        return_emoji = "🎯"
    elif total_return > 0.1:
        return_rating = "良好"
        return_emoji = "📈"
    elif total_return > 0:
        return_rating = "一般"
        return_emoji = "➡️"
    else:
        return_rating = "较差"
        return_emoji = "📉"
    
    # 稳定性评价
    if sharpe_ratio > 1:
        stability = "稳定"
        stability_emoji = "🌟"
    elif sharpe_ratio > 0.5:
        stability = "较稳定"
        stability_emoji = "✅"
    else:
        stability = "不稳定"
        stability_emoji = "⚠️"
    
    evaluation = f"""
    **策略综合评估:**
    
    - **收益表现**: {return_rating} {return_emoji} - 总收益率 {total_return:.2%}
    - **风险水平**: {risk_level} {risk_emoji} - 最大回撤 {max_drawdown:.2%}
    - **策略稳定性**: {stability} {stability_emoji} - 夏普比率 {sharpe_ratio:.2f}
    - **交易质量**: 胜率 {win_rate:.2%}，共{results['total_trades']}次交易
    
    **建议:**
    {
        '可以考虑实盘测试' if total_return > 0.1 and max_drawdown < 0.1 
        else '需要优化参数' if total_return > 0 
        else '建议重新设计策略'
    }
    """
    
    return evaluation

# 保留原有函数兼容性
def calculate_momentum_strategy(df, window=5):
    """兼容原有函数"""
    backtester = StrategyBacktester(df)
    return backtester.momentum_strategy(window)

def backtest_strategy(strategy_df, initial_capital=100000):
    """兼容原有函数"""
    backtester = StrategyBacktester(strategy_df, initial_capital)
    return backtester.backtest(strategy_df)

def create_strategy_chart(strategy_df):
    """兼容原有函数"""
    results = {'strategy_df': strategy_df, 'equity_curve': []}
    return create_comprehensive_strategy_chart(results)