from typing import List, Dict, Set


class AssetBucketManager:
    def __init__(self):
        self.asset_buckets = {
            'Risk Assets': [
                'RKLB', 'MSFT', 'NVDA', 'AAPL', 'AMZN', 'META', 'AVGO', 'GOOG', 'GOOGL', 'BRK.B', 'TSLA',
                'JPM', 'WMT', 'LLY', 'ORCL', 'NFLX', 'MA', 'XOM', 'COST', 'PG', 'JNJ', 'HD', 'BAC', 'PLTR',
                'ABBV', 'KO', 'PM', 'UNH', 'IBM', 'CSCO', 'CVX', 'GE', 'TMUS', 'CRM', 'WFC', 'ABT', 'LIN',
                'MS', 'DIS', 'INTU', 'AXP', 'MCD', 'AMD', 'NOW', 'MRK', 'T', 'GS', 'RTX', 'ACN', 'ISRG',
                'TXN', 'PEP', 'VZ', 'UBER', 'BKNG', 'CAT', 'QCOM', 'SCHW', 'ADBE', 'AMGN', 'SPGI', 'PGR',
                'BLK', 'BSX', 'BA', 'TMO', 'NEE', 'C', 'HON', 'SYK', 'DE', 'DHR', 'AMAT', 'TJX', 'MU',
                'PFE', 'GILD', 'PANW', 'UNP', 'ETN', 'CMCSA', 'COF', 'ADP', 'CRWD', 'COP', 'LOW',
                'LRCX', 'KLAC', 'VRTX', 'ADI', 'ANET', 'CB', 'APH', 'MDT', 'LMT', 'KKR', 'MMC', 'BX',
                'SBUX', 'ICE', 'AMT', 'MO', 'WELL', 'CME', 'SO', 'PLD', 'CEG', 'BMY', 'WM', 'INTC'
            ],
            'Defensive Assets': ['AGG', 'BND', 'XLP', 'XLU'],
            'High Beta': [
                'SPHB', 'HIBL', 'SSO',
                'BTC', 'ETH', 'USDT', 'XRP', 'SOL', 'DOGE', 'ADA', 'BCH', 'LINK', 'AVAX',
                'SHIB', 'LTC', 'DOT', 'DAI', 'AAVE'
            ],
            'Low Beta': ['USMV', 'SPLV'],
            'Cyclicals': ['XLY', 'XLI', 'XLB', 'XLF'],
            'Defensives': ['XLP', 'XLU', 'VIG'],
            'Growth': ['IWF', 'VUG', 'SPYG', 'QQQ'],
            'Value': ['IWD', 'VTV', 'SPYV'],
            'SMID Caps': ['VSM', 'SLY', 'IJR', 'IJH'],
            'Large Caps': ['SPY', 'VOO', 'IVV'],
            'US': ['SPY', 'VTI', 'IVV'],
            'International': ['EFA', 'VEA', 'IEFA'],
            'EM': ['EEM', 'VWO', 'IEMG'],
            'DM': ['EFA', 'VEA', 'IEFA'],
            'Spread Products': ['LQD', 'HYG'],
            'Treasurys': ['TLT', 'IEF', 'SHY', 'VGSH'],
            'Short Rates': ['SHV', 'SGOV', 'SHY'],
            'Belly': ['IEI', 'VGIT'],
            'Long Rates': ['TLT', 'VGLT'],
            'High Yield': ['JNK', 'HYG', 'PHB', 'SPHY', 'ANGL'],
            'Investment Grade': ['LQD', 'VCIT'],
            'Industrial Commodities': ['DBB', 'CPER', 'JJC'],
            'Energy Commodities': ['USO', 'UNG', 'XLE', 'OIH'],
            'Agricultural Commodities': ['DBA', 'CORN', 'SOYB'],
            'Gold': ['GLD', 'IAU', 'SGOL', 'BAR', 'AAAU'],
            'FX': ['FXE', 'FXY', 'FXB', 'FXF'],
            'USD': ['UUP', 'CYB']
        }

    def get_bucket_assets(self, bucket_name: str) -> List[str]:
        return self.asset_buckets.get(bucket_name, [])
    
    def get_assets_from_buckets(self, bucket_names: List[str]) -> List[str]:
        assets = []
        for bucket_name in bucket_names:
            assets.extend(self.get_bucket_assets(bucket_name))
        return list(set(assets))  # Remove duplicates
    
    def get_all_assets_from_buckets(self, bucket_names: List[str] = None) -> List[str]:
        if bucket_names is None:
            bucket_names = list(self.asset_buckets.keys())
        
        all_assets = set()
        for bucket_name in bucket_names:
            all_assets.update(self.get_bucket_assets(bucket_name))
        
        return list(all_assets)
    
    def get_bucket_for_asset(self, asset: str) -> List[str]:
        buckets = []
        for bucket_name, assets in self.asset_buckets.items():
            if asset in assets:
                buckets.append(bucket_name)
        return buckets
    
    def get_available_buckets(self) -> List[str]:
        return list(self.asset_buckets.keys())
    
    def add_asset_to_bucket(self, bucket_name: str, asset: str):
        if bucket_name not in self.asset_buckets:
            self.asset_buckets[bucket_name] = []
        
        if asset not in self.asset_buckets[bucket_name]:
            self.asset_buckets[bucket_name].append(asset)
    
    def remove_asset_from_bucket(self, bucket_name: str, asset: str):
        if bucket_name in self.asset_buckets and asset in self.asset_buckets[bucket_name]:
            self.asset_buckets[bucket_name].remove(asset)
    
    def create_custom_bucket(self, bucket_name: str, assets: List[str]):
        self.asset_buckets[bucket_name] = assets.copy()
    
    def get_bucket_intersection(self, bucket_names: List[str]) -> List[str]:
        if not bucket_names:
            return []
        
        asset_sets = [set(self.get_bucket_assets(bucket)) for bucket in bucket_names]
        intersection = asset_sets[0]
        
        for asset_set in asset_sets[1:]:
            intersection = intersection.intersection(asset_set)
        
        return list(intersection)
    
    def get_bucket_union(self, bucket_names: List[str]) -> List[str]:
        return self.get_assets_from_buckets(bucket_names)
    
    def filter_assets_by_type(self, assets: List[str], asset_type: str) -> List[str]:
        crypto_assets = {
            'BTC', 'ETH', 'USDT', 'XRP', 'BNB', 'SOL', 'USDC', 'TRX', 'DOGE', 'ADA',
            'BCH', 'LINK','AVAX', 'TON', 'SHIB', 'LTC', 'DOT',
            'DAI', 'AAVE'
        }
        
        etf_prefixes = ['SPY', 'QQQ', 'IWF', 'VUG', 'SPYG', 'IWD', 'VTV', 'SPYV', 'XL', 'AGG', 'BND']
        
        if asset_type.lower() == 'crypto':
            return [asset for asset in assets if asset in crypto_assets]
        elif asset_type.lower() == 'etf':
            return [asset for asset in assets if any(asset.startswith(prefix) for prefix in etf_prefixes)]
        elif asset_type.lower() == 'stock':
            return [asset for asset in assets if asset not in crypto_assets and 
                   not any(asset.startswith(prefix) for prefix in etf_prefixes)]
        else:
            return assets
    
    def get_bucket_stats(self) -> Dict[str, Dict]:
        stats = {}
        for bucket_name, assets in self.asset_buckets.items():
            stats[bucket_name] = {
                'total_assets': len(assets),
                'crypto_count': len(self.filter_assets_by_type(assets, 'crypto')),
                'etf_count': len(self.filter_assets_by_type(assets, 'etf')),
                'stock_count': len(self.filter_assets_by_type(assets, 'stock'))
            }
        return stats