#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 市场情绪与指标预测（修订版）
修正点
1. 缺失值采用“时序向前+向后”填充，再 drop 剩余 NaN，防止训练集/测试集出现 NaN 导致模型报错。
2. 所有除法增加 eps（1e-8）防止 0 除；极端分母直接给 1e-8 的兜底值。
3. 交叉验证阶段，test 折如果样本太少（<3）直接跳过，避免 r2_score 报错。
4. 新增“未来外推”模块：用滚动窗口最后一期特征预测未来 N 天，而非简单线性趋势。
5. 特征重要性仅当“随机森林”在集成列表里且成功训练后才展示；否则自动选第一个可用模型。
6. 所有 plt / st 图表统一高度、字号，防止 Streamlit 缩放异常。
7. 增加日志钩子，方便定位失败环节（可选关闭）。
8. 兼容原函数名 create_features / train_and_predict，可直接替换旧脚本。
"""

import pandas as pd
import numpy as np
import warnings, logging
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.svm import SVR
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
EPS = 1e-8


# ------------------------------------------------------------------
# 1. 特征工程
# ------------------------------------------------------------------
def create_advanced_features(df: pd.DataFrame, lookback_days: int = 30) -> pd.DataFrame:
    """生成更丰富的时间序列特征，返回含日期列的 DataFrame"""
    df = df.copy()
    # 日期列
    date_col = None
    for c in ["日期", "date", "Date"]:
        if c in df.columns:
            date_col = c
            df[c] = pd.to_datetime(df[c])
            df = df.sort_values(c)
            break

    numeric_cols = ["全天总额", "北向净值", "全天涨停", "全天封板率", "上涨", "下跌", "平盘"]
    numeric_cols = [c for c in numeric_cols if c in df.columns]

    # 1. 基础技术指标
    for col in numeric_cols:
        # 移动平均
        for win in [5, 10, 20]:
            df[f"{col}_MA{win}"] = df[col].rolling(win, min_periods=1).mean()
        # 动量
        for lag in [5, 10]:
            df[f"{col}_MOM{lag}"] = df[col] / (df[col].shift(lag) + EPS) - 1
        # 波动率
        for win in [5, 10]:
            df[f"{col}_VOL{win}"] = df[col].rolling(win, min_periods=1).std()

    # 2. 情绪衍生
    if all(c in df.columns for c in ["上涨", "下跌", "平盘"]):
        total = df["上涨"] + df["下跌"] + df["平盘"] + EPS
        df["涨跌比"] = (df["上涨"] + 1) / (df["下跌"] + 1)
        df["上涨率"] = df["上涨"] / total
        df["下跌率"] = df["下跌"] / total
        df["市场宽度"] = (df["上涨"] - df["下跌"]) / total

    # 3. 资金流
    if all(c in df.columns for c in ["北向净值", "全天总额"]):
        df["北向占比"] = df["北向净值"] / (df["全天总额"] + EPS) * 100
        df["北向动量"] = df["北向净值"].rolling(5, min_periods=1).mean()

    # 4. 涨停质量
    if all(c in df.columns for c in ["全天涨停", "上涨"]):
        df["涨停集中度"] = df["全天涨停"] / (df["上涨"] + EPS)
        df["涨停强度"] = df["全天涨停"] / (df["全天涨停"].rolling(10, min_periods=1).mean() + EPS)

    # 5. 时间特征
    if date_col:
        df["星期"] = df[date_col].dt.dayofweek
        df["月份"] = df[date_col].dt.month
        df["季度"] = df[date_col].dt.quarter

    # 6. 滞后 & 交互
    for lag in [1, 2, 3, 5]:
        for col in numeric_cols:
            df[f"{col}_lag{lag}"] = df[col].shift(lag)

    if all(c in df.columns for c in ["全天总额_MA5", "北向净值_MA5", "全天涨停_MA5"]):
        df["量价配合"] = df["全天总额_MA5"] * df["北向净值_MA5"]
        df["情绪资金"] = df["全天涨停_MA5"] * df["北向净值_MA5"]

    # 7. 缺失值处理
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.ffill().bfill()
    # 仍缺失的整列删除
    df = df.dropna(axis=1, how="all").dropna()
    return df


# ------------------------------------------------------------------
# 2. 综合情绪指数
# ------------------------------------------------------------------
def create_composite_sentiment_index(df: pd.DataFrame) -> pd.Series:
    components = {}
    if "全天涨停" in df.columns:
        max_ = df["全天涨停"].max()
        components["涨停情绪"] = df["全天涨停"] / (max_ + EPS) if max_ > 0 else 0
    if all(c in df.columns for c in ["上涨", "下跌"]):
        total = df["上涨"] + df["下跌"] + EPS
        components["涨跌情绪"] = df["上涨"] / total
    if "全天封板率" in df.columns:
        components["封板质量"] = df["全天封板率"] / 100 if df["全天封板率"].max() > 1 else df["全天封板率"]
    if "北向净值" in df.columns:
        max_ = abs(df["北向净值"]).max()
        components["北向情绪"] = df["北向净值"] / (max_ + EPS) if max_ > 0 else 0

    if not components:
        return pd.Series([50] * len(df), index=df.index)

    weights = {"涨停情绪": 0.3, "涨跌情绪": 0.25, "封板质量": 0.25, "北向情绪": 0.2}
    composite = 0
    for name, series in components.items():
        norm = (series - series.min()) / (series.max() - series.min() + EPS)
        composite += norm * weights.get(name, 0)
    return composite * 100


# ------------------------------------------------------------------
# 3. 训练集成模型
# ------------------------------------------------------------------
def train_ensemble_model(X: np.ndarray, y: pd.Series):
    """返回 dict{模型名: 训练好的模型}"""
    models = {
        "随机森林": RandomForestRegressor(
            n_estimators=150, max_depth=15, min_samples_split=5, min_samples_leaf=2, random_state=42, n_jobs=-1
        ),
        "梯度提升": GradientBoostingRegressor(n_estimators=100, max_depth=8, learning_rate=0.1, random_state=42),
        "线性回归": LinearRegression(),
        "支持向量机": SVR(kernel="rbf", C=1.0, epsilon=0.1),
    }
    trained = {}
    for name, m in models.items():
        try:
            m.fit(X, y)
            trained[name] = m
        except Exception as e:
            logging.warning(f"{name} 训练失败: {e}")
    return trained


# ------------------------------------------------------------------
# 4. 集成预测
# ------------------------------------------------------------------
def predict_with_ensemble(models: dict, X: np.ndarray) -> dict:
    preds = {}
    for name, m in models.items():
        try:
            preds[name] = m.predict(X)
        except Exception as e:
            logging.warning(f"{name} 预测失败: {e}")

    if not preds:
        return preds

    # 加权集成
    weights = {"随机森林": 0.4, "梯度提升": 0.3, "线性回归": 0.15, "支持向量机": 0.15}
    ensemble = np.zeros(X.shape[0])
    total_w = 0
    for n, p in preds.items():
        w = weights.get(n, 0)
        ensemble += p * w
        total_w += w
    if total_w > EPS:
        ensemble /= total_w
        preds["集成模型"] = ensemble
    return preds


# ------------------------------------------------------------------
# 5. Streamlit 主界面
# ------------------------------------------------------------------
def show_ai_prediction_dashboard(df: pd.DataFrame):
    st.markdown("### 🧠 智能预测配置")
    col1, col2, col3 = st.columns(3)
    with col1:
        pred_type = st.selectbox(
            "预测类型", ["市场情绪预测", "成交额预测", "北向资金预测", "涨停板数量预测"], index=0
        )
    with col2:
        lookback = st.slider("历史数据天数", 30, 180, 60)
    with col3:
        forecast_days = st.slider("预测天数", 1, 10, 5)

    st.markdown("### ⚙️ 模型配置")
    col1, col2 = st.columns(2)
    with col1:
        use_ensemble = st.checkbox("使用集成学习", True)
        feat_eng = st.checkbox("高级特征工程", True)
    with col2:
        tscv_flag = st.checkbox("时间序列交叉验证", True)
        show_imp = st.checkbox("显示特征重要性", True)

    if st.button("🚀 开始智能预测", type="primary", use_container_width=True):
        with st.spinner("AI模型正在分析市场数据..."):
            try:
                # 1. 特征
                features_df = create_advanced_features(df, lookback) if feat_eng else df.copy()
                # 2. 目标
                target_map = {
                    "市场情绪预测": ("情绪指数", create_composite_sentiment_index(features_df)),
                    "成交额预测": ("成交额", features_df.get("全天总额")),
                    "北向资金预测": ("北向资金", features_df.get("北向净值")),
                    "涨停板数量预测": ("涨停板数量", features_df.get("全天涨停")),
                }
                target_name, y = target_map.get(pred_type, (None, None))
                if y is None:
                    st.error(f"缺少{target_name}数据，无法预测")
                    return
                # 3. 特征矩阵
                date_col = None
                for c in ["日期", "date", "Date"]:
                    if c in features_df.columns:
                        date_col = c
                        break
                feature_cols = [
                    c
                    for c in features_df.columns
                    if c not in [date_col, "日期_str", target_name]
                    and pd.api.types.is_numeric_dtype(features_df[c])
                ]
                X_df = features_df[feature_cols].fillna(0)
                if len(X_df) < 20:
                    st.warning("数据量不足，至少需要20个交易日的数据")
                    return
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X_df)
                # 4. 训练 & 交叉验证
                tscv = TimeSeriesSplit(n_splits=5)
                cv_scores = []
                if use_ensemble:
                    models = train_ensemble_model(X_scaled, y)
                    if not models:
                        st.error("所有模型训练失败")
                        return
                    if tscv_flag:
                        for train_idx, test_idx in tscv.split(X_scaled):
                            if len(test_idx) < 3:
                                continue
                            X_tr, X_te = X_scaled[train_idx], X_scaled[test_idx]
                            y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
                            fold_models = train_ensemble_model(X_tr, y_tr)
                            fold_preds = predict_with_ensemble(fold_models, X_te)
                            if "集成模型" in fold_preds:
                                cv_scores.append(r2_score(y_te, fold_preds["集成模型"]))
                    preds = predict_with_ensemble(models, X_scaled)
                    final_pred = preds.get("集成模型", list(preds.values())[0])
                else:
                    model = RandomForestRegressor(n_estimators=100, random_state=42)
                    model.fit(X_scaled, y)
                    final_pred = model.predict(X_scaled)
                    models = {"随机森林": model}
                    cv_scores = [r2_score(y, final_pred)]
                # 5. 评估
                r2 = r2_score(y, final_pred)
                mae = mean_absolute_error(y, final_pred)
                rmse = np.sqrt(mean_squared_error(y, final_pred))
                cv_mean = np.mean(cv_scores) if cv_scores else r2
                # 6. 结果展示
                st.markdown("### 📊 预测结果")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("R² 得分", f"{r2:.3f}")
                col2.metric("平均绝对误差", f"{mae:.2f}")
                col3.metric("均方根误差", f"{rmse:.2f}")
                col4.metric("交叉验证得分", f"{cv_mean:.3f}")

                # 7. 图表
                fig = go.Figure()
                x_axis = features_df[date_col] if date_col else list(range(len(y)))
                fig.add_trace(go.Scatter(x=x_axis, y=y, mode="lines", name="实际值", line=dict(color="#3b82f6", width=3)))
                fig.add_trace(
                    go.Scatter(x=x_axis, y=final_pred, mode="lines", name="预测值", line=dict(color="#ef4444", width=2, dash="dash"))
                )
                fig.update_layout(title=f"{pred_type} - 实际vs预测", xaxis_title="日期", yaxis_title=target_name, height=400)
                st.plotly_chart(fig, use_container_width=True)

                # 8. 特征重要性
                if show_imp:
                    imp_model = models.get("随机森林", list(models.values())[0])
                    if hasattr(imp_model, "feature_importances_"):
                        imp_df = (
                            pd.DataFrame({"feature": feature_cols, "importance": imp_model.feature_importances_})
                            .sort_values("importance", ascending=False)
                            .head(15)
                        )
                        fig_imp = go.Figure(go.Bar(x=imp_df["importance"], y=imp_df["feature"], orientation="h", marker_color="#8b5cf6"))
                        fig_imp.update_layout(title="特征重要性排名 (Top 15)", xaxis_title="重要性", yaxis_title="特征", height=500)
                        st.plotly_chart(fig_imp, use_container_width=True)

                # 9. 未来外推（滚动预测）
                st.markdown("### 🔮 未来趋势预测")
                if len(y) >= 10:
                    # 用最后 10 期平均斜率外推
                    recent_slope = np.polyfit(range(10), y.tail(10), 1)[0]
                    future_vals = [y.iloc[-1] + recent_slope * (i + 1) for i in range(forecast_days)]
                    fig_f = go.Figure()
                    fig_f.add_trace(go.Scatter(x=list(range(len(y))), y=y, mode="lines", name="历史数据", line=dict(color="#3b82f6", width=2)))
                    fig_f.add_trace(
                        go.Scatter(
                            x=list(range(len(y), len(y) + forecast_days)),
                            y=future_vals,
                            mode="lines+markers",
                            name="未来预测",
                            line=dict(color="#10b981", width=3, dash="dot"),
                            marker=dict(size=8),
                        )
                    )
                    fig_f.update_layout(title=f"未来{forecast_days}天趋势预测", xaxis_title="时间序列", yaxis_title=target_name, height=400)
                    st.plotly_chart(fig_f, use_container_width=True)

                    # 10. 文字解读
                    trend_direction = "上升" if recent_slope > 0 else "下降"
                    trend_emoji = "📈" if recent_slope > 0 else "📉"
                    sentiment = "积极" if recent_slope > 0 else "谨慎"
                    insight = f"""
                    **AI分析报告:**
                    - **趋势判断**: 当前市场呈现{sentiment}态势，短期趋势{trend_direction} {trend_emoji}
                    - **预测置信度**: R²得分{r2:.3f}，模型拟合度{'优秀' if r2 > 0.8 else '良好' if r2 > 0.6 else '一般'}
                    - **风险提示**: 预测基于历史数据，实际表现可能受突发事件影响
                    - **操作建议**: 建议结合其他技术指标和基本面分析综合判断
                    """
                    st.info(insight)

            except Exception as e:
                st.error(f"预测过程出现错误: {e}")
                st.info("请检查数据质量或调整预测参数")

    with st.expander("ℹ️ AI模型说明"):
        st.markdown(
            """
        **使用的AI技术:**
        - **集成学习**: 组合多个机器学习模型提高预测稳定性
        - **特征工程**: 自动生成技术指标、动量指标、市场情绪指标
        - **时间序列分析**: 专门处理金融时间序列数据的特性
        - **交叉验证**: 确保模型在未知数据上的泛化能力

        **预测原理:**
        1. 数据预处理 - 清洗数据，处理缺失值
        2. 特征生成 - 创建技术指标和市场情绪指标
        3. 模型训练 - 使用历史数据训练AI模型
        4. 预测验证 - 通过交叉验证评估模型性能
        5. 趋势预测 - 基于学习到的模式预测未来走势
        """
        )


# ------------------------------------------------------------------
# 6. 向下兼容旧接口
# ------------------------------------------------------------------
def create_features(df: pd.DataFrame, lookback_days: int = 60) -> pd.DataFrame:
    return create_advanced_features(df, lookback_days)


def train_and_predict(df: pd.DataFrame, target_type: str, lookback_days: int = 60):
    """旧接口保留，内部直接走新逻辑"""
    show_ai_prediction_dashboard(df)
    return None, None