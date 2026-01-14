#!/usr/bin/env python3
"""
北交所股票分析 - 命令行工具
支持快速查询指定时间范围的数据
"""

import argparse
import json
from stock_analysis_cached import (
    StockDataCache,
    get_bz50_market_levels_cached,
    calculate_individual_stocks_levels_cached,
    calculate_similarity_with_market,
    sort_stocks_by_similarity,
    load_config
)


def main():
    parser = argparse.ArgumentParser(description='北交所股票分析工具')
    parser.add_argument('--start', type=str, help='开始日期 (YYYYMMDD)', default=None)
    parser.add_argument('--end', type=str, help='结束日期 (YYYYMMDD)', default=None)
    parser.add_argument('--stocks', type=int, help='最大股票数量', default=None)
    parser.add_argument('--no-cache', action='store_true', help='禁用缓存')
    parser.add_argument('--top', type=int, help='显示前N名', default=10)
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    # 使用命令行参数覆盖配置
    if args.start:
        config['start_date'] = args.start
    if args.end:
        config['end_date'] = args.end
    if args.stocks:
        config['max_stocks'] = args.stocks
    if args.no_cache:
        config['cache_enabled'] = False
    
    print("=== 北交所股票分析系统 ===\n")
    print(f"分析时间范围: {config['start_date']} ~ {config['end_date']}")
    print(f"股票数量: {config['max_stocks']}")
    print(f"缓存状态: {'启用' if config['cache_enabled'] else '禁用'}")
    print()
    
    # 初始化缓存
    cache = StockDataCache(config['data_dir'])
    
    # 获取大盘数据
    print("正在获取北证50指数数据...")
    market_levels = get_bz50_market_levels_cached(
        config['start_date'],
        config['end_date'],
        cache,
        config['cache_enabled']
    )
    print(f"✓ 获取到 {len(market_levels)} 天的北证50数据\n")
    
    # 获取个股数据
    print("正在获取个股数据...")
    stocks_levels = calculate_individual_stocks_levels_cached(
        config['start_date'],
        config['end_date'],
        cache,
        config['cache_enabled'],
        config['max_stocks']
    )
    print(f"✓ 获取到 {len(stocks_levels)} 只股票的数据\n")
    
    # 计算相似度
    print("正在计算相似度...")
    similarity_results = calculate_similarity_with_market(stocks_levels, market_levels)
    sorted_results = sort_stocks_by_similarity(similarity_results)
    print(f"✓ 完成相似度计算\n")
    
    # 显示结果
    print(f"=== 前 {args.top} 名匹配率排名 ===")
    print(f"{'排名':<6} {'股票代码':<12} {'匹配天数':<10} {'总天数':<10} {'匹配率':<10}")
    print("-" * 54)
    
    for i, (stock_code, info) in enumerate(sorted_results[:args.top]):
        print(f"{i+1:<6} {stock_code:<12} {info['match_days']:<10} {info['total_days']:<10} {info['match_ratio']:<10.4f}")
    
    print()


if __name__ == "__main__":
    main()
