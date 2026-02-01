#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
根据已下载的增持/减持公告PDF日期，获取对应股票的完整历史数据

功能：
1. 扫描 data/pdfs/bse_holdings/ 目录下的股票子目录
2. 解析PDF文件名提取日期，计算最早日期-10天作为start_date
3. 使用 fetch_and_cache_full_stock_data 下载完整历史数据
4. 合并股票基本信息，保存为 {股票代码}_full.json
"""

import os
import re
import json
from datetime import datetime, timedelta
from stock_analysis_cached import (
    fetch_and_cache_full_stock_data,
    get_stocks_data,
    Exchange
)


def parse_date_from_filename(filename):
    """
    从PDF文件名中提取日期
    文件名格式: {股票代码}_{股票简称}_{日期}_{公告ID}.pdf
    例如: 920599_同力股份_2026-01-27_1224952593.pdf
    
    :param filename: PDF文件名
    :return: datetime对象，失败返回None
    """
    try:
        # 匹配日期格式 YYYY-MM-DD
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
        if match:
            year, month, day = match.groups()
            return datetime(int(year), int(month), int(day))
    except Exception as e:
        print(f"  警告: 无法解析文件名中的日期: {filename}, 错误: {e}")
    return None


def get_earliest_pdf_date(stock_dir):
    """
    获取某股票目录下所有PDF中最早的日期
    
    :param stock_dir: 股票PDF目录路径
    :return: datetime对象，失败返回None
    """
    earliest_date = None
    pdf_count = 0
    
    try:
        if not os.path.exists(stock_dir):
            return None
        
        for filename in os.listdir(stock_dir):
            if filename.endswith('.pdf'):
                pdf_count += 1
                date = parse_date_from_filename(filename)
                if date:
                    if earliest_date is None or date < earliest_date:
                        earliest_date = date
        
        if pdf_count > 0:
            print(f"    找到 {pdf_count} 个PDF文件, 最早日期: {earliest_date.strftime('%Y-%m-%d') if earliest_date else '无法解析'}")
    
    except Exception as e:
        print(f"  错误: 读取目录失败 {stock_dir}: {e}")
    
    return earliest_date


def fetch_stock_full_data_with_pdf_dates():
    """
    主函数：根据PDF日期获取股票完整历史数据
    """
    # 配置参数
    pdf_base_dir = "data/pdfs/bse_holdings"
    output_dir = "data/full_stocks/bse"
    end_date = "20260130"
    days_before = 10  # 最早日期前推天数
    
    print("="*70)
    print("根据增持/减持公告PDF日期获取股票完整历史数据")
    print("="*70)
    print(f"PDF目录: {pdf_base_dir}")
    print(f"输出目录: {output_dir}")
    print(f"结束日期: {end_date}")
    print(f"起始日期: 最早PDF日期 - {days_before}天")
    print("="*70)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 步骤1: 获取北交所所有股票基本信息
    print("\n步骤1: 获取北交所股票基本信息...")
    try:
        stock_info_df = get_stocks_data(Exchange.BSE)
        if stock_info_df.empty:
            print("错误: 无法获取北交所股票列表")
            return
        
        # 创建股票代码到基本信息的映射
        stock_info_map = {}
        for _, row in stock_info_df.iterrows():
            code = row['证券代码']
            stock_info_map[code] = {
                '证券代码': code,
                '证券简称': row.get('证券简称', ''),
                '总股本': row.get('总股本', 0),
                '流通股本': row.get('流通股本', 0),
                '上市日期': row.get('上市日期', ''),
                '所属行业': row.get('所属行业', ''),
                '地区': row.get('地区', ''),
            }
        
        print(f"成功获取 {len(stock_info_map)} 只股票基本信息")
    
    except Exception as e:
        print(f"错误: 获取股票基本信息失败: {e}")
        return
    
    # 步骤2: 扫描PDF目录，获取有公告的股票列表
    print("\n步骤2: 扫描PDF目录...")
    
    if not os.path.exists(pdf_base_dir):
        print(f"错误: PDF目录不存在: {pdf_base_dir}")
        return
    
    stock_dirs = []
    for item in os.listdir(pdf_base_dir):
        item_path = os.path.join(pdf_base_dir, item)
        if os.path.isdir(item_path) and item.isdigit():  # 股票代码是纯数字
            stock_dirs.append(item)
    
    stock_dirs.sort()  # 按股票代码排序
    total_stocks = len(stock_dirs)
    
    print(f"找到 {total_stocks} 个股票子目录")
    
    if total_stocks == 0:
        print("警告: 没有找到任何股票PDF目录")
        return
    
    # 步骤3: 遍历每个股票，下载并保存数据
    print("\n步骤3: 开始下载股票历史数据...")
    print("="*70)
    
    success_count = 0
    skip_count = 0
    failed_count = 0
    
    for i, stock_code in enumerate(stock_dirs, 1):
        print(f"\n[{i}/{total_stocks}] 处理股票 {stock_code}")
        print("-"*70)
        
        try:
            # 获取该股票的PDF目录
            stock_pdf_dir = os.path.join(pdf_base_dir, stock_code)
            
            # 获取最早的PDF日期
            earliest_date = get_earliest_pdf_date(stock_pdf_dir)
            
            if earliest_date is None:
                print(f"  跳过: 无法确定PDF日期")
                skip_count += 1
                continue
            
            # 计算start_date（最早日期-10天）
            start_date_dt = earliest_date - timedelta(days=days_before)
            start_date = start_date_dt.strftime('%Y%m%d')
            
            print(f"    最早PDF日期: {earliest_date.strftime('%Y-%m-%d')}")
            print(f"    计算起始日期: {start_date_dt.strftime('%Y-%m-%d')} (向前{days_before}天)")
            print(f"    结束日期: {end_date[:4]}-{end_date[4:6]}-{end_date[6:]}")
            
            # 获取股票基本信息
            if stock_code not in stock_info_map:
                print(f"  警告: 未找到股票 {stock_code} 的基本信息，尝试继续...")
                stock_info_dict = {
                    '证券代码': stock_code,
                    '证券简称': '',
                    '总股本': 0,
                    '流通股本': 0,
                    '上市日期': '',
                    '所属行业': '',
                    '地区': '',
                }
            else:
                stock_info_dict = stock_info_map[stock_code]
            
            # 下载历史数据
            print(f"    下载历史数据...")
            result = fetch_and_cache_full_stock_data(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                stock_info_dict=stock_info_dict,
                use_cache=True
            )
            
            if result is None or result.empty:
                print(f"  失败: 未获取到数据")
                failed_count += 1
                continue
            
            # 准备保存的数据
            output_file = os.path.join(output_dir, f"{stock_code}_full.json")
            
            # 转换为需要的格式
            daily_data = result.to_dict('records')
            
            full_data = {
                'stock_code': stock_code,
                'exchange': 'bse',
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data': daily_data,
                '证券代码': stock_info_dict['证券代码'],
                '证券简称': stock_info_dict['证券简称'],
                '总股本': stock_info_dict['总股本'],
                '流通股本': stock_info_dict['流通股本'],
                '上市日期': stock_info_dict['上市日期'],
                '所属行业': stock_info_dict['所属行业'],
                '地区': stock_info_dict['地区'],
                '报告日期': datetime.now().strftime('%Y-%m-%d')
            }
            
            # 保存到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(full_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"  ✓ 成功: 保存 {len(daily_data)} 条数据到 {output_file}")
            success_count += 1
        
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            failed_count += 1
            import traceback
            traceback.print_exc()
    
    # 最终统计
    print("\n" + "="*70)
    print("处理完成！")
    print("="*70)
    print(f"总股票数: {total_stocks}")
    print(f"成功: {success_count}")
    print(f"跳过: {skip_count}")
    print(f"失败: {failed_count}")
    print(f"输出目录: {output_dir}")
    print("="*70)
    
    # 生成处理报告
    generate_processing_report(
        total_stocks=total_stocks,
        success_count=success_count,
        skip_count=skip_count,
        failed_count=failed_count,
        output_dir=output_dir
    )


def generate_processing_report(total_stocks, success_count, skip_count, 
                               failed_count, output_dir):
    """生成处理报告"""
    report_file = os.path.join(output_dir, "processing_report.txt")
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("股票完整历史数据下载报告\n")
            f.write("="*70 + "\n")
            f.write(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"数据来源: data/pdfs/bse_holdings/\n")
            f.write(f"输出目录: {output_dir}\n")
            f.write("\n")
            f.write("处理统计:\n")
            f.write(f"  总股票数: {total_stocks}\n")
            f.write(f"  成功: {success_count} ({success_count/total_stocks*100:.1f}%)\n")
            f.write(f"  跳过: {skip_count}\n")
            f.write(f"  失败: {failed_count}\n")
            f.write("\n")
            f.write("="*70 + "\n")
        
        print(f"\n处理报告已保存: {report_file}")
    except Exception as e:
        print(f"\n警告: 无法保存处理报告: {e}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("准备根据PDF日期下载股票完整历史数据")
    print("="*70)
    print("\n注意事项:")
    print("1. 本脚本将扫描 data/pdfs/bse_holdings/ 目录")
    print("2. 为每个有PDF的股票下载完整历史数据")
    print("3. 起始日期 = 最早PDF日期 - 10天")
    print("4. 结束日期 = 20260130")
    print("5. 已实现缓存机制，重复运行将复用已下载数据")
    print("\n是否继续? (按Enter继续，Ctrl+C取消)")
    
    try:
        input()
        fetch_stock_full_data_with_pdf_dates()
    except KeyboardInterrupt:
        print("\n\n用户中断处理")
    except Exception as e:
        print(f"\n\n发生错误: {e}")
        import traceback
        traceback.print_exc()
