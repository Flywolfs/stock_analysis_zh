#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析增持/减持公告与股价涨幅关系

功能：
1. 扫描公告JSON，提取包含"增持"或"减持"的公告日期
2. 扫描完整数据JSON，提取涨幅超过5%的交易日
3. 整合两部分数据，按日期排序
4. 保存分析结果到 analysis/holdings_analysis.json
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import traceback


def parse_date(date_str: str) -> str:
    """
    将日期字符串统一转换为 YYYY-MM-DD 格式
    
    :param date_str: 日期字符串（可能是 YYYY-MM-DD HH:MM:SS 或其他格式）
    :return: YYYY-MM-DD 格式的日期字符串
    """
    try:
        # 如果包含时间部分，去掉
        if ' ' in date_str:
            date_str = date_str.split(' ')[0]
        
        # 尝试解析不同格式
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # 如果已经是正确格式，直接返回
        return date_str
    except Exception as e:
        print(f"  警告: 无法解析日期 {date_str}: {e}")
        return date_str


def extract_holdings_announcements(stock_code: str, announcements_dir: str) -> List[Tuple[str, str]]:
    """
    从公告JSON中提取包含"增持"或"减持"的公告
    
    :param stock_code: 股票代码
    :param announcements_dir: 公告目录路径
    :return: [(date, "增持"|"减持"), ...]
    """
    announcement_file = os.path.join(announcements_dir, f"{stock_code}.json")
    
    if not os.path.exists(announcement_file):
        return []
    
    try:
        with open(announcement_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        announcements = data.get('data', [])
        holdings_events = []
        
        for announcement in announcements:
            title = announcement.get('公告标题', '')
            date_str = announcement.get('公告时间', '')
            
            if not date_str:
                continue
            
            # 解析日期
            date = parse_date(date_str)
            
            # 检查标题中是否包含关键词
            if '减持' in title:
                holdings_events.append((date, '减持'))
            elif '增持' in title:
                holdings_events.append((date, '增持'))
        
        return holdings_events
    
    except Exception as e:
        print(f"  错误: 读取公告文件失败 {announcement_file}: {e}")
        return []


def extract_high_pct_chg_days(stock_code: str, full_stocks_dir: str, 
                               threshold: float = 5.0) -> List[Tuple[str, float]]:
    """
    从完整数据JSON中提取涨幅超过指定阈值的交易日
    
    :param stock_code: 股票代码
    :param full_stocks_dir: 完整数据目录路径
    :param threshold: 涨幅阈值（百分比），默认5%
    :return: [(date, pct_chg), ...]
    """
    full_stock_file = os.path.join(full_stocks_dir, f"{stock_code}_full.json")
    
    if not os.path.exists(full_stock_file):
        return []
    
    try:
        with open(full_stock_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        daily_data = data.get('data', [])
        high_pct_days = []
        
        for day_data in daily_data:
            date_str = day_data.get('date', '')
            pct_chg = day_data.get('pct_chg')
            
            if not date_str or pct_chg is None:
                continue
            
            # 解析日期
            date = parse_date(date_str)
            
            # 检查涨幅是否超过阈值
            # 注意：pct_chg 是百分比形式，如 5.5 表示 5.5%
            if pct_chg > threshold:
                high_pct_days.append((date, float(pct_chg)))
        
        return high_pct_days
    
    except Exception as e:
        print(f"  错误: 读取完整数据文件失败 {full_stock_file}: {e}")
        return []


def merge_and_sort_events(holdings_events: List[Tuple[str, str]], 
                          price_events: List[Tuple[str, float]]) -> List[Tuple[str, Any]]:
    """
    合并增持/减持事件和价格涨幅事件，并按日期排序
    
    :param holdings_events: [(date, "增持"|"减持"), ...]
    :param price_events: [(date, pct_chg), ...]
    :return: 按日期排序的事件列表 [(date, event_value), ...]
    """
    # 合并两个列表
    all_events = holdings_events + price_events
    
    # 按日期排序
    all_events.sort(key=lambda x: x[0])
    
    return all_events


def analyze_all_stocks(announcements_dir: str, full_stocks_dir: str, 
                       output_file: str, pct_threshold: float = 5.0):
    """
    分析所有股票的增持/减持公告和涨幅事件
    
    :param announcements_dir: 公告目录
    :param full_stocks_dir: 完整数据目录
    :param output_file: 输出文件路径
    :param pct_threshold: 涨幅阈值（百分比）
    """
    print("="*70)
    print("增持/减持公告与股价涨幅分析")
    print("="*70)
    print(f"公告目录: {announcements_dir}")
    print(f"数据目录: {full_stocks_dir}")
    print(f"涨幅阈值: {pct_threshold}%")
    print(f"输出文件: {output_file}")
    print("="*70)
    
    # 获取所有公告文件
    if not os.path.exists(announcements_dir):
        print(f"错误: 公告目录不存在 {announcements_dir}")
        return
    
    announcement_files = [f for f in os.listdir(announcements_dir) if f.endswith('.json')]
    stock_codes = [f.replace('.json', '') for f in announcement_files]
    
    print(f"\n找到 {len(stock_codes)} 个公告文件")
    
    # 结果字典
    analysis_results = {}
    
    # 统计信息
    total_processed = 0
    has_data = 0
    has_holdings = 0
    has_high_pct = 0
    skipped = 0
    
    # 遍历每个股票
    for i, stock_code in enumerate(stock_codes, 1):
        # 检查是否存在对应的完整数据文件
        full_stock_file = os.path.join(full_stocks_dir, f"{stock_code}_full.json")
        if not os.path.exists(full_stock_file):
            skipped += 1
            if i % 50 == 0:
                print(f"进度: {i}/{len(stock_codes)} - 跳过 {stock_code} (无完整数据)")
            continue
        
        try:
            # 提取增持/减持公告
            holdings_events = extract_holdings_announcements(stock_code, announcements_dir)
            
            # 提取涨幅超过阈值的交易日
            price_events = extract_high_pct_chg_days(stock_code, full_stocks_dir, pct_threshold)
            
            # 合并并排序
            all_events = merge_and_sort_events(holdings_events, price_events)
            
            # 如果有事件，添加到结果
            if all_events:
                analysis_results[stock_code] = all_events
                has_data += 1
                
                if holdings_events:
                    has_holdings += 1
                if price_events:
                    has_high_pct += 1
            
            total_processed += 1
            
            # 显示进度
            if i % 50 == 0 or i == len(stock_codes):
                print(f"进度: {i}/{len(stock_codes)} - 已处理 {total_processed} 只，"
                      f"有数据 {has_data} 只，跳过 {skipped} 只")
        
        except Exception as e:
            print(f"  错误: 处理股票 {stock_code} 时出错: {e}")
            traceback.print_exc()
            continue
    
    # 保存结果
    print(f"\n正在保存结果到 {output_file}...")
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 结果已保存")
    except Exception as e:
        print(f"✗ 保存失败: {e}")
        return
    
    # 最终统计
    print("\n" + "="*70)
    print("分析完成")
    print("="*70)
    print(f"总公告文件: {len(stock_codes)}")
    print(f"已处理股票: {total_processed}")
    print(f"跳过（无完整数据）: {skipped}")
    print(f"有事件的股票: {has_data}")
    print(f"  - 有增持/减持公告: {has_holdings}")
    print(f"  - 有高涨幅交易日: {has_high_pct}")
    print("="*70)
    
    # 显示示例
    if analysis_results:
        print("\n示例结果（前3只股票）:")
        for i, (stock_code, events) in enumerate(list(analysis_results.items())[:3]):
            print(f"\n股票 {stock_code}:")
            for date, value in events[:5]:  # 只显示前5个事件
                if isinstance(value, str):
                    print(f"  {date}: {value}")
                else:
                    print(f"  {date}: 涨幅 {value:.2f}%")
            if len(events) > 5:
                print(f"  ... 共 {len(events)} 个事件")


def generate_summary_report(analysis_file: str):
    """
    生成分析摘要报告
    
    :param analysis_file: 分析结果JSON文件路径
    """
    if not os.path.exists(analysis_file):
        print(f"错误: 分析文件不存在 {analysis_file}")
        return
    
    try:
        with open(analysis_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("\n" + "="*70)
        print("分析摘要")
        print("="*70)
        
        total_stocks = len(data)
        total_events = sum(len(events) for events in data.values())
        
        # 统计不同类型的事件
        total_holdings_increase = 0
        total_holdings_decrease = 0
        total_high_pct = 0
        
        for events in data.values():
            for date, value in events:
                if value == '增持':
                    total_holdings_increase += 1
                elif value == '减持':
                    total_holdings_decrease += 1
                elif isinstance(value, (int, float)):
                    total_high_pct += 1
        
        print(f"总股票数: {total_stocks}")
        print(f"总事件数: {total_events}")
        print(f"  - 增持公告: {total_holdings_increase}")
        print(f"  - 减持公告: {total_holdings_decrease}")
        print(f"  - 高涨幅交易日: {total_high_pct}")
        print("="*70)
        
        # ==================== 新增：4个月内高涨幅分析 ====================
        print("\n" + "="*70)
        print("减持/增持后4个月内高涨幅分析")
        print("="*70)
        
        # 统计每只股票的减持/增持后高涨幅情况
        stocks_with_decrease = set()  # 出现减持的股票
        stocks_with_increase = set()  # 出现增持的股票
        stocks_decrease_then_high_pct = {}  # 减持后4个月内有高涨幅的股票及天数
        stocks_increase_then_high_pct = {}  # 增持后4个月内有高涨幅的股票及天数
        
        for stock_code, events in data.items():
            # 分离减持、增持和高涨幅事件
            decrease_dates = set()  # 使用set去重
            increase_dates = set()  # 使用set去重
            high_pct_events = []  # [(date, pct_chg), ...]
            
            for date_str, value in events:
                if value == '减持':
                    decrease_dates.add(date_str)
                elif value == '增持':
                    increase_dates.add(date_str)
                elif isinstance(value, (int, float)):
                    high_pct_events.append((date_str, value))
            
            # 转换为datetime对象
            decrease_datetimes = {datetime.strptime(d, '%Y-%m-%d') for d in decrease_dates}
            increase_datetimes = {datetime.strptime(d, '%Y-%m-%d') for d in increase_dates}
            high_pct_datetimes = [(datetime.strptime(d, '%Y-%m-%d'), v) for d, v in high_pct_events]
            
            # 分析减持后4个月内的高涨幅
            if decrease_datetimes:
                stocks_with_decrease.add(stock_code)
                high_pct_count_after_decrease = 0
                checked_high_pct_dates = set()  # 已统计的高涨幅日期，避免重复
                
                for decrease_dt in decrease_datetimes:
                    # 4个月时间窗口（120天）
                    window_end = decrease_dt + timedelta(days=120)
                    
                    # 查找该窗口内的高涨幅交易日
                    for high_pct_dt, pct_value in high_pct_datetimes:
                        # 高涨幅日期在减持后且在4个月窗口内
                        if decrease_dt < high_pct_dt <= window_end:
                            # 去重：同一日期只计算一次
                            if high_pct_dt not in checked_high_pct_dates:
                                high_pct_count_after_decrease += 1
                                checked_high_pct_dates.add(high_pct_dt)
                
                if high_pct_count_after_decrease > 0:
                    stocks_decrease_then_high_pct[stock_code] = high_pct_count_after_decrease
            
            # 分析增持后4个月内的高涨幅
            if increase_datetimes:
                stocks_with_increase.add(stock_code)
                high_pct_count_after_increase = 0
                checked_high_pct_dates = set()  # 已统计的高涨幅日期，避免重复
                
                for increase_dt in increase_datetimes:
                    # 4个月时间窗口（120天）
                    window_end = increase_dt + timedelta(days=120)
                    
                    # 查找该窗口内的高涨幅交易日
                    for high_pct_dt, pct_value in high_pct_datetimes:
                        # 高涨幅日期在增持后且在4个月窗口内
                        if increase_dt < high_pct_dt <= window_end:
                            # 去重：同一日期只计算一次
                            if high_pct_dt not in checked_high_pct_dates:
                                high_pct_count_after_increase += 1
                                checked_high_pct_dates.add(high_pct_dt)
                
                if high_pct_count_after_increase > 0:
                    stocks_increase_then_high_pct[stock_code] = high_pct_count_after_increase
        
        # 计算统计比例
        total_stocks_with_decrease = len(stocks_with_decrease)
        total_stocks_with_increase = len(stocks_with_increase)
        stocks_decrease_with_high_pct_count = len(stocks_decrease_then_high_pct)
        stocks_increase_with_high_pct_count = len(stocks_increase_then_high_pct)
        
        decrease_ratio = (stocks_decrease_with_high_pct_count / total_stocks_with_decrease * 100) if total_stocks_with_decrease > 0 else 0
        increase_ratio = (stocks_increase_with_high_pct_count / total_stocks_with_increase * 100) if total_stocks_with_increase > 0 else 0
        
        print(f"\n出现减持的股票数: {total_stocks_with_decrease}")
        print(f"减持后4个月内有高涨幅的股票数: {stocks_decrease_with_high_pct_count}")
        print(f"减持后4个月内高涨幅比例: {decrease_ratio:.2f}%")
        
        print(f"\n出现增持的股票数: {total_stocks_with_increase}")
        print(f"增持后4个月内有高涨幅的股票数: {stocks_increase_with_high_pct_count}")
        print(f"增持后4个月内高涨幅比例: {increase_ratio:.2f}%")
        
        # 显示减持后高涨幅的前10只股票
        if stocks_decrease_then_high_pct:
            print("\n减持后4个月内高涨幅天数最多的前10只股票:")
            top_decrease_stocks = sorted(
                stocks_decrease_then_high_pct.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            for stock_code, high_pct_days in top_decrease_stocks:
                print(f"  {stock_code}: {high_pct_days} 天")
        
        # 显示增持后高涨幅的前10只股票
        if stocks_increase_then_high_pct:
            print("\n增持后4个月内高涨幅天数最多的前10只股票:")
            top_increase_stocks = sorted(
                stocks_increase_then_high_pct.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            for stock_code, high_pct_days in top_increase_stocks:
                print(f"  {stock_code}: {high_pct_days} 天")
        
        print("\n" + "="*70)
        # ==================== 原有统计 ====================
        
        # 找出事件最多的前10只股票
        top_stocks = sorted(data.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        
        print("\n事件最多的前10只股票:")
        for stock_code, events in top_stocks:
            holdings = sum(1 for _, v in events if isinstance(v, str))
            high_pct = len(events) - holdings
            print(f"  {stock_code}: {len(events)} 个事件 "
                  f"(增持/减持: {holdings}, 高涨幅: {high_pct})")
        
        print("\n" + "="*70)
    
    except Exception as e:
        print(f"错误: 生成摘要失败: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    # 配置路径
    announcements_dir = "data/announcements/bse"
    full_stocks_dir = "data/full_stocks/bse"
    output_file = "analysis/holdings_analysis_15%.json"
    pct_threshold = 15.0  # 涨幅阈值5%
    
    print("\n" + "="*70)
    print("增持/减持公告与股价涨幅分析工具")
    print("="*70)
    print("\n参数配置:")
    print(f"  公告目录: {announcements_dir}")
    print(f"  数据目录: {full_stocks_dir}")
    print(f"  涨幅阈值: {pct_threshold}%")
    print(f"  输出文件: {output_file}")
    print("\n开始分析...\n")
    
    try:
        # 执行分析
        analyze_all_stocks(
            announcements_dir=announcements_dir,
            full_stocks_dir=full_stocks_dir,
            output_file=output_file,
            pct_threshold=pct_threshold
        )
        
        # 生成摘要报告
        generate_summary_report(output_file)
        
        print(f"\n分析完成！结果已保存到: {output_file}")
    
    except KeyboardInterrupt:
        print("\n\n用户中断分析")
    except Exception as e:
        print(f"\n\n发生错误: {e}")
        traceback.print_exc()
