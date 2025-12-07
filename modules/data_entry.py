# modules/data_entry.py
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

def show_data_entry_form():
    """显示完整的数据录入表单"""
    st.markdown("### 📝 完整数据录入")
    
    # 使用 tabs 组织不同的数据组 - 增加到6个Tab
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "💰 基础成交数据", 
        "📊 市场细分数据", 
        "🎯 涨跌停分析", 
        "📈 资金流向", 
        "🏢 市值分布",
        "🔥 热点数据"  
    ])
    
    with tab1:
        st.markdown("#### 基础成交数据")
        col1, col2 = st.columns(2)
        
        with col1:
            trade_date = st.date_input("交易日期*", datetime.now())
            open_amount = st.number_input("开盘金额(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            morning_total = st.number_input("上午总额(亿元)*", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            afternoon_total = st.number_input("下午总额(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            full_day_total = st.number_input("全天总额(亿元)*", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            yesterday_diff = st.number_input("今昨差额(亿元)", value=0.0, step=0.1, format="%.2f")
            
        with col2:
            sh_open = st.number_input("沪指开盘", value=0.0, step=0.1, format="%.2f")
            sz_open = st.number_input("深综开盘", value=0.0, step=0.1, format="%.2f")
            cy_open = st.number_input("创开盘金额", value=0.0, step=0.1, format="%.2f")
            advance = st.number_input("上涨家数*", min_value=0, value=0, step=1)
            flat = st.number_input("平盘/停牌家数", min_value=0, value=0, step=1)
            decline = st.number_input("下跌家数*", min_value=0, value=0, step=1)
    
    with tab2:
        st.markdown("#### 各市场成交细分")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**沪市成交**")
            sh_morning = st.number_input("沪额上午(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            sh_afternoon = st.number_input("沪额下午(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            sh_full = st.number_input("沪额全天(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            
            st.markdown("**深市成交**")
            sz_morning = st.number_input("深综上午(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            sz_afternoon = st.number_input("深综下午(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            sz_full = st.number_input("深综全天(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            
        with col2:
            st.markdown("**创业板成交**")
            cy_morning = st.number_input("创额上午(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            cy_afternoon = st.number_input("创额下午(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            cy_full = st.number_input("创额全天(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            
            st.markdown("**两融数据**")
            margin_balance = st.number_input("两融资余额(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            margin_net_buy = st.number_input("融资净买入(亿元)", value=0.0, step=0.1, format="%.2f")
    
    with tab3:
        st.markdown("#### 涨跌停分析")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**上午数据**")
            morning_limit_up = st.number_input("上午涨停", min_value=0, value=0, step=1)
            morning_limit_chain = st.number_input("上午涨停连接板", min_value=0, value=0, step=1)
            morning_height_board = st.number_input("上午高度板", min_value=0, value=0, step=1)
            
            st.markdown("**全天数据**")
            full_limit_up = st.number_input("全天涨停*", min_value=0, value=0, step=1)
            full_limit_chain = st.number_input("全天涨停连接板", min_value=0, value=0, step=1)
            full_height_board = st.number_input("全天高度板", min_value=0, value=0, step=1)
            
        with col2:
            st.markdown("**涨停细分**")
            main_board_limit = st.number_input("主板涨停数", min_value=0, value=0, step=1)
            gem_board_limit = st.number_input("创业板涨停数", min_value=0, value=0, step=1)
            beijing_board_limit = st.number_input("北证涨停数", min_value=0, value=0, step=1)
            rise_over_10 = st.number_input("涨幅大于10%", min_value=0, value=0, step=1)
            board_rate = st.number_input("全天封板率*", min_value=0.0, max_value=1.0, value=0.0, step=0.01, format="%.3f")
            
            st.markdown("**跌停数据**")
            main_board_limit_down = st.number_input("主板跌停数", min_value=0, value=0, step=1)
            gem_board_limit_down = st.number_input("创业板跌停数", min_value=0, value=0, step=1)
            beijing_board_limit_down = st.number_input("北证跌停数", min_value=0, value=0, step=1)
            fall_over_10 = st.number_input("跌幅大于10%", min_value=0, value=0, step=1)
            full_limit_down = st.number_input("全天总跌停*", min_value=0, value=0, step=1)
    
    with tab4:
        st.markdown("#### 资金流向")
        col1, col2 = st.columns(2)
        
        with col1:
            north_turnover = st.number_input("北向成交额(亿元)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            north_net = st.number_input("北向净值(亿元)*", value=0.0, step=0.1, format="%.2f")
            
        with col2:
            # 可以添加其他资金流向数据
            st.info("💡 北向资金数据已包含")
    
    with tab5:
        st.markdown("#### 涨停板市值分布")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**上午市值分布**")
            morning_over_100b = st.number_input(">100亿(上午)", min_value=0, value=0, step=1)
            morning_50_100b = st.number_input("50-100亿(上午)", min_value=0, value=0, step=1)
            morning_20_50b = st.number_input("20-50亿(上午)", min_value=0, value=0, step=1)
            morning_under_20b = st.number_input("<20亿(上午)", min_value=0, value=0, step=1)
            
        with col2:
            st.markdown("**全天市值分布**")
            full_over_100b = st.number_input(">100亿(全天)", min_value=0, value=0, step=1)
            full_50_100b = st.number_input("50-100亿(全天)", min_value=0, value=0, step=1)
            full_20_50b = st.number_input("20-50亿(全天)", min_value=0, value=0, step=1)
            full_under_20b = st.number_input("<20亿(全天)", min_value=0, value=0, step=1)
    
    # ==========================
    # 新增：热点数据录入Tab
    # ==========================
    with tab6:
        st.markdown("#### 🔥 市场热点数据")
        st.info("💡 录入当日市场热点信息，用于热点扫描分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**行业数据**")
            industry_rise = st.text_area(
                "行业涨幅榜",
                placeholder="半导体\\元器件\\通信设备\\IT设备\\软件服务...",
                help="用反斜杠(\\\\)分隔各行业，按涨幅从高到低排列"
            )
            
            industry_limit = st.text_area(
                "行业涨停榜", 
                placeholder="元器件10+6\\汽车类8+2\\工业机械5+6...",
                help="格式：行业名称+涨停数量，用反斜杠(\\\\)分隔"
            )
        
        with col2:
            st.markdown("**概念数据**")
            concept_rise = st.text_area(
                "概念涨幅榜",
                placeholder="AI手机PC\\无线耳机\\苹果概念\\新型烟草...",
                help="用反斜杠(\\\\)分隔各概念，按涨幅从高到低排列"
            )
            
            concept_limit = st.text_area(
                "概念涨停榜",
                placeholder="新能源车24+9\\机器人概念18+10\\人工智能15+16...",
                help="格式：概念名称+涨停数量，用反斜杠(\\\\)分隔"
            )
        
        # 热点数据使用说明
        with st.expander("📋 热点数据录入说明"):
            st.markdown("""
            **录入格式说明：**
            - **分隔符**: 使用反斜杠 `\\` 分隔不同项目
            - **行业涨幅榜**: 按当日涨幅从高到低排列，例如：`半导体\\元器件\\通信设备`
            - **概念涨幅榜**: 按当日涨幅从高到低排列，例如：`AI手机PC\\无线耳机\\苹果概念`
            - **行业涨停榜**: 格式为 `行业名称+涨停数量`，例如：`元器件10+6\\汽车类8+2`
            - **概念涨停榜**: 格式为 `概念名称+涨停数量`，例如：`新能源车24+9\\机器人概念18+10`
            
            **数据来源建议：**
            - 同花顺、东方财富等行情软件
            - 各大财经网站的市场热点板块
            - 券商研报中的热点分析
            """)
    
    # 提交按钮 - 放在所有tab下面
    st.markdown("---")
    submitted = st.button("💾 保存完整数据", type="primary", use_container_width=True)
    
    if submitted:
        # 数据验证
        if not trade_date:
            st.error("请选择交易日期")
            return None
        if morning_total == 0 and full_day_total == 0:
            st.error("请至少填写上午总额或全天总额")
            return None
            
        # 构建完整数据字典
        data = {
            '日期': trade_date.strftime('%Y-%m-%d'),
            # 基础成交数据
            '开盘金额': open_amount,
            '上午总额': morning_total,
            '下午总额': afternoon_total,
            '全天总额': full_day_total,
            '今昨差额': yesterday_diff,
            '沪指开盘': sh_open,
            '深综开盘': sz_open,
            '创开盘金额': cy_open,
            '上涨': advance,
            '平盘/停牌': flat,
            '下跌': decline,
            
            # 市场细分数据
            '沪额上午': sh_morning,
            '沪额下午': sh_afternoon,
            '沪额全天': sh_full,
            '深综上午': sz_morning,
            '深综下午': sz_afternoon,
            '深综全天': sz_full,
            '创额上午': cy_morning,
            '创额下午': cy_afternoon,
            '创额全天': cy_full,
            '两融资余额': margin_balance,
            '融资净买入': margin_net_buy,
            
            # 涨跌停分析
            '上午涨停': morning_limit_up,
            '上午涨停连接板': morning_limit_chain,
            '上午高度板': morning_height_board,
            '全天涨停': full_limit_up,
            '全天涨停连接板': full_limit_chain,
            '全天高度板': full_height_board,
            '主板涨停数': main_board_limit,
            '创业板涨停数': gem_board_limit,
            '北证涨停数': beijing_board_limit,
            '涨幅大于10%': rise_over_10,
            '全天封板率': board_rate,
            '主板跌停数': main_board_limit_down,
            '创业板跌停数': gem_board_limit_down,
            '北证跌停数': beijing_board_limit_down,
            '跌幅于大于10%': fall_over_10,
            '全天总跌停': full_limit_down,
            
            # 资金流向
            '北向成交额': north_turnover,
            '北向净值': north_net,
            
            # 市值分布
            '涨停板>100亿(上午）': morning_over_100b,
            '50亿<涨停板<100亿(上午）': morning_50_100b,
            '20亿<涨停板<50亿(上午）': morning_20_50b,
            '涨停板<20亿(上午）': morning_under_20b,
            '涨停板>100亿(全天）': full_over_100b,
            '50亿<涨停板<100亿(全天）': full_50_100b,
            '20亿<涨停板<50亿(全天）': full_20_50b,
            '涨停板<20亿(全天）': full_under_20b,
            
            # 新增热点数据
            '行业涨幅榜': industry_rise if industry_rise else "",
            '概念涨幅榜': concept_rise if concept_rise else "",
            '行业涨停榜': industry_limit if industry_limit else "",
            '概念涨停榜': concept_limit if concept_limit else ""
        }
        
        # 显示数据预览
        st.success("✅ 数据验证通过！")
        st.markdown("#### 📋 数据预览")
        
        # 创建预览数据框
        preview_data = []
        for key, value in data.items():
            if value:  # 只显示有值的字段
                preview_data.append({"字段": key, "数值": str(value)[:100] + "..." if len(str(value)) > 100 else str(value)})
        
        if preview_data:
            st.dataframe(pd.DataFrame(preview_data), use_container_width=True)
        
        return data
    
    return None

def save_new_data(current_df, new_data, uploaded_file):
    """保存新数据到Excel文件"""
    try:
        # 创建新数据行
        new_row = pd.DataFrame([new_data])
        
        # 合并数据（确保日期列类型一致）
        if '日期' in current_df.columns:
            current_df['日期'] = pd.to_datetime(current_df['日期'])
        new_row['日期'] = pd.to_datetime(new_row['日期'])
        
        # 检查是否已存在相同日期的数据
        existing_dates = current_df['日期'].dt.strftime('%Y-%m-%d').tolist() if '日期' in current_df.columns else []
        new_date = new_row['日期'].iloc[0].strftime('%Y-%m-%d')
        
        if new_date in existing_dates:
            st.warning(f"⚠️ 日期 {new_date} 的数据已存在，将覆盖原有数据")
            # 移除原有数据
            current_df = current_df[current_df['日期'].dt.strftime('%Y-%m-%d') != new_date]
        
        # 合并数据
        updated_df = pd.concat([current_df, new_row], ignore_index=True)
        updated_df = updated_df.sort_values('日期', ascending=False)
        
        # 保存到Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            updated_df.to_excel(writer, index=False, sheet_name='市场数据')
        
        output.seek(0)
        
        # 提供下载
        st.download_button(
            label="📥 下载更新后的Excel文件",
            data=output.getvalue(),
            file_name=f"A股完整数据_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        # 显示成功信息
        st.success("✅ 数据保存成功！")
        
        # 显示热点数据预览（如果有）
        if any(new_data.get(col) for col in ['行业涨幅榜', '概念涨幅榜', '行业涨停榜', '概念涨停榜']):
            st.info("🔥 热点数据已成功录入，可在'热点扫描'Tab中查看")
        
        return True
        
    except Exception as e:
        st.error(f"保存数据时出错: {str(e)}")
        return False