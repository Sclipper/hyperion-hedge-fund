from src.graph.state import AgentState, show_agent_reasoning
from src.tools.api import get_financial_metrics, get_market_cap, search_line_items
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
import json
import re
from typing_extensions import Literal
from src.utils.progress import progress
from src.utils.llm import call_llm
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
# Fix import paths - use the correct backend database location
from app.backend.database.connection import SessionLocal
from src.agents.technicals import technical_analyst_agent

class DariusDaleSignal(BaseModel):
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: float
    reasoning: str


def darius_dale_agent(state: AgentState, agent_id: str = "darius_dale_agent"):
    """
    Darius Dale is a macro analyst who uses the ATH and LMN data to make investment decisions.
    Returns a basket of tickers that align with top macro markets.
    """
    data = state["data"]
    tickers = data["tickers"]

    # End date defaults to today
    end_date = data["end_date"] if data["end_date"] else datetime.now().strftime("%Y-%m-%d")

    dale_analysis = {}
    
    progress.update_status(agent_id, None, "Finding latest macro data")
    macro_data = find_latest_macro_data(end_date)
    
    if macro_data['has_data']:
        print(f"✅ Found macro research: {macro_data['research_data'][0]['title']}")
        print(f"📊 Extracted top markets: {macro_data['top_markets']}")
        
        # Get tickers that fit with the top markets
        progress.update_status(agent_id, None, "Finding tickers that fit with the top markets")
        macro_tickers = get_tickers_that_fit_with_markets(macro_data['top_markets'])

        # Find trending tickers
        progress.update_status(agent_id, None, "Finding trending tickers")
        # TODO: Add end date to this query
        trending_tickers = find_trending_assets(macro_tickers, end_date)
        # reduce the tickers to the top 10
        print(f"🎯 Trending tickers: {trending_tickers}")
        trending_tickers = trending_tickers[:3]
        
        # Add the trending tickers to the state
        state["data"]["tickers"] = trending_tickers

        # Analyze each trending ticker individually
        for ticker in trending_tickers:
            progress.update_status(agent_id, ticker, f"Analyzing {ticker}")
            print(f"🎯 Analyzing {ticker}")
            
            # Get financial data for this ticker
            progress.update_status(agent_id, ticker, "Fetching financial metrics")
            metrics = get_financial_metrics(ticker, end_date, period="quarterly", limit=8)
            
            progress.update_status(agent_id, ticker, "Gathering financial line items")
            financial_line_items = search_line_items(
                ticker,
                [
                    "revenue",
                    "net_income", 
                    "operating_income",
                    "operating_margin",
                    "free_cash_flow",
                    "cash_and_equivalents",
                    "total_debt",
                    "shareholders_equity"
                ],
                end_date,
                period="quarterly",
                limit=8
            )
            
            progress.update_status(agent_id, ticker, "Getting market cap")
            market_cap = get_market_cap(ticker, end_date)
            
            # Perform Darius Dale-style analysis
            progress.update_status(agent_id, ticker, "Analyzing macro alignment")
            macro_alignment = analyze_macro_alignment(ticker, macro_data, financial_line_items)
            
            progress.update_status(agent_id, ticker, "Analyzing sector positioning")
            sector_analysis = analyze_sector_positioning(financial_line_items, metrics)
            
            progress.update_status(agent_id, ticker, "Calculating risk-adjusted potential")
            risk_analysis = calculate_risk_adjusted_potential(financial_line_items, market_cap)
            
            # Combine scores with Darius Dale's weighting (macro-focused)
            total_score = (
                macro_alignment["score"] * 0.4 +    # Heavy weight on macro alignment
                sector_analysis["score"] * 0.35 +   # Sector rotation importance
                risk_analysis["score"] * 0.25       # Risk management
            )
            
            # Generate signal based on score
            if total_score >= 7.0:
                signal = "bullish"
            elif total_score <= 4.0:
                signal = "bearish"
            else:
                signal = "neutral"
            
            analysis_data = {
                "signal": signal,
                "score": total_score,
                "macro_alignment": macro_alignment,
                "sector_analysis": sector_analysis,
                "risk_analysis": risk_analysis,
                "top_markets": macro_data['top_markets'],
                "ticker_markets": [market for market, market_tickers in assetBuckets.items() if ticker in market_tickers]
            }
            
            progress.update_status(agent_id, ticker, "Generating Darius Dale analysis")
            dale_output = generate_darius_dale_output(
                ticker=ticker,
                analysis_data=analysis_data,
                state=state,
                agent_id=agent_id,
            )
            
            dale_analysis[ticker] = {
                "signal": dale_output.signal,
                "confidence": dale_output.confidence,
                "reasoning": dale_output.reasoning
            }
            
            progress.update_status(agent_id, ticker, "Done", analysis=dale_output.reasoning)

    else:
        print("❌ No macro research data available")
        # If no macro data, still return neutral signal for original tickers
        for ticker in tickers:
            dale_analysis[ticker] = {
                "signal": "neutral",
                "confidence": 0.0,
                "reasoning": "No macro research data available to generate ticker recommendations."
            }
    
    # Wrap results in a single message for the chain
    message = HumanMessage(
        content=json.dumps(dale_analysis),
        name=agent_id
    )
    
    # Show reasoning if requested
    if state.get("metadata", {}).get("show_reasoning", False):
        show_agent_reasoning(dale_analysis, "Darius Dale Agent")

    progress.update_status(agent_id, None, "Done")
    
    # Add signals to the overall state
    state["data"]["analyst_signals"][agent_id] = dale_analysis
    print(f"🎯 Darius Dale Agent analyzed {len(dale_analysis)} tickers")
    
    return {
        "messages": [message],
        "data": state["data"]
    }


def find_trending_assets(tickers: list[str], end_date: str) -> list[str]:
    """
    Find trending assets from the tickers.
    """
    db = SessionLocal()
    try:
        print(f"🎯 Searching for trending assets in {len(tickers)} tickers")
        result = db.execute(text("""
            SELECT * FROM scanner_historical
            WHERE ticker = ANY(:tickers)
            AND confidence > 0.7
            AND market = 'trending'
            AND created_at <= :end_date
        """), {"tickers": tickers, "end_date": end_date})
        
        trending_tickers = [dict(row._mapping) for row in result]
        trending_ticker_symbols = [ticker['ticker'] for ticker in trending_tickers]
        print(f"🎯 Found {len(trending_ticker_symbols)} trending tickers")
        return trending_ticker_symbols
    except Exception as e:
        print(f"Warning: Could not fetch trending assets: {e}")
        print("Returning empty list - continuing without trending filter")
        return []
    finally:
        db.close()

def extract_top_markets(text: str) -> list[str]:
    """
    Extract top markets from macro research text.
    Looks for patterns like "considerations ... are: market1 > analysis, market2 > analysis"
    """
    if not text:
        return []
    
    # 1. Normalize whitespace (collapse newlines/tabs into single spaces)
    clean = re.sub(r'\s+', ' ', text).strip()
    
    # 2. Find the clause after "considerations ... are:"
    pattern = r'considerations.*?are:(.*?)(?:\.|$)'
    match = re.search(pattern, clean, re.IGNORECASE)
    if not match:
        return []

    # 3. Grab that body, split on commas (and optional leading "and ")
    body = match.group(1).strip()
    parts = re.split(r',\s*(?:and\s*)?', body, flags=re.IGNORECASE)
    
    # 4. For each part containing ">", take what's before the first ">"
    winners = []
    for part in parts:
        idx = part.find('>')
        if idx == -1:
            continue
        # slice left of '>', trim punctuation
        winner = part[:idx].rstrip('.,').strip()
        if winner:
            winners.append(winner)
    
    return winners


def find_latest_macro_data(end_date: str):
    """
    Get latest macro research data from database and extract top markets.
    Creates its own database session (recommended pattern).
    Returns dict with original data and extracted markets.
    """
    # Create a new database session
    db = SessionLocal()
    try:
        # Execute raw SQL query with proper parameter binding
        result = db.execute(text("""
            SELECT title, plain_text 
            FROM research 
            WHERE created_at <= :end_date
            ORDER BY created_at DESC 
            LIMIT 1
        """), {"end_date": end_date})
        # Convert to list of dictionaries
        research_data = [dict(row._mapping) for row in result]
        
        # Extract top markets from the latest research
        if research_data and research_data[0].get('plain_text'):
            top_markets = extract_top_markets(research_data[0]['plain_text'])
            return {
                'research_data': research_data,
                'top_markets': top_markets,
                'has_data': True
            }
        else:
            return {
                'research_data': [],
                'top_markets': [],
                'has_data': False
            }
            
    except Exception as e:
        # Handle case where research table doesn't exist or other database errors
        print(f"Warning: Could not fetch macro data from research table: {e}")
        print("Returning empty macro data - agent will continue without research context")
        return {
            'research_data': [],
            'top_markets': [],
            'has_data': False
        }
    finally:
        # Always close the session
        db.close()


def generate_darius_dale_output(
    ticker: str,
    analysis_data: dict[str, any],
    state: AgentState,
    agent_id: str = "darius_dale_agent",
) -> DariusDaleSignal:
    """
    Generates investment decisions in the style of Darius Dale.
    """
    template = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are a Darius Dale AI agent, making investment decisions using his macro-economic approach:

            1. Focus on macro-economic context and market cycles.
            2. Emphasize sector rotation and timing strategies.
            3. Prioritize risk-adjusted returns over absolute returns.
            4. Consider Federal Reserve policy and economic indicators.
            5. Use technical analysis combined with fundamental analysis.
            6. Focus on position sizing and risk management.
            7. Look for asymmetric risk/reward opportunities.
            8. Consider market sentiment and momentum.
            9. Emphasize timing of entry and exit points.
            10. Integrate top-down macro view with bottom-up stock analysis.

            Rules:
            - Always consider the broader macro environment and where we are in the cycle.
            - Focus on sectors and stocks positioned for the next phase of the economic cycle.
            - Emphasize risk management and position sizing in your analysis.
            - Consider technical momentum alongside fundamental metrics.
            - Look for companies that can outperform in different market regimes.
            - Pay attention to earnings revisions and guidance trends.
            - Consider Federal Reserve policy impact on the sector/stock.
            - Provide a tactical recommendation (bullish, bearish, or neutral) with clear timing context.
            
            When providing your reasoning, be thorough and specific by:
            1. Starting with the macro-economic context and cycle positioning
            2. Explaining how this stock/sector fits into current market rotation themes
            3. Discussing the risk/reward profile and position sizing considerations
            4. Providing specific technical and fundamental momentum indicators
            5. Addressing potential risks and how they could impact the investment
            6. Using Darius Dale's analytical, macro-focused communication style
            
            For example, if bullish: "Given the current late-cycle environment and Fed policy stance, this name is positioned for the next rotation into..."
            For example, if bearish: "The macro setup suggests headwinds for this sector, with deteriorating fundamentals confirming the top-down thesis..."
            """
        ),
        (
            "human",
            """Based on the following analysis, create a Darius Dale-style investment signal.

            Analysis Data for {ticker}:
            {analysis_data}

            Return the trading signal in this JSON format:
            {{
              "signal": "bullish/bearish/neutral",
              "confidence": float (0-100),
              "reasoning": "string"
            }}
            """
        )
    ])

    prompt = template.invoke({
        "analysis_data": json.dumps(analysis_data, indent=2),
        "ticker": ticker
    })

    def create_default_darius_dale_signal():
        return DariusDaleSignal(
            signal="neutral",
            confidence=0.0,
            reasoning="Error in analysis, defaulting to neutral"
        )

    return call_llm(
        prompt=prompt,
        state=state,
        pydantic_model=DariusDaleSignal, 
        agent_name=agent_id, 
        default_factory=create_default_darius_dale_signal,
    )

# source: https://ark-invest.com

def get_tickers_that_fit_with_markets(markets: list[str]) -> list[str]:
    """
    Get tickers that fit with the given markets.
    """
    # For each market, find the tickers that fit with the market and return them
    tickers = []
    for market in markets:
        tickers.extend(assetBuckets[market])
    return tickers



# TODO: Run backtest 4-5 years behind with MAGS
assetBuckets = {
   'Risk Assets': [
    'RKLB'
    #   'MSFT', 'NVDA', 'AAPL', 'AMZN', 'META', 'AVGO', 'GOOG', 'GOOGL', 'BRK.B', 'TSLA', 'JPM', 'WMT', 'LLY', 'ORCL', 'NFLX', 'MA', 'XOM', 'COST', 'PG', 'JNJ', 'HD', 'BAC', 'PLTR', 'ABBV', 'KO', 'PM', 'UNH', 'IBM', 'CSCO', 'CVX', 'GE', 'TMUS', 'CRM', 'WFC', 'ABT', 'LIN', 'MS', 'DIS', 'INTU', 'AXP', 'MCD', 'AMD', 'NOW', 'MRK', 'T', 'GS', 'RTX', 'ACN', 'ISRG', 'TXN', 'PEP', 'VZ', 'UBER', 'BKNG', 'CAT', 'QCOM', 'SCHW', 'ADBE', 'AMGN', 'SPGI', 'PGR', 'BLK', 'BSX', 'BA', 'TMO', 'NEE', 'C', 'HON', 'SYK', 'DE', 'DHR', 'AMAT', 'TJX', 'MU', 'PFE', 'GILD', 'GEV', 'PANW', 'UNP', 'ETN', 'CMCSA', 'COF', 'ADP', 'CRWD', 'COP', 'LOW', 'LRCX', 'KLAC', 'VRTX', 'ADI', 'ANET', 'CB', 'APH', 'MDT', 'LMT', 'KKR', 'MMC', 'BX', 'SBUX', 'ICE', 'AMT', 'MO', 'WELL', 'CME', 'SO', 'PLD', 'CEG', 'BMY', 'WM', 'INTC', 'TT', 'DASH', 'MCK', 'HCA', 'FI', 'DUK', 'CTAS', 'NKE', 'EQIX', 'MDLZ', 'ELV', 'MCO', 'CVS', 'UPS', 'CI', 'PH', 'SHW', 'ABNB', 'AJG', 'CDNS', 'TDG', 'DELL', 'RSG', 'FTNT', 'MMM', 'APO', 'AON', 'ORLY', 'COIN', 'GD', 'ECL', 'SNPS', 'RCL', 'EMR', 'WMB', 'CL', 'NOC', 'ITW', 'MAR', 'CMG', 'PNC', 'ZTS', 'HWM', 'JCI', 'EOG', 'MSI', 'USB', 'PYPL', 'BK', 'NEM', 'ADSK', 'WDAY', 'MNST', 'VST', 'APD', 'KMI', 'CSX', 'AZO', 'TRV', 'AXON', 'CARR', 'ROP', 'DLR', 'FCX', 'HLT', 'COR', 'NSC', 'AFL', 'REGN', 'PAYX', 'AEP', 'FDX', 'NXPI', 'PWR', 'MET', 'CHTR', 'TFC', 'O', 'ALL', 'MPC', 'SPG', 'PSA', 'PSX', 'OKE', 'CTVA', 'GWW', 'NDAQ', 'TEL', 'AIG', 'SRE', 'SLB', 'BDX', 'AMP', 'PCAR', 'FAST', 'LHX', 'CPRT', 'GM', 'D', 'URI', 'KDP', 'OXY', 'HES', 'VLO', 'KR', 'TTWO', 'FANG', 'EW', 'CMI', 'CCI', 'GLW', 'TGT', 'FICO', 'VRSK', 'EXC', 'KMB', 'FIS', 'MSCI', 'ROST', 'IDXX', 'F', 'AME', 'KVUE', 'PEG', 'CBRE', 'CAH', 'CTSH', 'BKR', 'YUM', 'XEL', 'GRMN', 'EA', 'OTIS', 'DHI', 'PRU', 'RMD', 'TRGP', 'MCHP', 'ED', 'ROK', 'ETR', 'SYY', 'EBAY', 'BRO', 'EQT', 'HIG', 'HSY', 'WAB', 'LYV', 'VICI', 'VMC', 'ACGL', 'CSGP', 'MPWR', 'WEC', 'ODFL', 'GEHC', 'A', 'IR', 'MLM', 'CCL', 'DXCM', 'EFX', 'EXR', 'DAL', 'PCG', 'IT', 'XYL', 'KHC', 'IRM', 'RJF', 'NRG', 'ANSS', 'LVS', 'WTW', 'AVB', 'HUM', 'MTB', 'NUE', 'GIS', 'EXE', 'STZ', 'STT', 'VTR', 'DD', 'BR', 'STX', 'WRB', 'TSCO', 'KEYS', 'AWK', 'CNC', 'LULU', 'K', 'DTE', 'LEN', 'ROL', 'EL', 'IQV', 'SMCI', 'VRSN', 'EQR', 'WBD', 'DRI', 'ADM', 'FITB', 'AEE', 'GDDY', 'PPL', 'TPL', 'DG', 'PPG', 'SBAC', 'TYL', 'IP', 'UAL', 'ATO', 'DOV', 'VLTO', 'CBOE', 'MTD', 'FTV', 'CHD', 'SYF', 'HPE', 'STE', 'CNP', 'FE', 'ES', 'HBAN', 'TDY', 'CINF', 'HPQ', 'CDW', 'CPAY', 'SW', 'JBL', 'LH', 'DVN', 'ON', 'NTRS', 'HUBB', 'ULTA', 'PODD', 'AMCR', 'INVH', 'EXPE', 'WDC', 'NTAP', 'CMS', 'CTRA', 'NVR', 'DLTR', 'TROW', 'WAT', 'DOW', 'DGX', 'PTC', 'PHM', 'RF', 'WSM', 'MKC', 'LII', 'EIX', 'TSN', 'STLD', 'IFF', 'HAL', 'LDOS', 'LYB', 'WY', 'GPN', 'BIIB', 'L', 'NI', 'ESS', 'ERIE', 'GEN', 'CFG', 'ZBH', 'LUV', 'KEY', 'TPR', 'MAA', 'TRMB', 'PFG', 'PKG', 'HRL', 'GPC', 'FFIV', 'CF', 'RL', 'FDS', 'SNA', 'MOH', 'PNR', 'WST', 'BALL', 'EXPD', 'LNT', 'FSLR', 'EVRG', 'J', 'DPZ', 'BAX', 'DECK', 'CLX', 'ZBRA', 'APTV', 'TKO', 'BBY', 'HOLX', 'KIM', 'EG', 'COO', 'TER', 'TXT', 'JBHT', 'UDR', 'AVY', 'OMC', 'IEX', 'INCY', 'JKHY', 'ALGN', 'PAYC', 'MAS', 'REG', 'SOLV', 'CPT', 'FOXA', 'ARE', 'BF.B', 'NDSN', 'JNPR', 'BEN', 'DOC', 'BLDR', 'ALLE', 'MOS', 'BG', 'BXP', 'FOX', 'AKAM', 'RVTY', 'CHRW', 'UHS', 'HST', 'SWKS', 'POOL', 'PNW', 'VTRS', 'CAG', 'DVA', 'SJM', 'SWK', 'AIZ', 'GL', 'TAP', 'WBA', 'MRNA', 'KMX', 'HAS', 'LKQ', 'CPB', 'EPAM', 'MGM', 'HII', 'NWS', 'WYNN', 'DAY', 'AOS', 'HSIC', 'EMN', 'IPG', 'MKTX', 'FRT', 'NCLH', 'PARA', 'NWSA', 'TECH', 'LW', 'AES', 'MTCH', 'GNRC', 'APA', 'CRL', 'ALB', 'IVZ', 'MHK', 'CZR', 'ENPH', 'BTC', 'ETH', 'USDT', 'XRP', 'BNB', 'SOL', 'USDC', 'TRX', 'DOGE', 'ADA', 'HYPE', 'SUI', 'BCH', 'LINK', 'LEO', 'XLM', 'AVAX', 'TON', 'SHIB', 'LTC', 'HBAR', 'XMR', 'DOT', 'USDe', 'DAI', 'BGB', 'UNI', 'PEPE', 'PI', 'AAVE', 'OKB', 'TAO', 'APT', 'CRO', 'ICP', 'NEAR', 'ETC', 'ONDO', 'USD1', 'MNT', 'POL', 'GT', 'KAS', 'TRUMP', 'VET', 'SKY', 'ENA', 'RENDER', 'FET', 'FIL'
   ],
   'Defensive Assets': ['AGG', 'BND', 'XLP', 'XLU'],
   'High Beta': ['SPHB', 'HIBL', 'SSO',
      'BTC', 'ETH', 'USDT', 'XRP', 'BNB', 'SOL', 'USDC', 'TRX', 'DOGE', 'ADA', 'HYPE', 'SUI', 'BCH', 'LINK', 'LEO', 'XLM', 'AVAX', 'TON', 'SHIB', 'LTC', 'HBAR', 'XMR', 'DOT', 'USDe', 'DAI', 'BGB', 'UNI', 'PEPE', 'PI', 'AAVE', 'OKB', 'TAO', 'APT', 'CRO', 'ICP', 'NEAR', 'ETC', 'ONDO', 'USD1', 'MNT', 'POL', 'GT', 'KAS', 'TRUMP', 'VET', 'SKY', 'ENA', 'RENDER', 'FET', 'FIL'

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


def analyze_macro_alignment(ticker: str, macro_data: dict, financial_line_items: list) -> dict:
    """
    Analyze how well the ticker aligns with current macro trends.
    Dale focuses on macro-economic positioning and cycle timing.
    """
    score = 0
    details = []
    
    # 1. Check if ticker is in the recommended markets from macro research
    if macro_data['has_data'] and macro_data['top_markets']:
        ticker_markets = []
        for market, tickers in assetBuckets.items():
            if ticker in tickers:
                ticker_markets.append(market)
        
        # Score based on alignment with top markets
        aligned_markets = set(ticker_markets) & set(macro_data['top_markets'])
        if aligned_markets:
            score += 5
            details.append(f"Strong macro alignment: {ticker} in recommended markets {list(aligned_markets)}")
        else:
            details.append(f"No macro alignment: {ticker} not in top markets {macro_data['top_markets']}")
    else:
        details.append("No macro research data available for alignment analysis")
    
    # 2. Analyze recent revenue trends (macro sensitivity)
    if financial_line_items:
        revenues = [item.revenue for item in financial_line_items[:4] 
                   if hasattr(item, 'revenue') and item.revenue is not None]
        
        if len(revenues) >= 3:
            recent_growth = (revenues[0] / revenues[1] - 1) if revenues[1] != 0 else 0
            if recent_growth > 0.05:  # >5% recent growth
                score += 3
                details.append(f"Positive momentum: {recent_growth:.1%} recent revenue growth")
            elif recent_growth > 0:
                score += 1
                details.append(f"Modest momentum: {recent_growth:.1%} recent revenue growth")
            else:
                details.append(f"Negative momentum: {recent_growth:.1%} recent revenue decline")
    
    # 3. Check financial resilience (important for macro investing)
    if financial_line_items:
        cash_values = [item.cash_and_equivalents for item in financial_line_items[:1]
                      if hasattr(item, 'cash_and_equivalents') and item.cash_and_equivalents is not None]
        debt_values = [item.total_debt for item in financial_line_items[:1]
                      if hasattr(item, 'total_debt') and item.total_debt is not None]
        
        if cash_values and debt_values:
            net_cash = cash_values[0] - debt_values[0]
            if net_cash > 0:
                score += 2
                details.append("Strong balance sheet: Net cash positive")
            else:
                details.append("Leveraged balance sheet: Net debt position")
    
    final_score = min(10, score)
    
    return {
        "score": final_score,
        "details": "; ".join(details)
    }


def analyze_sector_positioning(financial_line_items: list, metrics: list) -> dict:
    """
    Analyze sector rotation and positioning opportunities.
    Dale looks for sectors positioned for the next market phase.
    """
    score = 0
    details = []
    
    if not financial_line_items:
        return {
            "score": 0,
            "details": "Insufficient data for sector analysis"
        }
    
    # 1. Operating leverage analysis (important for sector rotation)
    if len(financial_line_items) >= 4:
        op_margins = [item.operating_margin for item in financial_line_items
                     if hasattr(item, 'operating_margin') and item.operating_margin is not None]
        
        if len(op_margins) >= 3:
            margin_trend = op_margins[0] - op_margins[2]  # Recent vs 2 quarters ago
            if margin_trend > 0.02:  # Improving margins
                score += 3
                details.append("Strong operational leverage: Margins expanding")
            elif margin_trend > 0:
                score += 1
                details.append("Modest operational leverage: Margins stable to improving")
            else:
                details.append("Margin pressure: Operating leverage declining")
    
    # 2. Growth consistency (sector leadership indicator)
    revenues = [item.revenue for item in financial_line_items
               if hasattr(item, 'revenue') and item.revenue is not None]
    
    if len(revenues) >= 4:
        growth_rates = []
        for i in range(len(revenues)-1):
            if revenues[i+1] != 0:
                growth_rates.append(revenues[i] / revenues[i+1] - 1)
        
        if growth_rates:
            positive_quarters = sum(1 for g in growth_rates if g > 0)
            if positive_quarters >= len(growth_rates) * 0.75:
                score += 3
                details.append("Consistent growth leader in sector")
            elif positive_quarters >= len(growth_rates) * 0.5:
                score += 2
                details.append("Generally growing within sector")
            else:
                details.append("Inconsistent sector performance")
    
    # 3. Market share dynamics (free cash flow growth vs revenue growth)
    if financial_line_items:
        fcf_values = [item.free_cash_flow for item in financial_line_items[:3]
                     if hasattr(item, 'free_cash_flow') and item.free_cash_flow is not None]
        
        if len(fcf_values) >= 2 and len(revenues) >= 2:
            fcf_growth = (fcf_values[0] / fcf_values[1] - 1) if fcf_values[1] != 0 else 0
            rev_growth = (revenues[0] / revenues[1] - 1) if revenues[1] != 0 else 0
            
            if fcf_growth > rev_growth and fcf_growth > 0:
                score += 2
                details.append("Improving efficiency: FCF growing faster than revenue")
            elif fcf_growth > 0:
                score += 1
                details.append("Positive cash generation trend")
    
    final_score = min(10, score)
    
    return {
        "score": final_score,
        "details": "; ".join(details)
    }


def calculate_risk_adjusted_potential(financial_line_items: list, market_cap: float) -> dict:
    """
    Calculate risk-adjusted return potential using Dale's risk management approach.
    Focus on downside protection and asymmetric risk/reward.
    """
    score = 0
    details = []
    
    if not financial_line_items or market_cap is None:
        return {
            "score": 0,
            "details": "Insufficient data for risk assessment"
        }
    
    # 1. Balance sheet strength (downside protection)
    debt_values = [item.total_debt for item in financial_line_items[:1]
                  if hasattr(item, 'total_debt') and item.total_debt is not None]
    equity_values = [item.shareholders_equity for item in financial_line_items[:1]
                    if hasattr(item, 'shareholders_equity') and item.shareholders_equity is not None]
    
    if debt_values and equity_values and equity_values[0] > 0:
        debt_to_equity = debt_values[0] / equity_values[0]
        if debt_to_equity < 0.3:
            score += 3
            details.append(f"Low leverage risk: D/E ratio {debt_to_equity:.2f}")
        elif debt_to_equity < 0.6:
            score += 2
            details.append(f"Moderate leverage: D/E ratio {debt_to_equity:.2f}")
        elif debt_to_equity < 1.0:
            score += 1
            details.append(f"Higher leverage: D/E ratio {debt_to_equity:.2f}")
        else:
            details.append(f"High leverage risk: D/E ratio {debt_to_equity:.2f}")
    
    # 2. Earnings quality (cash conversion)
    if financial_line_items:
        fcf_values = [item.free_cash_flow for item in financial_line_items[:1]
                     if hasattr(item, 'free_cash_flow') and item.free_cash_flow is not None]
        ni_values = [item.net_income for item in financial_line_items[:1]
                    if hasattr(item, 'net_income') and item.net_income is not None]
        
        if fcf_values and ni_values and ni_values[0] > 0:
            cash_conversion = fcf_values[0] / ni_values[0]
            if cash_conversion > 1.1:
                score += 3
                details.append(f"High earnings quality: FCF/NI ratio {cash_conversion:.2f}")
            elif cash_conversion > 0.8:
                score += 2
                details.append(f"Good earnings quality: FCF/NI ratio {cash_conversion:.2f}")
            else:
                details.append(f"Lower earnings quality: FCF/NI ratio {cash_conversion:.2f}")
    
    # 3. Liquidity and financial flexibility
    cash_values = [item.cash_and_equivalents for item in financial_line_items[:1]
                  if hasattr(item, 'cash_and_equivalents') and item.cash_and_equivalents is not None]
    revenue_values = [item.revenue for item in financial_line_items[:1]
                     if hasattr(item, 'revenue') and item.revenue is not None]
    
    if cash_values and revenue_values and revenue_values[0] > 0:
        cash_runway = cash_values[0] / (revenue_values[0] / 4)  # Quarters of cash
        if cash_runway > 4:  # >1 year of cash
            score += 2
            details.append(f"Strong liquidity: {cash_runway:.1f} quarters of cash")
        elif cash_runway > 2:
            score += 1
            details.append(f"Adequate liquidity: {cash_runway:.1f} quarters of cash")
        else:
            details.append(f"Limited liquidity: {cash_runway:.1f} quarters of cash")
    
    # 4. Volatility assessment (earnings stability)
    if len(financial_line_items) >= 4:
        quarterly_incomes = [item.net_income for item in financial_line_items
                           if hasattr(item, 'net_income') and item.net_income is not None]
        
        if len(quarterly_incomes) >= 4:
            positive_quarters = sum(1 for income in quarterly_incomes if income > 0)
            if positive_quarters == len(quarterly_incomes):
                score += 2
                details.append("Low earnings volatility: Consistent profitability")
            elif positive_quarters >= len(quarterly_incomes) * 0.75:
                score += 1
                details.append("Moderate earnings stability")
            else:
                details.append("High earnings volatility")
    
    final_score = min(10, score)
    
    return {
        "score": final_score,
        "details": "; ".join(details)
    }
