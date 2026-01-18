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
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib
import platform
warnings.filterwarnings('ignore')

# 设置matplotlib支持中文显示
def setup_chinese_font():
    """配置matplotlib中文字体"""
    system = platform.system()
    
    if system == 'Windows':
        # Windows系统使用微软雅黑或黑体
        matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
    elif system == 'Darwin':  # macOS
        # macOS使用苹方或黑体
        matplotlib.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS']
    else:  # Linux
        # Linux尝试使用Noto、文泉驿或Droid字体
        matplotlib.rcParams['font.sans-serif'] = [
            'Noto Sans CJK SC', 'Noto Sans CJK JP', 'Noto Sans CJK KR',
            'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei',
            'Droid Sans Fallback', 'DejaVu Sans'
        ]
    
    matplotlib.rcParams['axes.unicode_minus'] = False  # 用于正常显示负号

# 初始化中文字体配置
setup_chinese_font()


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


# 注：fetch_and_cache_stock_data 和 get_bz50_market_levels_cached 已被移除
# 现在统一使用 fetch_and_cache_full_stock_data 获取完整数据


def calculate_individual_stocks_levels_cached(start_date: str, end_date: str,
                                              cache: StockDataCache = None, use_cache: bool = True,
                                              max_stocks: int = 10) -> Dict[str, Dict[str, int]]:
    """
    计算北交所每只股票每日涨跌幅度等级（带缓存）
    使用 fetch_and_cache_full_stock_data 获取完整数据，提取涨跌幅并转换为等级
    
    :param start_date: 开始日期 (YYYYMMDD)
    :param end_date: 结束日期 (YYYYMMDD)
    :param cache: 缓存管理器
    :param use_cache: 是否使用缓存
    :param max_stocks: 最大股票数量
    :return: {stock_code: {date: level}}
    """
    if cache is None:
        cache = StockDataCache("data")
    
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
            # 使用 fetch_and_cache_full_stock_data 获取完整数据
            stock_df = fetch_and_cache_full_stock_data(
                str(code), start_date, end_date, cache, use_cache
            )
            
            if not stock_df.empty:
                stock_levels = {}
                # 从DataFrame中提取涨跌幅并转换为等级
                for _, row in stock_df.iterrows():
                    date = row['date'].strftime('%Y-%m-%d')
                    change_pct = float(row['pct_chg']) if pd.notna(row['pct_chg']) else 0.0
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
    使用 fetch_and_cache_full_stock_data 获取完整数据
    
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
    market_df = fetch_and_cache_full_stock_data("899050", start_date, end_date, cache, use_cache)
    if market_df.empty:
        return {
            "error": "无法获取北证50指数数据",
            "stock_code": stock_code,
            "match_days": 0,
            "total_days": 0,
            "match_ratio": 0.0,
            "details": []
        }
    print(f"✓ 获取到 {len(market_df)} 天的北证50数据")
    
    # 将北证50数据转换为 {date: level} 字典
    market_levels = {}
    for _, row in market_df.iterrows():
        date = row['date'].strftime('%Y-%m-%d')
        change_pct = float(row['pct_chg']) if pd.notna(row['pct_chg']) else 0.0
        level = calculate_price_change_level(change_pct)
        market_levels[date] = level
    
    # 2. 获取个股数据
    print(f"\n正在获取股票 {stock_code} 的数据...")
    stock_df = fetch_and_cache_full_stock_data(stock_code, start_date, end_date, cache, use_cache)
    if stock_df.empty:
        return {
            "error": f"无法获取股票 {stock_code} 数据",
            "stock_code": stock_code,
            "match_days": 0,
            "total_days": 0,
            "match_ratio": 0.0,
            "details": []
        }
    print(f"✓ 获取到 {len(stock_df)} 天的股票数据")
    
    # 3. 计算每日的等级和匹配度
    print(f"\n正在计算匹配度...")
    match_days = 0
    total_days = 0
    details = []
    
    # 遍历个股数据，与市场数据匹配
    for _, row in stock_df.iterrows():
        date = row['date'].strftime('%Y-%m-%d')
        if date in market_levels:
            stock_change_pct = float(row['pct_chg']) if pd.notna(row['pct_chg']) else 0.0
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
    market_df = fetch_and_cache_full_stock_data(
        "899050",
        config['start_date'],
        config['end_date'],
        cache,
        config['cache_enabled']
    )
    
    # 将DataFrame转换为等级字典
    market_levels = {}
    if not market_df.empty:
        for _, row in market_df.iterrows():
            date = row['date'].strftime('%Y-%m-%d')
            change_pct = float(row['pct_chg']) if pd.notna(row['pct_chg']) else 0.0
            level = calculate_price_change_level(change_pct)
            market_levels[date] = level
    
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



# ==================== 多因子计算功能 ====================

def calculate_correlation_factor(stock_df: pd.DataFrame, market_df: pd.DataFrame) -> dict:
    """
    计算相关性因子
    
    :param stock_df: 个股完整数据
    :param market_df: 市场(北证50)完整数据
    :return: 相关性因子字典，包含：
        - pearson_corr: Pearson相关系数
        - pearson_pvalue: Pearson相关系数的p值
        - spearman_corr: Spearman秩相关系数
        - spearman_pvalue: Spearman相关系数的p值
        - beta: Beta系数
        - direction_match_rate: 方向一致性（涨跌方向匹配率）
    """
    # 合并数据，只保留共同日期
    merged = pd.merge(
        stock_df[['date', 'pct_chg']],
        market_df[['date', 'pct_chg']],
        on='date',
        suffixes=('_stock', '_market')
    )
    
    if len(merged) < 5:  # 至少需要5个数据点
        return {
            'pearson_corr': np.nan,
            'pearson_pvalue': np.nan,
            'spearman_corr': np.nan,
            'spearman_pvalue': np.nan,
            'beta': np.nan,
            'direction_match_rate': np.nan
        }
    
    stock_returns = merged['pct_chg_stock'].values
    market_returns = merged['pct_chg_market'].values
    
    # Pearson相关系数 (使用scipy计算，包含p值)
    pearson_corr, pearson_pvalue = stats.pearsonr(stock_returns, market_returns)
    
    # Spearman秩相关系数 (适用于非线性关系)
    spearman_corr, spearman_pvalue = stats.spearmanr(stock_returns, market_returns)
    
    # Beta系数 = Cov(stock, market) / Var(market)
    cov_matrix = np.cov(stock_returns, market_returns)
    beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else np.nan
    
    # 方向一致性（同涨同跌）
    same_direction = ((stock_returns > 0) == (market_returns > 0)).sum()
    direction_match_rate = same_direction / len(merged)
    
    return {
        'pearson_corr': round(pearson_corr, 4),
        'pearson_pvalue': round(pearson_pvalue, 4),
        'spearman_corr': round(spearman_corr, 4),
        'spearman_pvalue': round(spearman_pvalue, 4),
        'beta': round(beta, 4),
        'direction_match_rate': round(direction_match_rate, 4)
    }


def calculate_volatility_factor(stock_df: pd.DataFrame, market_df: pd.DataFrame) -> dict:
    """
    计算波动性因子
    
    :param stock_df: 个股完整数据
    :param market_df: 市场(北证50)完整数据
    :return: 波动性因子字典，包含：
        - stock_volatility: 个股波动率（涨跌幅标准差）
        - market_volatility: 市场波动率（涨跌幅标准差）
        - relative_volatility: 相对波动率（个股/市场）
        - volatility_diff: 波动率差值
        - amplitude_corr: 振幅相关性
        - amplitude_pvalue: 振幅相关性的p值
    """
    stock_volatility = stock_df['pct_chg'].std()
    market_volatility = market_df['pct_chg'].std()
    
    relative_volatility = stock_volatility / market_volatility if market_volatility != 0 else np.nan
    volatility_diff = abs(stock_volatility - market_volatility)
    
    # 计算振幅相关性
    if 'amplitude' in stock_df.columns and 'amplitude' in market_df.columns:
        merged = pd.merge(stock_df[['date', 'amplitude']], 
                         market_df[['date', 'amplitude']], 
                         on='date', suffixes=('_stock', '_market'))
        if len(merged) >= 5:
            # 使用scipy计算相关系数
            amplitude_corr, amplitude_pvalue = stats.pearsonr(
                merged['amplitude_stock'].values,
                merged['amplitude_market'].values
            )
        else:
            amplitude_corr = np.nan
            amplitude_pvalue = np.nan
    else:
        amplitude_corr = np.nan
        amplitude_pvalue = np.nan
    
    return {
        'stock_volatility': round(stock_volatility, 4),
        'market_volatility': round(market_volatility, 4),
        'relative_volatility': round(relative_volatility, 4),
        'volatility_diff': round(volatility_diff, 4),
        'amplitude_corr': round(amplitude_corr, 4) if not np.isnan(amplitude_corr) else np.nan,
        'amplitude_pvalue': round(amplitude_pvalue, 4) if not np.isnan(amplitude_pvalue) else np.nan
    }


def calculate_volume_factor(stock_df: pd.DataFrame) -> dict:
    """
    计算成交量因子
    
    :param stock_df: 个股完整数据
    :return: 成交量因子字典，包含：
        - avg_volume: 平均成交量
        - volume_std: 成交量标准差
        - avg_turnover: 平均换手率
    """
    if 'volume' not in stock_df.columns or stock_df['volume'].isna().all():
        return {
            'avg_volume': np.nan,
            'volume_std': np.nan,
            'avg_turnover': np.nan
        }
    
    avg_volume = stock_df['volume'].mean()
    volume_std = stock_df['volume'].std()
    avg_turnover = stock_df['turnover'].mean() if 'turnover' in stock_df.columns else np.nan
    
    return {
        'avg_volume': round(avg_volume, 2),
        'volume_std': round(volume_std, 2),
        'avg_turnover': round(avg_turnover, 4) if not np.isnan(avg_turnover) else np.nan
    }


def calculate_total_return(stock_code: str, start_date: str, end_date: str,
                          cache: StockDataCache = None, use_cache: bool = True) -> dict:
    """
    计算指定股票在指定日期范围内的总涨跌幅度
    
    :param stock_code: 股票代码
    :param start_date: 开始日期 (YYYYMMDD)
    :param end_date: 结束日期 (YYYYMMDD)
    :param cache: 缓存管理器
    :param use_cache: 是否使用缓存
    :return: {
        'stock_code': 股票代码,
        'start_date': 开始日期,
        'end_date': 结束日期,
        'start_price': 期初价格,
        'end_price': 期末价格,
        'total_return': 总涨跌幅(%),
        'trading_days': 交易天数,
        'error': 错误信息（如果有）
    }
    """
    if cache is None:
        cache = StockDataCache("data")
    
    try:
        # 获取股票完整数据
        stock_df = fetch_and_cache_full_stock_data(
            stock_code, start_date, end_date, cache, use_cache
        )
        
        if stock_df.empty:
            return {
                'stock_code': stock_code,
                'start_date': start_date,
                'end_date': end_date,
                'start_price': None,
                'end_price': None,
                'total_return': None,
                'trading_days': 0,
                'error': '无数据'
            }
        
        # 按日期排序
        stock_df = stock_df.sort_values('date')
        
        # 获取期初和期末价格
        start_price = float(stock_df.iloc[0]['close'])
        end_price = float(stock_df.iloc[-1]['close'])
        trading_days = len(stock_df)
        
        # 计算总涨跌幅 = (期末价格 - 期初价格) / 期初价格 * 100
        total_return = ((end_price - start_price) / start_price) * 100
        
        return {
            'stock_code': stock_code,
            'start_date': stock_df.iloc[0]['date'].strftime('%Y-%m-%d'),
            'end_date': stock_df.iloc[-1]['date'].strftime('%Y-%m-%d'),
            'start_price': round(start_price, 2),
            'end_price': round(end_price, 2),
            'total_return': round(total_return, 2),
            'trading_days': trading_days,
            'error': None
        }
        
    except Exception as e:
        return {
            'stock_code': stock_code,
            'start_date': start_date,
            'end_date': end_date,
            'start_price': None,
            'end_price': None,
            'total_return': None,
            'trading_days': 0,
            'error': str(e)
        }


def calculate_all_stocks_total_return(start_date: str, end_date: str,
                                     cache: StockDataCache = None,
                                     use_cache: bool = True,
                                     max_stocks: int = None) -> pd.DataFrame:
    """
    计算所有北交所股票在指定日期范围内的总涨跌幅度
    
    :param start_date: 开始日期 (YYYYMMDD)
    :param end_date: 结束日期 (YYYYMMDD)
    :param cache: 缓存管理器
    :param use_cache: 是否使用缓存
    :param max_stocks: 最大股票数量，None表示全部
    :return: DataFrame包含所有股票的总涨跌幅信息
    """
    if cache is None:
        cache = StockDataCache("data")
    
    # 获取股票列表
    stock_info = get_beijing_stocks_data()
    if stock_info.empty:
        print("无法获取股票列表")
        return pd.DataFrame()
    
    if '证券代码' in stock_info.columns:
        stock_codes = stock_info['证券代码'].tolist()
    elif '代码' in stock_info.columns:
        stock_codes = stock_info['代码'].tolist()
    else:
        print("无法找到股票代码列")
        return pd.DataFrame()
    
    # 创建股票信息映射
    stock_name_map = {}
    if '证券代码' in stock_info.columns and '证券简称' in stock_info.columns:
        for _, row in stock_info.iterrows():
            stock_name_map[str(row['证券代码'])] = row['证券简称']
    
    total_stocks = len(stock_codes)
    if max_stocks:
        stock_codes = stock_codes[:max_stocks]
    process_count = len(stock_codes)
    
    print(f"\n{'='*60}")
    print(f"北交所共有 {total_stocks} 只股票")
    print(f"将计算前 {process_count} 只股票的总涨跌幅")
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"{'='*60}\n")
    
    results = []
    success_count = 0
    failed_count = 0
    
    for i, code in enumerate(stock_codes):
        print(f"\r[{i+1}/{process_count}] 正在处理: {code}", end='', flush=True)
        
        result = calculate_total_return(str(code), start_date, end_date, cache, use_cache)
        
        # 添加股票名称
        result['stock_name'] = stock_name_map.get(str(code), '')
        results.append(result)
        
        if result['error'] is None:
            success_count += 1
            print(f"  ✓ {result['total_return']:>8.2f}%")
        else:
            failed_count += 1
            print(f"  × {result['error']}")
        
        # 每处理10只股票后休息
        if (i + 1) % 10 == 0 and i + 1 < process_count:
            pause_time = random.uniform(2, 5)
            print(f"\n  已处理 {i+1} 只，休息 {pause_time:.1f} 秒...")
            time.sleep(pause_time)
    
    print(f"\n\n{'='*60}")
    print(f"完成！成功: {success_count} 只，失败: {failed_count} 只")
    print(f"{'='*60}")
    
    # 转换为DataFrame
    df = pd.DataFrame(results)
    
    # 按总涨跌幅排序
    if not df.empty and 'total_return' in df.columns:
        df = df.sort_values('total_return', ascending=False, na_position='last')
    
    return df


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


# ==================== 综合因子计算与可视化 ====================

def fetch_and_cache_bz50_data(start_date: str, end_date: str,
                             cache: StockDataCache = None,
                             use_cache: bool = True) -> pd.DataFrame:
    """
    获取并缓存北证50指数数据
    
    :param start_date: 开始日期 (YYYYMMDD)
    :param end_date: 结束日期 (YYYYMMDD)
    :param cache: 缓存管理器
    :param use_cache: 是否使用缓存
    :return: 北证50指数DataFrame
    """
    if cache is None:
        cache = StockDataCache("data")
    
    # 北证50指数代码
    bz50_code = "899050"
    
    # 使用fetch_and_cache_full_stock_data获取数据
    market_df = fetch_and_cache_full_stock_data(
        bz50_code, start_date, end_date, cache, use_cache
    )
    
    return market_df


def calculate_all_factors_and_compare(start_date: str, end_date: str,
                                     cache: StockDataCache = None,
                                     use_cache: bool = True,
                                     max_stocks: int = 20,
                                     output_file: str = None) -> pd.DataFrame:
    """
    综合计算所有因子并与总涨跌幅对比
    
    :param start_date: 开始日期 (YYYYMMDD)
    :param end_date: 结束日期 (YYYYMMDD)
    :param cache: 缓存管理器
    :param use_cache: 是否使用缓存
    :param max_stocks: 最大股票数量
    :param output_file: 输出CSV文件路径
    :return: DataFrame包含所有因子和总涨跌幅
    """
    if cache is None:
        cache = StockDataCache("data")
    
    # 获取北证50数据
    print("\n正在获取北证50指数数据...")
    market_df = fetch_and_cache_bz50_data(start_date, end_date, cache, use_cache)
    if market_df.empty:
        print("无法获取北证50数据")
        return pd.DataFrame()
    
    # 获取股票列表
    stock_info = get_beijing_stocks_data()
    if stock_info.empty:
        print("无法获取股票列表")
        return pd.DataFrame()
    
    if '证券代码' in stock_info.columns:
        stock_codes = stock_info['证券代码'].tolist()
    elif '代码' in stock_info.columns:
        stock_codes = stock_info['代码'].tolist()
    else:
        print("无法找到股票代码列")
        return pd.DataFrame()
    
    # 创建股票名称映射
    stock_name_map = {}
    if '证券代码' in stock_info.columns and '证券简称' in stock_info.columns:
        for _, row in stock_info.iterrows():
            stock_name_map[str(row['证券代码'])] = row['证券简称']
    
    # 限制股票数量
    if max_stocks:
        stock_codes = stock_codes[:max_stocks]
    
    print(f"\n{'='*70}")
    print(f"将计算 {len(stock_codes)} 只股票的综合因子")
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"{'='*70}\n")
    
    results = []
    success_count = 0
    failed_count = 0
    
    for i, code in enumerate(stock_codes):
        stock_code = str(code)
        stock_name = stock_name_map.get(stock_code, '')
        print(f"\r[{i+1}/{len(stock_codes)}] 正在处理: {stock_code} {stock_name}", end='', flush=True)
        
        try:
            # 获取股票完整数据
            stock_df = fetch_and_cache_full_stock_data(
                stock_code, start_date, end_date, cache, use_cache
            )
            
            if stock_df.empty:
                failed_count += 1
                print(f"  × 无数据")
                continue
            
            # 1. 计算总涨跌幅
            start_price = float(stock_df.iloc[0]['close'])
            end_price = float(stock_df.iloc[-1]['close'])
            total_return = ((end_price - start_price) / start_price) * 100
            
            # 2. 计算涨跌幅匹配度因子
            stock_levels = {}
            market_levels = {}
            for _, row in stock_df.iterrows():
                date = row['date'].strftime('%Y-%m-%d')
                change_pct = float(row['pct_chg']) if pd.notna(row['pct_chg']) else 0.0
                stock_levels[date] = calculate_price_change_level(change_pct)
            
            for _, row in market_df.iterrows():
                date = row['date'].strftime('%Y-%m-%d')
                change_pct = float(row['pct_chg']) if pd.notna(row['pct_chg']) else 0.0
                market_levels[date] = calculate_price_change_level(change_pct)
            
            match_days = 0
            total_days = 0
            for date, stock_level in stock_levels.items():
                if date in market_levels:
                    total_days += 1
                    if stock_level == market_levels[date]:
                        match_days += 1
            
            match_ratio = match_days / total_days if total_days > 0 else 0
            
            # 3. 计算相关性因子
            corr_factor = calculate_correlation_factor(stock_df, market_df)
            
            # 4. 计算波动性因子
            vol_factor = calculate_volatility_factor(stock_df, market_df)
            
            # 5. 计算成交量因子
            volume_factor = calculate_volume_factor(stock_df)
            
            # 整合结果
            result = {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'trading_days': len(stock_df),
                'total_return': round(total_return, 2),
                # 涨跌幅匹配度因子
                'match_ratio': round(match_ratio, 4),
                # 相关性因子
                'pearson_corr': corr_factor['pearson_corr'],
                'spearman_corr': corr_factor['spearman_corr'],
                'beta': corr_factor['beta'],
                'direction_match_rate': corr_factor['direction_match_rate'],
                # 波动性因子
                'stock_volatility': vol_factor['stock_volatility'],
                'relative_volatility': vol_factor['relative_volatility'],
                'amplitude_corr': vol_factor['amplitude_corr'],
                # 成交量因子
                'avg_volume': volume_factor['avg_volume'],
                'avg_turnover': volume_factor['avg_turnover']
            }
            
            results.append(result)
            success_count += 1
            print(f"  ✓ 总涨跌幅: {total_return:>8.2f}%, 匹配率: {match_ratio:>6.2%}")
            
        except Exception as e:
            failed_count += 1
            print(f"  × 失败: {e}")
        
        # 每处理10只股票后休息
        if (i + 1) % 10 == 0 and i + 1 < len(stock_codes):
            pause_time = random.uniform(2, 4)
            print(f"\n  已处理 {i+1} 只，休息 {pause_time:.1f} 秒...")
            time.sleep(pause_time)
    
    print(f"\n\n{'='*70}")
    print(f"完成！成功: {success_count} 只，失败: {failed_count} 只")
    print(f"{'='*70}")
    
    # 转换为DataFrame
    df = pd.DataFrame(results)
    
    # 按总涨跌幅排序
    if not df.empty and 'total_return' in df.columns:
        df = df.sort_values('total_return', ascending=False, na_position='last')
    
    # 保存到文件
    if output_file and not df.empty:
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存到: {output_file}")
    
    return df


def plot_factors_comparison(df: pd.DataFrame, output_image: str = None, chart_type: str = 'bar'):
    """
    绘制因子与总涨跌幅对比图
    
    :param df: 包含所有因子的DataFrame
    :param output_image: 输出图片路径
    :param chart_type: 图表类型，'bar'为柱状图，'line'为线图
    """
    if df.empty:
        print("数据为空，无法绘图")
        return
    
    # 过滤掉无效数据
    df = df.dropna(subset=['total_return'])
    
    if df.empty:
        print("没有有效数据，无法绘图")
        return
    
    # 确保中文字体已配置
    setup_chinese_font()
    
    # 准备数据：选择关键因子
    stock_labels = df['stock_name'].tolist() if 'stock_name' in df.columns else df['stock_code'].tolist()
    
    # 创建图表
    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    chart_type_title = '柱状图' if chart_type == 'bar' else '线图'
    fig.suptitle(f'北交所股票因子与总涨跌幅对比分析（{chart_type_title}）', fontsize=16, fontweight='bold')
    
    # 1. 总涨跌幅 vs 涨跌幅匹配率
    ax1 = axes[0, 0]
    x_pos = np.arange(len(stock_labels))
    
    # 归一化数据到同一范围以便对比
    total_return_normalized = df['total_return'].values
    match_ratio_normalized = df['match_ratio'].values * 100  # 转换为百分比
    
    if chart_type == 'line':
        ax1.plot(x_pos, total_return_normalized, marker='o', label='总涨跌幅(%)', color='steelblue', linewidth=2, markersize=6)
        ax1.plot(x_pos, match_ratio_normalized, marker='s', label='匹配率(%)', color='coral', linewidth=2, markersize=6)
    else:  # bar
        width = 0.35
        ax1.bar(x_pos - width/2, total_return_normalized, width, label='总涨跌幅(%)', color='steelblue')
        ax1.bar(x_pos + width/2, match_ratio_normalized, width, label='匹配率(%)', color='coral')
    
    ax1.set_ylabel('数值(%)')
    ax1.set_title('总涨跌幅 vs 涨跌幅匹配率')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(stock_labels, rotation=45, ha='right', fontsize=8)
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    # 2. 总涨跌幅 vs Pearson相关系数
    ax2 = axes[0, 1]
    pearson_normalized = df['pearson_corr'].values * 100  # 缩放到百分比
    
    if chart_type == 'line':
        ax2.plot(x_pos, total_return_normalized, marker='o', label='总涨跌幅(%)', color='steelblue', linewidth=2, markersize=6)
        ax2.plot(x_pos, pearson_normalized, marker='s', label='Pearson相关系数×100', color='lightgreen', linewidth=2, markersize=6)
    else:
        width = 0.35
        ax2.bar(x_pos - width/2, total_return_normalized, width, label='总涨跌幅(%)', color='steelblue')
        ax2.bar(x_pos + width/2, pearson_normalized, width, label='Pearson相关系数×100', color='lightgreen')
    
    ax2.set_ylabel('数值')
    ax2.set_title('总涨跌幅 vs Pearson相关系数')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(stock_labels, rotation=45, ha='right', fontsize=8)
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    # 3. 总涨跌幅 vs Beta系数
    ax3 = axes[1, 0]
    beta_normalized = df['beta'].values * 50  # 缩放Beta系数
    
    if chart_type == 'line':
        ax3.plot(x_pos, total_return_normalized, marker='o', label='总涨跌幅(%)', color='steelblue', linewidth=2, markersize=6)
        ax3.plot(x_pos, beta_normalized, marker='s', label='Beta系数×50', color='gold', linewidth=2, markersize=6)
    else:
        width = 0.35
        ax3.bar(x_pos - width/2, total_return_normalized, width, label='总涨跌幅(%)', color='steelblue')
        ax3.bar(x_pos + width/2, beta_normalized, width, label='Beta系数×50', color='gold')
    
    ax3.set_ylabel('数值')
    ax3.set_title('总涨跌幅 vs Beta系数')
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(stock_labels, rotation=45, ha='right', fontsize=8)
    ax3.legend()
    ax3.grid(axis='y', alpha=0.3)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    # 4. 总涨跌幅 vs 方向一致性
    ax4 = axes[1, 1]
    direction_normalized = df['direction_match_rate'].values * 100
    
    if chart_type == 'line':
        ax4.plot(x_pos, total_return_normalized, marker='o', label='总涨跌幅(%)', color='steelblue', linewidth=2, markersize=6)
        ax4.plot(x_pos, direction_normalized, marker='s', label='方向一致性(%)', color='mediumpurple', linewidth=2, markersize=6)
    else:
        width = 0.35
        ax4.bar(x_pos - width/2, total_return_normalized, width, label='总涨跌幅(%)', color='steelblue')
        ax4.bar(x_pos + width/2, direction_normalized, width, label='方向一致性(%)', color='mediumpurple')
    
    ax4.set_ylabel('数值(%)')
    ax4.set_title('总涨跌幅 vs 方向一致性')
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(stock_labels, rotation=45, ha='right', fontsize=8)
    ax4.legend()
    ax4.grid(axis='y', alpha=0.3)
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    # 5. 总涨跌幅 vs 相对波动率
    ax5 = axes[2, 0]
    rel_vol_normalized = df['relative_volatility'].values * 50  # 缩放相对波动率
    
    if chart_type == 'line':
        ax5.plot(x_pos, total_return_normalized, marker='o', label='总涨跌幅(%)', color='steelblue', linewidth=2, markersize=6)
        ax5.plot(x_pos, rel_vol_normalized, marker='s', label='相对波动率×50', color='salmon', linewidth=2, markersize=6)
    else:
        width = 0.35
        ax5.bar(x_pos - width/2, total_return_normalized, width, label='总涨跌幅(%)', color='steelblue')
        ax5.bar(x_pos + width/2, rel_vol_normalized, width, label='相对波动率×50', color='salmon')
    
    ax5.set_ylabel('数值')
    ax5.set_title('总涨跌幅 vs 相对波动率')
    ax5.set_xticks(x_pos)
    ax5.set_xticklabels(stock_labels, rotation=45, ha='right', fontsize=8)
    ax5.legend()
    ax5.grid(axis='y', alpha=0.3)
    ax5.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    # 6. 总涨跌幅 vs 平均换手率
    ax6 = axes[2, 1]
    # 过滤掉NaN值
    turnover_data = df['avg_turnover'].fillna(0).values * 10  # 缩放换手率
    
    if chart_type == 'line':
        ax6.plot(x_pos, total_return_normalized, marker='o', label='总涨跌幅(%)', color='steelblue', linewidth=2, markersize=6)
        ax6.plot(x_pos, turnover_data, marker='s', label='平均换手率×10', color='lightcoral', linewidth=2, markersize=6)
    else:
        width = 0.35
        ax6.bar(x_pos - width/2, total_return_normalized, width, label='总涨跌幅(%)', color='steelblue')
        ax6.bar(x_pos + width/2, turnover_data, width, label='平均换手率×10', color='lightcoral')
    
    ax6.set_ylabel('数值')
    ax6.set_title('总涨跌幅 vs 平均换手率')
    ax6.set_xticks(x_pos)
    ax6.set_xticklabels(stock_labels, rotation=45, ha='right', fontsize=8)
    ax6.legend()
    ax6.grid(axis='y', alpha=0.3)
    ax6.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    plt.tight_layout()
    
    # 保存图片
    if output_image:
        plt.savefig(output_image, dpi=300, bbox_inches='tight')
        print(f"\n图表已保存到: {output_image}")
    
    plt.show()


def analyze_factors_and_visualize(start_date: str = '20240101', end_date: str = '20241231',
                                 max_stocks: int = 20,
                                 use_cache: bool = True,
                                 chart_type: str = 'bar'):
    """
    综合分析：计算所有因子并生成可视化对比图
    
    :param start_date: 开始日期 (YYYYMMDD)
    :param end_date: 结束日期 (YYYYMMDD)
    :param max_stocks: 最大股票数量
    :param use_cache: 是否使用缓存
    :param chart_type: 图表类型，'bar'为柱状图，'line'为线图
    """
    # 生成输出文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = f'factors_comparison_{timestamp}.csv'
    image_file = f'factors_comparison_{chart_type}_{timestamp}.png'
    
    # 计算所有因子
    print("="*70)
    print("开始综合因子分析...")
    print("="*70)
    
    df = calculate_all_factors_and_compare(
        start_date=start_date,
        end_date=end_date,
        max_stocks=max_stocks,
        use_cache=use_cache,
        output_file=csv_file
    )
    
    if not df.empty:
        # 显示统计摘要
        print("\n" + "="*70)
        print("统计摘要")
        print("="*70)
        print(f"平均总涨跌幅: {df['total_return'].mean():.2f}%")
        print(f"平均匹配率: {df['match_ratio'].mean():.2%}")
        print(f"平均Pearson相关系数: {df['pearson_corr'].mean():.4f}")
        print(f"平均Beta系数: {df['beta'].mean():.4f}")
        print(f"平均方向一致性: {df['direction_match_rate'].mean():.2%}")
        print(f"平均相对波动率: {df['relative_volatility'].mean():.4f}")
        
        # 生成可视化图表
        chart_type_name = '柱状图' if chart_type == 'bar' else '线图'
        print(f"\n生成可视化图表（{chart_type_name}）...")
        plot_factors_comparison(df, output_image=image_file, chart_type=chart_type)
    else:
        print("\n没有数据可供分析")


if __name__ == "__main__":
    main()
    # 测试获取完整历史数据（不指定日期，自动使用上市日期到今天）
    # fetch_all_bj_stocks_full_data(
    #     max_stocks=3,
    #     use_cache=True,
    #     end_date="20260116",
    # )
    
    # 或者指定日期范围获取部分数据
    # fetch_all_bj_stocks_full_data(
    #     start_date="20240601",
    #     end_date="20240831",
    #     max_stocks=10,
    #     use_cache=True
    # )