#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量下载北交所所有股票的增持/减持公告PDF
时间范围: 20240830 ~ 20260130
"""

from stock_analysis_cached import (
    get_stocks_data,
    download_stock_announcements_with_pdfs,
    Exchange
)
import time
import random
from datetime import datetime


def download_all_bse_holdings_announcements():
    """
    下载北交所所有股票的增持/减持公告PDF
    """
    # 配置参数
    exchange = Exchange.BSE
    start_date = "20240830"
    end_date = "20260130"
    keywords = ['增持', '减持']  # 关键词过滤
    
    print("="*70)
    print("北交所股票增持/减持公告PDF批量下载")
    print("="*70)
    print(f"交易所: 北交所 (BSE)")
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"关键词: {keywords}")
    print(f"PDF限制: 无限制 (max_pdfs=None)")
    print("="*70)
    
    # 获取北交所股票列表
    print("\n步骤1: 获取北交所股票列表...")
    stock_info = get_stocks_data(exchange)
    
    if stock_info.empty:
        print("错误: 无法获取北交所股票列表")
        return
    
    stock_codes = stock_info['证券代码'].tolist()
    total_stocks = len(stock_codes)
    
    print(f"成功获取 {total_stocks} 只北交所股票")
    print(f"股票代码: {', '.join(stock_codes[:10])}{'...' if total_stocks > 10 else ''}")
    
    # 统计变量
    total_announcements = 0
    total_pdfs = 0
    success_stocks = 0
    failed_stocks = 0
    start_time = datetime.now()
    
    print(f"\n步骤2: 开始批量下载...")
    print("="*70)
    
    # 遍历每只股票
    for i, code in enumerate(stock_codes, 1):
        stock_name = stock_info[stock_info['证券代码'] == code]['证券简称'].iloc[0] if len(stock_info[stock_info['证券代码'] == code]) > 0 else code
        
        print(f"\n[{i}/{total_stocks}] 处理 {code} {stock_name}")
        print("-"*70)
        
        try:
            # 下载该股票的增持/减持公告
            announcements_df, downloaded_files = download_stock_announcements_with_pdfs(
                stock_code=code,
                exchange=exchange,
                start_date=start_date,
                end_date=end_date,
                download_pdfs=True,
                max_pdfs=None,  # 不限制数量
                title_keywords=keywords,  # 只下载包含"增持"或"减持"的公告
                save_dir=f"data/pdfs/bse_holdings/{code}"  # 按股票代码分目录
            )
            
            # 统计
            announcement_count = len(announcements_df)
            pdf_count = len(downloaded_files)
            
            total_announcements += announcement_count
            total_pdfs += pdf_count
            
            if pdf_count > 0:
                success_stocks += 1
                print(f"✓ 成功: 原始公告{announcement_count}条, 下载PDF{pdf_count}个")
            else:
                print(f"○ 无匹配: 原始公告{announcement_count}条, 无增持/减持公告")
            
        except Exception as e:
            failed_stocks += 1
            print(f"✗ 失败: {e}")
        
        # 反爬虫策略：每10只股票休息一下
        # if i % 10 == 0 and i < total_stocks:
        #     pause_time = random.uniform(3, 6)
        #     print(f"\n[反爬虫] 已处理 {i} 只股票，休息 {pause_time:.1f} 秒...")
        #     time.sleep(pause_time)
        
        # 显示进度
        if i % 20 == 0 or i == total_stocks:
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time = elapsed / i
            remaining = (total_stocks - i) * avg_time
            print(f"\n[进度] {i}/{total_stocks} ({i/total_stocks*100:.1f}%)")
            print(f"  已用时间: {elapsed/60:.1f}分钟")
            print(f"  预计剩余: {remaining/60:.1f}分钟")
            print(f"  当前统计: 成功{success_stocks}只, 失败{failed_stocks}只, 下载PDF{total_pdfs}个")
    
    # 最终统计
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    print("\n" + "="*70)
    print("下载完成！")
    print("="*70)
    print(f"总股票数: {total_stocks}")
    print(f"成功下载: {success_stocks} 只")
    print(f"无匹配公告: {total_stocks - success_stocks - failed_stocks} 只")
    print(f"失败: {failed_stocks} 只")
    print(f"总公告数: {total_announcements} 条")
    print(f"下载PDF: {total_pdfs} 个")
    print(f"总用时: {total_time/60:.1f} 分钟")
    print(f"平均速度: {total_time/total_stocks:.1f} 秒/股")
    print(f"\nPDF保存位置: data/pdfs/bse_holdings/")
    print("="*70)
    
    # 生成下载报告
    generate_download_report(
        total_stocks=total_stocks,
        success_stocks=success_stocks,
        failed_stocks=failed_stocks,
        total_announcements=total_announcements,
        total_pdfs=total_pdfs,
        total_time=total_time
    )


def generate_download_report(total_stocks, success_stocks, failed_stocks, 
                            total_announcements, total_pdfs, total_time):
    """生成下载报告"""
    report_file = "data/pdfs/bse_holdings/download_report.txt"
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("北交所股票增持/减持公告PDF下载报告\n")
            f.write("="*70 + "\n")
            f.write(f"下载时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"时间范围: 20240830 ~ 20260130\n")
            f.write(f"关键词: 增持, 减持\n")
            f.write("\n")
            f.write("下载统计:\n")
            f.write(f"  总股票数: {total_stocks}\n")
            f.write(f"  成功下载: {success_stocks} ({success_stocks/total_stocks*100:.1f}%)\n")
            f.write(f"  无匹配公告: {total_stocks - success_stocks - failed_stocks}\n")
            f.write(f"  失败: {failed_stocks}\n")
            f.write(f"  总公告数: {total_announcements}\n")
            f.write(f"  下载PDF: {total_pdfs}\n")
            f.write(f"  总用时: {total_time/60:.1f} 分钟\n")
            f.write(f"  平均速度: {total_time/total_stocks:.1f} 秒/股\n")
            f.write("\n")
            f.write("PDF保存位置: data/pdfs/bse_holdings/\n")
            f.write("="*70 + "\n")
        
        print(f"\n下载报告已保存: {report_file}")
    except Exception as e:
        print(f"\n警告: 无法保存下载报告: {e}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("准备开始批量下载北交所增持/减持公告PDF")
    print("="*70)
    print("\n注意事项:")
    print("1. 本脚本将下载所有北交所股票的公告（可能需要较长时间）")
    print("2. 只下载标题包含'增持'或'减持'关键词的公告PDF")
    print("3. 已实现反爬虫机制，请耐心等待")
    print("4. 可随时按 Ctrl+C 中断下载")
    print("\n是否继续? (按Enter继续，Ctrl+C取消)")
    
    try:
        input()
        download_all_bse_holdings_announcements()
    except KeyboardInterrupt:
        print("\n\n用户中断下载")
    except Exception as e:
        print(f"\n\n发生错误: {e}")
        import traceback
        traceback.print_exc()
