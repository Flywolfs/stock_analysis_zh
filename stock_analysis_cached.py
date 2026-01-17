"""
北交所股票数据分析程序 - 带缓存版本
支持数据本地存储和增量更新
"""

import akshare as ak
import pandas as pd
from typing import Dict, List, Tuple, Optional
import warnings
import time
import json
import os
from datetime import datetime, timedelta
import random
warnings.filterwarnings('ignore')


class StockDataCache:
    """股票数据缓存管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.stocks_dir = os.path.join(data_dir, "stocks")
        self.market_dir = os.path.join(data_dir, "market")
        self.metadata_file = os.path.join(data_dir, "metadata.json")
        
        # 创建必要的目录
        os.makedirs(self.stocks_dir, exist_ok=True)
        os.makedirs(self.market_dir, exist_ok=True)
        
        # 加载元数据
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """加载元数据"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self):
        """保存元数据"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def get_stock_cache_file(self, stock_code: str) -> str:
        """获取股票缓存文件路径"""
        return os.path.join(self.stocks_dir, f"{stock_code}.json")
    
    def get_market_cache_file(self) -> str:
        """获取市场数据缓存文件路径"""
        return os.path.join(self.market_dir, "market_data.json")
    
    def load_stock_data(self, stock_code: str) -> Optional[Dict]:
        """从缓存加载股票数据"""
        cache_file = self.get_stock_cache_file(stock_code)
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def save_stock_data(self, stock_code: str, data: Dict):
        """保存股票数据到缓存"""
        cache_file = self.get_stock_cache_file(stock_code)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 更新元数据，包括股票的实际日期范围
        if stock_code not in self.metadata:
            self.metadata[stock_code] = {}
        self.metadata[stock_code]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 记录股票实际的日期范围
        if 'daily_data' in data and data['daily_data']:
            dates = sorted(data['daily_data'].keys())
            self.metadata[stock_code]['actual_start_date'] = dates[0]
            self.metadata[stock_code]['actual_end_date'] = dates[-1]
        
        self._save_metadata()
    
    def load_market_data(self) -> Optional[Dict]:
        """从缓存加载市场数据"""
        cache_file = self.get_market_cache_file()
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def save_market_data(self, data: Dict):
        """保存市场数据到缓存"""
        cache_file = self.get_market_cache_file()
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 更新元数据
        self.metadata['market'] = {
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self._save_metadata()
    
    def get_cached_date_range(self, stock_code: str) -> Tuple[Optional[str], Optional[str]]:
        """获取缓存数据的日期范围"""
        data = self.load_stock_data(stock_code)
        if data and 'daily_data' in data and data['daily_data']:
            dates = sorted(data['daily_data'].keys())
            return dates[0], dates[-1]
        return None, None
    
    def get_stock_actual_date_range(self, stock_code: str) -> Tuple[Optional[str], Optional[str]]:
        """获取股票实际存在的日期范围（从元数据中读取）"""
        if stock_code in self.metadata:
            actual_start = self.metadata[stock_code].get('actual_start_date')
            actual_end = self.metadata[stock_code].get('actual_end_date')
            return actual_start, actual_end
        return None, None
    
    def merge_stock_data(self, stock_code: str, new_data: Dict[str, float]) -> Dict[str, float]:
        """合并新旧股票数据"""
        cached_data = self.load_stock_data(stock_code)
        if cached_data and 'daily_data' in cached_data:
            # 合并数据
            merged = cached_data['daily_data'].copy()
            merged.update(new_data)
            return merged
        return new_data


def load_config(config_file: str = "config.json") -> Dict:
    """加载配置文件"""
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "data_dir": "data",
        "start_date": "20240101",
        "end_date": "20241231",
        "cache_enabled": True,
        "max_stocks": 10
    }


def calculate_missing_date_ranges(cached_start: Optional[str], cached_end: Optional[str],
                                  required_start: str, required_end: str) -> List[Tuple[str, str]]:
    """
    计算需要下载的日期范围
    :return: [(start_date, end_date), ...] 需要下载的日期范围列表
    """
    if cached_start is None or cached_end is None:
        # 没有缓存，需要下载全部
        return [(required_start, required_end)]
    
    ranges = []
    
    # 转换为标准格式进行比较 (去掉横线)
    cached_start_num = cached_start.replace('-', '')
    cached_end_num = cached_end.replace('-', '')
    required_start_num = required_start.replace('-', '')
    required_end_num = required_end.replace('-', '')
    
    # 检查是否需要下载开始日期之前的数据
    if required_start_num < cached_start_num:
        ranges.append((required_start, cached_start.replace('-', '')))
    
    # 检查是否需要下载结束日期之后的数据
    if required_end_num > cached_end_num:
        ranges.append((cached_end.replace('-', ''), required_end))
    
    return ranges


def get_beijing_stocks_data():
    """获取北交所股票数据"""
    try:
        stock_info = ak.stock_info_bj_name_code()
        return stock_info
    except Exception as e:
        print(f"获取北交所股票列表失败: {e}")
        return pd.DataFrame()


def get_beijing_stock_daily(symbol: str, start_date: str, end_date: str, retry_count: int = 3):
    """
    获取单个北交所股票的日线数据（带重试机制）
    :param symbol: 股票代码
    :param start_date: 开始日期 格式: YYYYMMDD
    :param end_date: 结束日期 格式: YYYYMMDD
    :param retry_count: 重试次数
    :return: 日线数据DataFrame
    """
    for attempt in range(retry_count):
        try:
            # 动态sleep时间：0.5-2秒随机
            sleep_time = random.uniform(0.5, 2.0)
            time.sleep(sleep_time)
            
            stock_zh_a_hist_df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="hfq"
            )
            return stock_zh_a_hist_df
        except Exception as e:
            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 2  # 递增等待时间：2秒, 4秒, 6秒
                print(f"获取股票 {symbol} 数据失败，{wait_time}秒后重试... (第{attempt+1}/{retry_count}次)")
                time.sleep(wait_time)
            else:
                print(f"获取股票 {symbol} 数据失败: {e}")
                return pd.DataFrame()


def get_bz50_index_daily(start_date: str, end_date: str, retry_count: int = 3):
    """
    获取北证50指数日线数据（带重试机制）
    :param retry_count: 重试次数
    """
    for attempt in range(retry_count):
        try:
            # 动态sleep时间
            sleep_time = random.uniform(0.5, 2.0)
            time.sleep(sleep_time)
            
            # 北证50指数代码是899050，直接使用stock_zh_a_hist接口
            bz50_df = ak.stock_zh_a_hist(
                symbol="899050",
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="hfq"
            )
            
            if not bz50_df.empty and '日期' in bz50_df.columns:
                # 重命名列以便后续处理
                bz50_df = bz50_df.rename(columns={'日期': 'date', '涨跌幅': 'pct_chg'})
                bz50_df['date'] = pd.to_datetime(bz50_df['date'])
            
            return bz50_df
        except Exception as e:
            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 2
                print(f"获取北证50指数数据失败，{wait_time}秒后重试... (第{attempt+1}/{retry_count}次)")
                time.sleep(wait_time)
            else:
                print(f"获取北证50指数数据失败: {e}")
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


def fetch_and_cache_stock_data(stock_code: str, start_date: str, end_date: str,
                               cache: StockDataCache, use_cache: bool = True) -> Dict[str, float]:
    """
    获取并缓存股票数据（支持增量更新）
    :return: {日期: 涨跌幅百分比}
    """
    if use_cache:
        # 检查缓存中的日期范围
        cached_start, cached_end = cache.get_cached_date_range(stock_code)
        # 检查股票实际存在的日期范围（用于判断股票是否已上市）
        actual_start, actual_end = cache.get_stock_actual_date_range(stock_code)
        
        # 如果已知道股票的实际上市日期，检查请求范围是否在股票上市之前
        if actual_start:
            # 只检查开始日期，不检查结束日期（允许查询未来数据）
            actual_start_num = actual_start.replace('-', '')
            start_date_num = start_date.replace('-', '')
            
            # 如果请求的开始日期在股票上市之前，调整到上市日
            if start_date_num < actual_start_num:
                start_date = actual_start.replace('-', '')
                print(f"  股票 {stock_code} 在{start_date_num}之前未上市，调整开始日期为{actual_start}")
        
        # 计算需要下载的日期范围
        missing_ranges = calculate_missing_date_ranges(cached_start, cached_end, start_date, end_date)
        
        if not missing_ranges:
            print(f"  股票 {stock_code} 使用缓存数据")
            cached_data = cache.load_stock_data(stock_code)
            # 过滤出指定日期范围的数据
            result = {}
            for date, change in cached_data['daily_data'].items():
                if start_date <= date.replace('-', '') <= end_date:
                    result[date] = change
            return result
        else:
            print(f"  股票 {stock_code} 需要下载缺失数据段: {missing_ranges}")
    else:
        missing_ranges = [(start_date, end_date)]
    
    # 下载缺失的数据
    all_data = {}
    for range_start, range_end in missing_ranges:
        try:
            stock_df = get_beijing_stock_daily(str(stock_code), range_start, range_end)
            if not stock_df.empty:
                stock_df['日期'] = pd.to_datetime(stock_df['日期'])
                for _, row in stock_df.iterrows():
                    date = row['日期'].strftime('%Y-%m-%d')
                    change_pct = float(row['涨跌幅']) if '涨跌幅' in row else 0.0
                    all_data[date] = change_pct
            else:
                # 如果下载失败且不知道实际范围，记录为空范围
                if not cache.get_stock_actual_date_range(stock_code)[0]:
                    # 这支股票可能还未上市或已退市
                    cache.metadata[stock_code] = {
                        'actual_start_date': None,
                        'actual_end_date': None,
                        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    cache._save_metadata()
        except Exception as e:
            print(f"  下载股票 {stock_code} 数据失败: {e}")
    
    # 合并到缓存数据
    if use_cache:
        merged_data = cache.merge_stock_data(stock_code, all_data)
        cache.save_stock_data(stock_code, {'daily_data': merged_data})
        
        # 返回指定日期范围的数据
        result = {}
        for date, change in merged_data.items():
            if start_date <= date.replace('-', '') <= end_date:
                result[date] = change
        return result
    
    return all_data


def get_bz50_market_levels_cached(start_date: str, end_date: str,
                                  cache: StockDataCache, use_cache: bool = True) -> Dict[str, int]:
    """
    获取北证50指数每日涨跌等级（带缓存）
    """
    market_code = "899050"  # 北证50指数代码
    
    if use_cache:
        # 检查缓存
        market_data = cache.load_market_data()
        if market_data and 'daily_changes' in market_data:
            cached_changes = market_data['daily_changes']
            # 检查缓存是否包含需要的日期范围
            cached_dates = set(cached_changes.keys())
            
            # 过滤出需要的日期范围并转换为等级
            result = {}
            for date, change_pct in cached_changes.items():
                date_num = date.replace('-', '')
                if start_date <= date_num <= end_date:
                    level = calculate_price_change_level(change_pct)
                    result[date] = level
            
            # 如果缓存完全覆盖需求范围，直接返回
            if result:
                # 检查是否需要下载更多数据
                if cached_dates:
                    cached_start = min(cached_dates).replace('-', '')
                    cached_end = max(cached_dates).replace('-', '')
                    if start_date >= cached_start and end_date <= cached_end:
                        print(f"北证50指数使用缓存数据")
                        return result
    
    # 需要下载新数据
    print(f"正在下载北证50指数数据...")
    try:
        bz50_df = get_bz50_index_daily(start_date, end_date)
        
        bz50_changes = {}  # 存储实际涨跌幅
        bz50_levels = {}   # 存储涨跌等级
        
        if not bz50_df.empty:
            for _, row in bz50_df.iterrows():
                date = row['date'].strftime('%Y-%m-%d')
                change_pct = float(row['pct_chg']) if 'pct_chg' in row else 0.0
                bz50_changes[date] = change_pct  # 保存实际涨跌幅
                level = calculate_price_change_level(change_pct)
                bz50_levels[date] = level
        
        # 合并到缓存（缓存实际涨跌幅，而非等级）
        if use_cache:
            existing_data = cache.load_market_data()
            if existing_data and 'daily_changes' in existing_data:
                existing_data['daily_changes'].update(bz50_changes)
                cache.save_market_data(existing_data)
            else:
                cache.save_market_data({'daily_changes': bz50_changes})
        
        # 返回涨跌等级（用于相似度计算）
        result = {}
        for date, level in bz50_levels.items():
            date_num = date.replace('-', '')
            if start_date <= date_num <= end_date:
                result[date] = level
        
        return result
        
    except Exception as e:
        print(f"获取北证50指数失败: {e}")
        return {}


def calculate_individual_stocks_levels_cached(start_date: str, end_date: str,
                                              cache: StockDataCache, use_cache: bool = True,
                                              max_stocks: int = 10) -> Dict[str, Dict[str, int]]:
    """
    计算北交所每只股票每日涨跌幅度等级（带缓存）
    """
    stock_info = get_beijing_stocks_data()
    if stock_info.empty:
        print("无法获取股票列表，返回空数据")
        return {}
    
    if '证券代码' in stock_info.columns:
        stock_codes = stock_info['证券代码'].tolist()
    elif '代码' in stock_info.columns:
        stock_codes = stock_info['代码'].tolist()
    else:
        print("无法找到正确的股票代码列")
        return {}
    
    total_stocks = len(stock_codes)
    process_stocks = min(max_stocks, total_stocks)
    print(f"北交所共有 {total_stocks} 只股票，将处理前 {process_stocks} 只")
    
    stocks_levels = {}
    success_count = 0
    failed_count = 0
    
    for i, code in enumerate(stock_codes[:max_stocks]):
        print(f"\r正在获取个股数据 - 第 {i+1}/{process_stocks} 只股票: {code}", end='', flush=True)
        
        try:
            stock_data = fetch_and_cache_stock_data(str(code), start_date, end_date, cache, use_cache)
            
            if stock_data:
                stock_levels = {}
                for date, change_pct in stock_data.items():
                    level = calculate_price_change_level(change_pct)
                    stock_levels[date] = level
                
                stocks_levels[str(code)] = stock_levels
                success_count += 1
                print(f"  ✓ 股票 {code} 数据处理完成，共 {len(stock_levels)} 条记录")
            else:
                failed_count += 1
                print(f"  × 股票 {code} 没有数据")
                
        except Exception as e:
            failed_count += 1
            print(f"  × 处理股票 {code} 时出错: {e}")
            continue
        
        # 每处理10只股票后，额外休息2-5秒，防止请求过于频繁
        if (i + 1) % 10 == 0 and i + 1 < process_stocks:
            pause_time = random.uniform(2, 5)
            print(f"\n  已处理 {i+1} 只股票，休息 {pause_time:.1f} 秒后继续...")
            time.sleep(pause_time)
    
    print(f"\n总计: 成功 {success_count} 只，失败 {failed_count} 只")
    return stocks_levels


def calculate_similarity_with_market(stocks_levels: Dict[str, Dict[str, int]], 
                                   market_levels: Dict[str, int]) -> Dict[str, Dict[str, float]]:
    """计算每只股票与北交所大盘的相似度"""
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
    """按匹配率从高到低对所有股票进行排序"""
    sorted_results = sorted(
        similarity_results.items(),
        key=lambda x: x[1]['match_ratio'],
        reverse=True
    )
    return sorted_results


def calculate_single_stock_similarity(stock_code: str, start_date: str, end_date: str,
                                     cache: StockDataCache = None, use_cache: bool = True) -> Dict:
    """
    计算单支股票与北证50指数的匹配度
    
    :param stock_code: 股票代码 (例: "920000")
    :param start_date: 开始日期 (格式: YYYYMMDD)
    :param end_date: 结束日期 (格式: YYYYMMDD)
    :param cache: 缓存管理器，如果为None将自动创建
    :param use_cache: 是否使用缓存
    :return: {
        "stock_code": 股票代码,
        "match_days": 匹配天数,
        "total_days": 总天数,
        "match_ratio": 匹配率,
        "details": [
            {"date": 日期, "stock_level": 股票等级, "market_level": 市场等级, "matched": 是否匹配},
            ...
        ]
    }
    """
    # 初始化缓存管理器
    if cache is None:
        cache = StockDataCache("data")
    
    # 1. 获取北证50指数数据
    print(f"正在获取北证50指数数据...")
    market_levels = get_bz50_market_levels_cached(start_date, end_date, cache, use_cache)
    if not market_levels:
        return {
            "error": "无法获取北证50指数数据",
            "stock_code": stock_code,
            "match_days": 0,
            "total_days": 0,
            "match_ratio": 0.0,
            "details": []
        }
    print(f"✓ 获取到 {len(market_levels)} 天的北证50数据")
    
    # 2. 获取个股数据
    print(f"\n正在获取股票 {stock_code} 的数据...")
    stock_data = fetch_and_cache_stock_data(stock_code, start_date, end_date, cache, use_cache)
    if not stock_data:
        return {
            "error": f"无法获取股票 {stock_code} 数据",
            "stock_code": stock_code,
            "match_days": 0,
            "total_days": 0,
            "match_ratio": 0.0,
            "details": []
        }
    print(f"✓ 获取到 {len(stock_data)} 天的股票数据")
    
    # 3. 计算每日的等级和匹配度
    print(f"\n正在计算匹配度...")
    match_days = 0
    total_days = 0
    details = []
    
    # 获取所有共同日期并排序
    common_dates = sorted(set(stock_data.keys()) & set(market_levels.keys()))
    
    for date in common_dates:
        stock_change_pct = stock_data[date]
        stock_level = calculate_price_change_level(stock_change_pct)
        market_level = market_levels[date]
        
        is_matched = (stock_level == market_level)
        total_days += 1
        if is_matched:
            match_days += 1
        
        details.append({
            "date": date,
            "stock_change_pct": round(stock_change_pct, 2),
            "stock_level": stock_level,
            "market_level": market_level,
            "matched": is_matched
        })
    
    # 4. 计算匹配率
    match_ratio = match_days / total_days if total_days > 0 else 0.0
    
    result = {
        "stock_code": stock_code,
        "match_days": match_days,
        "total_days": total_days,
        "match_ratio": match_ratio,
        "details": details
    }
    
    # 5. 输出结果总结
    print(f"\n=== 匹配度分析结果 ===")
    print(f"股票代码: {stock_code}")
    print(f"分析时间范围: {start_date} ~ {end_date}")
    print(f"匹配天数: {match_days} / {total_days}")
    print(f"匹配率: {match_ratio:.2%}")
    
    return result


def main():
    """主函数"""
    print("=== 北交所股票分析系统（带缓存版本）===\n")
    
    # 加载配置
    config = load_config()
    print(f"配置信息:")
    print(f"  数据目录: {config['data_dir']}")
    print(f"  开始日期: {config['start_date']}")
    print(f"  结束日期: {config['end_date']}")
    print(f"  缓存启用: {config['cache_enabled']}")
    print(f"  最大股票数: {config['max_stocks']}")
    print()
    
    # 初始化缓存管理器
    cache = StockDataCache(config['data_dir'])
    
    # 获取北交所大盘每日涨跌等级
    print("正在获取北证50指数数据...")
    market_levels = get_bz50_market_levels_cached(
        config['start_date'],
        config['end_date'],
        cache,
        config['cache_enabled']
    )
    print(f"获取到 {len(market_levels)} 天的北证50数据")
    if market_levels:
        sample_dates = sorted(market_levels.keys())[:5]
        for date in sample_dates:
            level_desc = {4: "大涨", 3: "小涨", 2: "小跌", 1: "大跌"}
            print(f"  {date}: {market_levels[date]} ({level_desc[market_levels[date]]})")
    print()
    
    # 获取每只股票的涨跌等级
    print("正在获取个股数据...")
    stocks_levels = calculate_individual_stocks_levels_cached(
        config['start_date'],
        config['end_date'],
        cache,
        config['cache_enabled'],
        config['max_stocks']
    )
    print(f"获取到 {len(stocks_levels)} 只股票的数据")
    print()
    
    # 计算相似度
    print("正在计算股票与大盘的相似度...")
    similarity_results = calculate_similarity_with_market(stocks_levels, market_levels)
    print(f"计算出 {len(similarity_results)} 只股票的相似度")
    print()
    
    # 按相似度排序
    print("按相似度排序结果:")
    sorted_results = sort_stocks_by_similarity(similarity_results)
    
    if sorted_results:
        print(f"{'排名':<4} {'股票代码':<10} {'匹配天数':<10} {'总天数':<10} {'匹配率':<10}")
        print("-" * 50)
        
        for i, (stock_code, info) in enumerate(sorted_results):
            print(f"{i+1:<4} {stock_code:<10} {info['match_days']:<10} {info['total_days']:<10} {info['match_ratio']:<10.4f}")
    else:
        print("没有可排序的数据")



# ==================== 完整交易数据获取和缓存功能 ====================

def fetch_and_cache_full_stock_data(stock_code: str, start_date: str = None, end_date: str = None,
                                   cache: StockDataCache = None, use_cache: bool = True,
                                   stock_info_dict: dict = None) -> pd.DataFrame:
    """
    获取并缓存股票完整的交易数据（支持增量更新）
    
    :param stock_code: 股票代码
    :param start_date: 开始日期 (YYYYMMDD)，None表示使用股票上市日期
    :param end_date: 结束日期 (YYYYMMDD)，None表示使用今天日期
    :param cache: 缓存管理器，None表示使用默认缓存
    :param use_cache: 是否使用缓存
    :param stock_info_dict: 股票基本信息字典（证券简称、所属行业等）
    :return: DataFrame 包含完整交易数据
    
    返回的DataFrame包含字段：
    - date: 日期
    - open: 开盘价
    - high: 最高价
    - low: 最低价
    - close: 收盘价
    - volume: 成交量
    - amount: 成交额
    - amplitude: 振幅
    - pct_chg: 涨跌幅(%)
    - change: 涨跌额
    - turnover: 换手率
    """
    # 初始化缓存管理器
    if cache is None:
        cache = StockDataCache("data")
    
    # 如果未指定日期，使用默认范围
    if start_date is None or end_date is None:
        # 尝试从stock_info_dict获取上市日期
        list_date = None
        if stock_info_dict and '上市日期' in stock_info_dict:
            list_date_raw = stock_info_dict['上市日期']
            import datetime as dt
            if isinstance(list_date_raw, str):
                list_date = list_date_raw.replace('-', '')
            elif isinstance(list_date_raw, (dt.date, dt.datetime)):
                list_date = list_date_raw.strftime('%Y%m%d')
        
        # 如果没有提供，尝试从metadata获取
        if not list_date:
            actual_start, _ = cache.get_stock_actual_date_range(stock_code)
            if actual_start:
                list_date = actual_start.replace('-', '')
        
        # 设置默认日期范围
        if start_date is None:
            start_date = list_date if list_date else '20200101'  # 默认从2020年开始（北交所成立前后）
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')  # 今天
    
    # 缓存文件路径 (与原有缓存区分开)
    full_data_dir = os.path.join(cache.data_dir, "full_stocks")
    os.makedirs(full_data_dir, exist_ok=True)
    cache_file = os.path.join(full_data_dir, f"{stock_code}_full.json")
    
    if use_cache:
        # 检查缓存
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                cached_df = pd.DataFrame(cached_data['data'])
                cached_df['date'] = pd.to_datetime(cached_df['date'])
                
                # 检查缓存范围
                if not cached_df.empty:
                    cached_start = cached_df['date'].min().strftime('%Y%m%d')
                    cached_end = cached_df['date'].max().strftime('%Y%m%d')
                    
                    # 计算缺失范围
                    missing_ranges = calculate_missing_date_ranges(
                        cached_start, 
                        cached_end,
                        start_date,
                        end_date
                    )
                    
                    if not missing_ranges:
                        print(f"  股票 {stock_code} 使用完整数据缓存")
                        # 过滤出指定日期范围
                        mask = (cached_df['date'] >= pd.to_datetime(start_date)) & \
                               (cached_df['date'] <= pd.to_datetime(end_date))
                        return cached_df[mask].reset_index(drop=True)
                    else:
                        print(f"  股票 {stock_code} 需要下载缺失的完整数据: {missing_ranges}")
                else:
                    missing_ranges = [(start_date, end_date)]
        else:
            missing_ranges = [(start_date, end_date)]
    else:
        missing_ranges = [(start_date, end_date)]
    
    # 下载新数据
    all_dfs = []
    for range_start, range_end in missing_ranges:
        try:
            stock_df = get_beijing_stock_daily(str(stock_code), range_start, range_end)
            if not stock_df.empty:
                # 标准化列名
                column_mapping = {
                    '日期': 'date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '振幅': 'amplitude',
                    '涨跌幅': 'pct_chg',
                    '涨跌额': 'change',
                    '换手率': 'turnover'
                }
                stock_df = stock_df.rename(columns=column_mapping)
                stock_df['date'] = pd.to_datetime(stock_df['date'])
                all_dfs.append(stock_df)
        except Exception as e:
            print(f"  下载股票 {stock_code} 完整数据失败: {e}")
    
    # 合并数据
    if use_cache and os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
            cached_df = pd.DataFrame(cached_data['data'])
            cached_df['date'] = pd.to_datetime(cached_df['date'])
            all_dfs.insert(0, cached_df)
    
    if all_dfs:
        merged_df = pd.concat(all_dfs, ignore_index=True)
        merged_df = merged_df.drop_duplicates(subset=['date'], keep='last')
        merged_df = merged_df.sort_values('date').reset_index(drop=True)
        
        # 保存到缓存
        if use_cache:
            # 转换为JSON可序列化格式
            save_df = merged_df.copy()
            save_df['date'] = save_df['date'].dt.strftime('%Y-%m-%d')
            cache_data = {
                'stock_code': stock_code,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data': save_df.to_dict('records')
            }
            
            # 添加股票基本信息（如果提供）
            if stock_info_dict:
                import datetime as dt
                for key, value in stock_info_dict.items():
                    # 将pandas的Timestamp转换为字符串
                    if pd.api.types.is_datetime64_any_dtype(type(value)):
                        cache_data[key] = pd.to_datetime(value).strftime('%Y-%m-%d')
                    # 将Python datetime.date/datetime对象转换为字符串
                    elif isinstance(value, (dt.date, dt.datetime)):
                        cache_data[key] = value.strftime('%Y-%m-%d') if isinstance(value, dt.datetime) else value.isoformat()
                    # 将numpy类型转换为Python原生类型
                    elif hasattr(value, 'item'):
                        cache_data[key] = value.item()
                    # 处理NaN和None
                    elif pd.isna(value):
                        cache_data[key] = None
                    else:
                        cache_data[key] = value
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # 更新元数据
            if stock_code not in cache.metadata:
                cache.metadata[stock_code] = {}
            cache.metadata[stock_code]['full_data_last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if not merged_df.empty:
                cache.metadata[stock_code]['full_data_start'] = merged_df['date'].min().strftime('%Y-%m-%d')
                cache.metadata[stock_code]['full_data_end'] = merged_df['date'].max().strftime('%Y-%m-%d')
            cache._save_metadata()
        
        # 过滤出指定日期范围
        mask = (merged_df['date'] >= pd.to_datetime(start_date)) & \
               (merged_df['date'] <= pd.to_datetime(end_date))
        return merged_df[mask].reset_index(drop=True)
    
    return pd.DataFrame()


def fetch_all_bj_stocks_full_data(start_date: str = None, end_date: str = None, 
                                 cache: StockDataCache = None,
                                 use_cache: bool = True,
                                 max_stocks: int = None) -> Dict[str, pd.DataFrame]:
    """
    获取北交所所有股票的完整交易数据
    
    :param start_date: 开始日期 (YYYYMMDD)，None表示使用每只股票的上市日期
    :param end_date: 结束日期 (YYYYMMDD)，None表示使用今天日期
    :param cache: 缓存管理器
    :param use_cache: 是否使用缓存
    :param max_stocks: 最大股票数量，None表示全部
    :return: {stock_code: DataFrame}
    """
    if cache is None:
        cache = StockDataCache("data")
    
    # 获取股票列表
    stock_info = get_beijing_stocks_data()
    if stock_info.empty:
        print("无法获取股票列表")
        return {}
    
    # 创建股票代码到信息的映射字典
    stock_info_map = {}
    if '证券代码' in stock_info.columns:
        stock_codes = stock_info['证券代码'].tolist()
        # 为每个股票创建信息字典
        for idx, row in stock_info.iterrows():
            code = str(row['证券代码'])
            stock_info_map[code] = {
                '证券简称': row.get('证券简称', ''),
                '总股本': row.get('总股本', ''),
                '流通股本': row.get('流通股本', ''),
                '上市日期': row.get('上市日期', ''),
                '所属行业': row.get('所属行业', ''),
                '地区': row.get('地区', ''),
                '报告日期': row.get('报告日期', '')
            }
    elif '代码' in stock_info.columns:
        stock_codes = stock_info['代码'].tolist()
        # 为每个股票创建信息字典（兼容不同的列名）
        for idx, row in stock_info.iterrows():
            code = str(row['代码'])
            stock_info_map[code] = row.to_dict()
    else:
        print("无法找到股票代码列")
        return {}
    
    total_stocks = len(stock_codes)
    if max_stocks:
        stock_codes = stock_codes[:max_stocks]
    process_count = len(stock_codes)
    
    # 确定日期范围
    default_end_date = datetime.now().strftime('%Y%m%d') if end_date is None else end_date
    date_mode = "完整历史" if start_date is None else f"{start_date} ~ {default_end_date}"
    
    print(f"\n{'='*60}")
    print(f"北交所共有 {total_stocks} 只股票")
    print(f"将获取前 {process_count} 只股票的完整交易数据")
    print(f"时间范围: {date_mode}")
    if start_date is None:
        print(f"  (注：将根据每只股票的上市日期自动确定起始时间)")
    print(f"{'='*60}\n")
    
    all_stocks_data = {}
    success_count = 0
    failed_count = 0
    
    for i, code in enumerate(stock_codes):
        print(f"\r[{i+1}/{process_count}] 正在处理股票: {code}", end='', flush=True)
        
        try:
            # 获取该股票的基本信息
            info_dict = stock_info_map.get(str(code), None)
            df = fetch_and_cache_full_stock_data(str(code), start_date, end_date, cache, use_cache, info_dict)
            if not df.empty:
                all_stocks_data[str(code)] = df
                success_count += 1
                print(f"  ✓ 成功 (共 {len(df)} 条记录)")
            else:
                failed_count += 1
                print(f"  × 无数据")
        except Exception as e:
            failed_count += 1
            print(f"  × 失败: {e}")
        
        # 每处理10只股票后休息
        if (i + 1) % 10 == 0 and i + 1 < process_count:
            pause_time = random.uniform(2, 5)
            print(f"\n  已处理 {i+1} 只，休息 {pause_time:.1f} 秒...")
            time.sleep(pause_time)
    
    print(f"\n\n{'='*60}")
    print(f"完成！成功: {success_count} 只，失败: {failed_count} 只")
    print(f"{'='*60}")
    
    return all_stocks_data


if __name__ == "__main__":
    # main()
    # 测试获取完整历史数据（不指定日期，自动使用上市日期到今天）
    fetch_all_bj_stocks_full_data(
        max_stocks=3,
        use_cache=True,
        end_date="20260116",
    )
    
    # 或者指定日期范围获取部分数据
    # fetch_all_bj_stocks_full_data(
    #     start_date="20240601",
    #     end_date="20240831",
    #     max_stocks=10,
    #     use_cache=True
    # )