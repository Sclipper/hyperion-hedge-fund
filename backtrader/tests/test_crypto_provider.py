"""
Test suite for Alpha Vantage crypto provider
Tests crypto data fetching with proper error handling
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import os
from unittest.mock import Mock, patch
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.providers.alpha_vantage.crypto_provider import AlphaVantageCryptoProvider


class TestAlphaVantageCryptoProvider:
    """Test crypto provider functionality"""
    
    @pytest.fixture
    def crypto_provider(self):
        """Create crypto provider instance with mocked API key"""
        with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
            provider = AlphaVantageCryptoProvider()
            # Mock the rate limiting to speed up tests
            provider._rate_limit = Mock()
            return provider
    
    def test_supported_crypto_list(self, crypto_provider):
        """Test getting supported cryptocurrency list"""
        # Test with known supported cryptos
        known_cryptos = crypto_provider.KNOWN_SUPPORTED_CRYPTOS
        assert 'BTC' in known_cryptos
        assert 'ETH' in known_cryptos
        assert 'DOGE' in known_cryptos
        assert len(known_cryptos) > 20
    
    def test_is_crypto_supported(self, crypto_provider):
        """Test crypto support checking"""
        # Supported cryptos
        assert crypto_provider.is_crypto_supported('BTC')
        assert crypto_provider.is_crypto_supported('ETH')
        assert crypto_provider.is_crypto_supported('BTCUSD')  # Should strip USD
        
        # Use known list for testing
        crypto_provider._supported_cryptos = crypto_provider.KNOWN_SUPPORTED_CRYPTOS
        
        # Unsupported cryptos
        assert not crypto_provider.is_crypto_supported('FAKE123')
        assert not crypto_provider.is_crypto_supported('UNKNOWN')
    
    @patch('requests.Session.get')
    def test_fetch_crypto_intraday_success(self, mock_get, crypto_provider):
        """Test successful crypto intraday data fetch"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Meta Data': {
                '1. Information': 'Intraday Prices for Digital Currency',
                '2. Digital Currency Code': 'BTC',
                '3. Digital Currency Name': 'Bitcoin',
                '4. Market Code': 'USD',
                '5. Market Name': 'United States Dollar',
                '6. Interval': '60min',
                '7. Last Refreshed': '2025-07-27 23:00:00',
                '8. Time Zone': 'UTC'
            },
            'Time Series Crypto (60min)': {
                '2025-07-27 23:00:00': {
                    '1. open': '95000.00',
                    '2. high': '95500.00',
                    '3. low': '94500.00',
                    '4. close': '95200.00',
                    '5. volume': '1000.50'
                },
                '2025-07-27 22:00:00': {
                    '1. open': '94800.00',
                    '2. high': '95000.00',
                    '3. low': '94600.00',
                    '4. close': '95000.00',
                    '5. volume': '1200.75'
                }
            }
        }
        mock_get.return_value = mock_response
        
        # Test fetching data
        start_date = datetime(2025, 7, 27, 22, 0, 0)
        end_date = datetime(2025, 7, 27, 23, 0, 0)
        
        df = crypto_provider.fetch_crypto_intraday('BTC', '60min', start_date, end_date)
        
        # Verify results
        assert not df.empty
        assert len(df) == 2
        assert all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])
        assert df.index[0] == pd.Timestamp('2025-07-27 22:00:00')
        assert df.index[1] == pd.Timestamp('2025-07-27 23:00:00')
        assert df.loc['2025-07-27 23:00:00', 'Close'] == 95200.0
    
    def test_fetch_crypto_intraday_unsupported(self, crypto_provider):
        """Test fetching unsupported crypto"""
        # Set known supported list and prevent API calls
        crypto_provider._supported_cryptos = {'BTC', 'ETH', 'DOGE'}
        crypto_provider._last_crypto_list_fetch = datetime.now()  # Prevent refresh
        
        with patch('requests.Session.get') as mock_get:
            # Try unsupported crypto
            df = crypto_provider.fetch_crypto_intraday('FAKE123', '60min', 
                                                      datetime.now() - timedelta(days=1),
                                                      datetime.now())
            
            # Should return empty DataFrame
            assert df.empty
            mock_get.assert_not_called()  # Should not make API call
    
    @patch('requests.Session.get')
    def test_fetch_crypto_daily_success(self, mock_get, crypto_provider):
        """Test successful crypto daily data fetch"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Meta Data': {
                '1. Information': 'Daily Prices and Volumes for Digital Currency',
                '2. Digital Currency Code': 'ETH',
                '3. Digital Currency Name': 'Ethereum',
                '4. Market Code': 'USD',
                '5. Market Name': 'United States Dollar',
                '6. Last Refreshed': '2025-07-27',
                '7. Time Zone': 'UTC'
            },
            'Time Series (Digital Currency Daily)': {
                '2025-07-27': {
                    '1a. open (USD)': '3800.00',
                    '2a. high (USD)': '3900.00',
                    '3a. low (USD)': '3750.00',
                    '4a. close (USD)': '3850.00',
                    '5. volume': '50000.00',
                    '6. market cap (USD)': '460000000000'
                },
                '2025-07-26': {
                    '1a. open (USD)': '3750.00',
                    '2a. high (USD)': '3820.00',
                    '3a. low (USD)': '3700.00',
                    '4a. close (USD)': '3800.00',
                    '5. volume': '48000.00',
                    '6. market cap (USD)': '456000000000'
                }
            }
        }
        mock_get.return_value = mock_response
        
        # Test fetching data
        start_date = datetime(2025, 7, 26)
        end_date = datetime(2025, 7, 27)
        
        df = crypto_provider.fetch_crypto_daily('ETH', start_date, end_date)
        
        # Verify results
        assert not df.empty
        assert len(df) == 2
        assert all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])
        assert df.index[0] == pd.Timestamp('2025-07-26')
        assert df.index[1] == pd.Timestamp('2025-07-27')
        assert df.loc['2025-07-27', 'Close'] == 3850.0
    
    def test_resample_to_timeframe(self, crypto_provider):
        """Test resampling functionality"""
        # Create hourly data
        dates = pd.date_range('2025-07-27 00:00:00', periods=8, freq='1H')
        data = {
            'Open': [100, 101, 102, 103, 104, 105, 106, 107],
            'High': [101, 102, 103, 104, 105, 106, 107, 108],
            'Low': [99, 100, 101, 102, 103, 104, 105, 106],
            'Close': [101, 102, 103, 104, 105, 106, 107, 108],
            'Volume': [100, 200, 300, 400, 500, 600, 700, 800]
        }
        df = pd.DataFrame(data, index=dates)
        df.attrs['symbol'] = 'BTC'
        df.attrs['interval'] = '1h'
        
        # Resample to 4h
        resampled = crypto_provider.resample_to_timeframe(df, '4h')
        
        # Verify results
        assert len(resampled) == 2  # 8 hours -> 2 4h candles
        assert resampled.index[0] == pd.Timestamp('2025-07-27 00:00:00')
        assert resampled.index[1] == pd.Timestamp('2025-07-27 04:00:00')
        
        # Check aggregation
        assert resampled.iloc[0]['Open'] == 100  # First open
        assert resampled.iloc[0]['High'] == 104  # Max of first 4 hours
        assert resampled.iloc[0]['Low'] == 99   # Min of first 4 hours
        assert resampled.iloc[0]['Close'] == 104  # Last close
        assert resampled.iloc[0]['Volume'] == 1000  # Sum of volumes
    
    @patch('requests.Session.get')
    def test_api_error_handling(self, mock_get, crypto_provider):
        """Test API error handling"""
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Error Message': 'Invalid API call. Please retry or visit the documentation'
        }
        mock_get.return_value = mock_response
        
        # Test fetching data
        df = crypto_provider.fetch_crypto_intraday('BTC', '60min',
                                                  datetime.now() - timedelta(days=1),
                                                  datetime.now())
        
        # Should return empty DataFrame
        assert df.empty
    
    @patch('requests.Session.get')
    def test_rate_limit_handling(self, mock_get, crypto_provider):
        """Test rate limit handling"""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Note': 'Thank you for using Alpha Vantage! Our standard API rate limit is 75 requests per minute.'
        }
        mock_get.return_value = mock_response
        
        # Test fetching data
        df = crypto_provider.fetch_crypto_intraday('ETH', '60min',
                                                  datetime.now() - timedelta(days=1),
                                                  datetime.now())
        
        # Should return empty DataFrame
        assert df.empty
    
    def test_interval_validation(self, crypto_provider):
        """Test interval validation"""
        # Prevent crypto list API calls
        crypto_provider._supported_cryptos = {'BTC', 'ETH', 'DOGE'}
        crypto_provider._last_crypto_list_fetch = datetime.now()
        
        # Test invalid interval
        with patch('requests.Session.get') as mock_get:
            df = crypto_provider.fetch_crypto_intraday('BTC', '2h',  # Invalid
                                                      datetime.now() - timedelta(days=1),
                                                      datetime.now())
            assert df.empty
            mock_get.assert_not_called()  # Should not make API call


def test_integration_with_main_provider():
    """Test integration with main Alpha Vantage provider"""
    with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
        from data.providers.alpha_vantage.provider import AlphaVantageProvider
        
        provider = AlphaVantageProvider()
        crypto_provider = provider.get_crypto_provider()
        
        assert crypto_provider is not None
        assert isinstance(crypto_provider, AlphaVantageCryptoProvider)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])