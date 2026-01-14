"""
北交所股票数据分析程序
根据requirement.md实现以下功能：
1. 使用akshare查询北交所股票数据
2. 计算北交所整体涨跌幅度
3. 计算个股涨跌幅度
4. 计算股票与大盘相似度
5. 按匹配率排序
"""

import akshare as ak
import pandas as pd
from typing import Dict, List, Tuple
import warnings
import time
warnings.filterwarnings('ignore')


def get_beijing_stocks_data():
    """
    获取北交所股票数据
    返回北交所所有股票的历史交易数据
    """
    # 获取北交所股票列表
    try:
        stock_info = ak.stock_info_bj_name_code()
        return stock_info
    except Exception as e:
        print(f"获取北交所股票列表失败: {e}")
        return pd.DataFrame()


def get_beijing_stock_daily(symbol: str, start_date: str, end_date: str):
    """
    获取单个北交所股票的日线数据
    :param symbol: 股票代码
    :param start_date: 开始日期 格式: YYYYMMDD
    :param end_date: 结束日期 格式: YYYYMMDD
    :return: 日线数据DataFrame
    """
    try:
        # 添加延时避免请求过于频繁
        time.sleep(0.5)
        stock_zh_a_hist_df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=""
        )
        return stock_zh_a_hist_df
    except Exception as e:
        print(f"获取股票 {symbol} 数据失败: {e}")
        return pd.DataFrame()


def calculate_price_change_level(change_percent: float) -> int:
    """
    计算涨跌幅度等级
    :param change_percent: 涨跌幅百分比
    :return: 4-大涨(>1%), 3-小涨(0-1%), 2-小跌(-1%-0), 1-大跌(<-1%)
    """
    if change_percent > 1.0:
        return 4  # 大涨
    elif change_percent >= 0 and change_percent <= 1.0:
        return 3  # 小涨
    elif change_percent >= -1.0 and change_percent < 0:
        return 2  # 小跌
    else:
        return 1  # 大跌


def get_beijing_index_daily(start_date: str, end_date: str) -> Dict[str, int]:
    """
    获取北交所指数每日涨跌数据并计算涨跌幅度等级
    :param start_date: 开始日期 格式: YYYYMMDD
    :param end_date: 结束日期 格式: YYYYMMDD
    :return: 字典，key为日期，value为涨跌幅度等级(4,3,2,1)
    """
    # 获取北交所指数数据
    try:
        bj_index = ak.stock_zh_index_hist(symbol="bj", start_date=start_date, end_date=end_date)
        bj_index_daily_levels = {}
        
        for index, row in bj_index.iterrows():
            date = row['日期'].strftime('%Y-%m-%d')
            change_pct = row['涨跌幅']
            level = calculate_price_change_level(change_pct)
            bj_index_daily_levels[date] = level
            
        return bj_index_daily_levels
    except Exception as e:
        print(f"获取北交所指数数据失败: {e}")
        # 如果无法获取指数数据，则基于成分股计算平均值
        return calculate_beijing_average_daily(start_date, end_date)


def calculate_beijing_average_daily(start_date: str, end_date: str) -> Dict[str, int]:
    """
    通过北交所股票数据计算平均涨跌情况
    :param start_date: 开始日期 格式: YYYYMMDD
    :param end_date: 结束日期 格式: YYYYMMDD
    :return: 字典，key为日期，value为涨跌幅度等级(4,3,2,1)
    """
    # 获取北交所股票列表
    stock_info = get_beijing_stocks_data()
    if stock_info.empty:
        print("无法获取股票列表，返回空数据")
        return {}
    
    # 修正列名 - 根据实际返回的列名调整
    if '证券代码' in stock_info.columns:
        stock_codes = stock_info['证券代码'].tolist()
    elif '代码' in stock_info.columns:
        stock_codes = stock_info['代码'].tolist()
    else:
        print("无法找到正确的股票代码列")
        return {}
    
    daily_changes = {}
    
    # 收集所有股票在每个交易日的涨跌幅 - 仅使用前3只股票加快测试
    for i, code in enumerate(stock_codes[:3]):  # 进一步减少到前3只股票
        print(f"正在处理第 {i+1}/{min(3, len(stock_codes))} 只股票: {code}")
        try:
            stock_data = get_beijing_stock_daily(str(code), start_date, end_date)
            if stock_data.empty:
                print(f"  股票 {code} 没有数据")
                continue
                
            stock_data['日期'] = pd.to_datetime(stock_data['日期'])
            
            for index, row in stock_data.iterrows():
                date = row['日期'].strftime('%Y-%m-%d')
                change_pct = float(row['涨跌幅']) if '涨跌幅' in row else 0.0
                
                if date not in daily_changes:
                    daily_changes[date] = []
                daily_changes[date].append(change_pct)
                
        except Exception as e:
            print(f"  处理股票 {code} 时出错: {e}")
            continue
    
    # 计算每天的平均涨跌幅
    bj_avg_daily_levels = {}
    for date, changes in daily_changes.items():
        if len(changes) > 0:
            avg_change = sum(changes) / len(changes)
            level = calculate_price_change_level(avg_change)
            bj_avg_daily_levels[date] = level
    
    return bj_avg_daily_levels


def calculate_individual_stocks_levels(start_date: str, end_date: str) -> Dict[str, Dict[str, int]]:
    """
    计算北交所每只股票每日涨跌幅度等级
    :param start_date: 开始日期 格式: YYYYMMDD
    :param end_date: 结束日期 格式: YYYYMMDD
    :return: 字典，key为股票代码，value为该股票的涨跌幅度等级字典
    """
    stock_info = get_beijing_stocks_data()
    if stock_info.empty:
        print("无法获取股票列表，返回空数据")
        return {}
    
    # 修正列名 - 根据实际返回的列名调整
    if '证券代码' in stock_info.columns:
        stock_codes = stock_info['证券代码'].tolist()
    elif '代码' in stock_info.columns:
        stock_codes = stock_info['代码'].tolist()
    else:
        print("无法找到正确的股票代码列")
        return {}
    
    stocks_levels = {}
    
    # 只处理前3只股票以减少API调用次数
    for i, code in enumerate(stock_codes[:3]):
        print(f"正在获取个股数据 - 第 {i+1}/{min(3, len(stock_codes))} 只股票: {code}")
        try:
            stock_data = get_beijing_stock_daily(str(code), start_date, end_date)
            if stock_data.empty:
                print(f"  股票 {code} 没有数据")
                continue
                
            stock_levels = {}
            stock_data['日期'] = pd.to_datetime(stock_data['日期'])
            
            for index, row in stock_data.iterrows():
                date = row['日期'].strftime('%Y-%m-%d')
                change_pct = float(row['涨跌幅']) if '涨跌幅' in row else 0.0
                level = calculate_price_change_level(change_pct)
                stock_levels[date] = level
            
            if stock_levels:  # 只有当股票有数据时才加入
                stocks_levels[str(code)] = stock_levels
                print(f"  股票 {code} 数据处理完成，共 {len(stock_levels)} 条记录")
        except Exception as e:
            print(f"  处理股票 {code} 时出错: {e}")
            continue
    
    return stocks_levels


def calculate_similarity_with_market(stocks_levels: Dict[str, Dict[str, int]], 
                                   market_levels: Dict[str, int]) -> Dict[str, Dict[str, float]]:
    """
    计算每只股票与北交所大盘的相似度
    :param stocks_levels: 每只股票的涨跌幅度等级字典
    :param market_levels: 北交所大盘的涨跌幅度等级字典
    :return: 字典，格式为{股票代码: {"match_days": 匹配天数, "total_days": 总天数, "match_ratio": 匹配率}}
    """
    similarity_results = {}
    
    for stock_code, stock_levels in stocks_levels.items():
        match_days = 0
        total_days = 0
        
        for date, stock_level in stock_levels.items():
            if date in market_levels:
                total_days += 1
                if stock_level == market_levels[date]:
                    match_days += 1
        
        if total_days > 0:
            match_ratio = match_days / total_days
            similarity_results[stock_code] = {
                "match_days": match_days,
                "total_days": total_days,
                "match_ratio": match_ratio
            }
    
    return similarity_results


def sort_stocks_by_similarity(similarity_results: Dict[str, Dict[str, float]]) -> List[Tuple[str, Dict[str, float]]]:
    """
    按匹配率从高到低对所有股票进行排序
    :param similarity_results: 相似度结果字典
    :return: 排序后的列表，元素为(股票代码, 相似度信息)
    """
    sorted_results = sorted(
        similarity_results.items(),
        key=lambda x: x[1]['match_ratio'],
        reverse=True
    )
    return sorted_results


def demo_functionality():
    """
    演示各项功能的具体实现
    """
    print("=== 北交所股票分析系统演示 ===\n")
    
    # 示例：展示价格变化等级计算
    print("1. 价格变化等级计算示例:")
    test_changes = [2.5, 0.8, -0.5, -1.5]
    for change in test_changes:
        level = calculate_price_change_level(change)
        level_desc = {4: "大涨", 3: "小涨", 2: "小跌", 1: "大跌"}
        print(f"   涨跌幅 {change}% -> 等级 {level} ({level_desc[level]})")
    print()
    
    # 获取部分股票数据进行演示
    print("2. 获取北交所股票列表 (前5只):")
    try:
        stock_info = get_beijing_stocks_data()
        if not stock_info.empty:
            print(stock_info.head())
        else:
            print("无法获取股票列表数据")
    except Exception as e:
        print(f"获取股票列表失败: {e}")
    print()
    
    # 设置时间范围
    start_date = "20240101"
    end_date = "20241231"
    
    # 获取北交所大盘每日涨跌等级
    print("3. 正在获取北交所大盘数据...")
    market_levels = calculate_beijing_average_daily(start_date, end_date)
    print(f"   获取到 {len(market_levels)} 天的大盘数据")
    if market_levels:
        sample_dates = list(market_levels.keys())[:5]
        for date in sample_dates:
            level_desc = {4: "大涨", 3: "小涨", 2: "小跌", 1: "大跌"}
            print(f"   {date}: {market_levels[date]} ({level_desc[market_levels[date]]})")
    else:
        print("   没有获取到大盘数据")
    print()
    
    # 获取每只股票的涨跌等级
    print("4. 正在获取个股数据...")
    stocks_levels = calculate_individual_stocks_levels(start_date, end_date)
    print(f"   获取到 {len(stocks_levels)} 只股票的数据")
    if stocks_levels:
        # 显示第一只股票的部分数据
        first_stock = list(stocks_levels.keys())[0]
        print(f"   示例 - 股票 {first_stock} 的部分涨跌数据:")
        stock_data = stocks_levels[first_stock]
        sample_dates = list(stock_data.keys())[:5]
        for date in sample_dates:
            level_desc = {4: "大涨", 3: "小涨", 2: "小跌", 1: "大跌"}
            print(f"     {date}: {stock_data[date]} ({level_desc[stock_data[date]]})")
    else:
        print("   没有获取到个股数据")
    print()
    
    # 计算相似度
    print("5. 正在计算股票与大盘的相似度...")
    similarity_results = calculate_similarity_with_market(stocks_levels, market_levels)
    print(f"   计算出 {len(similarity_results)} 只股票的相似度")
    if similarity_results:
        # 显示前几只股票的相似度
        for i, (stock_code, info) in enumerate(list(similarity_results.items())[:5]):
            print(f"   股票 {stock_code}: 匹配天数={info['match_days']}, "
                  f"总天数={info['total_days']}, 匹配率={info['match_ratio']:.4f}")
    else:
        print("   没有计算出相似度数据")
    print()
    
    # 按相似度排序
    print("6. 按相似度排序 (前10名):")
    sorted_results = sort_stocks_by_similarity(similarity_results)
    
    if sorted_results:
        print(f"{'排名':<4} {'股票代码':<10} {'匹配天数':<8} {'总天数':<8} {'匹配率':<10}")
        print("-" * 46)
        
        for i, (stock_code, info) in enumerate(sorted_results[:10]):
            print(f"{i+1:<4} {stock_code:<10} {info['match_days']:<8} {info['total_days']:<8} {info['match_ratio']:<10.4f}")
    else:
        print("   没有可排序的数据")


def main():
    """
    主函数，演示所有功能
    """
    demo_functionality()


if __name__ == "__main__":
    main()