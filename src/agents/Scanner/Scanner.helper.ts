import { logger } from '@/utils/fns'
import axios from 'axios'
import { allCryptos } from '../TA/TA.model'
import { assetBuckets } from '../Darius/Darius.model'
import { ScanAllAssetsResult } from './Scanner.controller'
import { prisma } from '@/app'


export interface ScannerAsset {
  symbol: string
  timeframe: '1h' | '4h' | '1d'
  market: 'trending' | 'ranging'
  confidence: number
}

export interface TechnicalIndicators {
  emaFast: number
  emaSlow: number
  rsi: number
  adx: number
  sma20: number
  sma50: number
  volatility: number
}

/**
 * Determines if an asset is in trending or ranging market based on TA indicators
*/
export const analyzeMarketRegime = (indicators: Array<{ indicator: string, value: number }>): { market: 'trending' | 'ranging', confidence: number } => {
  // Extract values from indicator array
  const getValue = (name: string) => indicators.find(i => i.indicator === name)?.value || 0

  const emaFast = getValue('emaFast')
  const emaSlow = getValue('emaSlow')
  const adx = getValue('adx')
  const sma = getValue('sma')
  const volatility = getValue('volatility')
  const price = getValue('price')

  // Trending indicators
  const trendStrength = Math.abs(emaFast - emaSlow) / emaSlow * 100
  const adxTrending = adx > 25 // ADX above 25 indicates trending
  const maCrossover = emaFast > emaSlow // EMA crossover indicates uptrend
  const priceAboveMAs = price > emaFast && price > sma // Price above moving averages

  // Ranging indicators  
  const lowVolatility = volatility < 0.02 // Low volatility suggests ranging
  const lowAdx = adx < 20 // Low ADX suggests ranging
  const tightMAs = Math.abs(emaFast - sma) / sma < 0.03 // Moving averages close together

  // Calculate trending score (0-1)
  let trendingScore = 0
  if (adxTrending) trendingScore += 0.4
  if (trendStrength > 2) trendingScore += 0.3
  if (maCrossover && priceAboveMAs) trendingScore += 0.2
  if (volatility > 0.03) trendingScore += 0.1

  // Calculate ranging score (0-1)
  let rangingScore = 0
  if (lowAdx) rangingScore += 0.4
  if (lowVolatility) rangingScore += 0.3
  if (tightMAs) rangingScore += 0.3

  // Determine market regime
  if (trendingScore > rangingScore) {
    return {
      market: 'trending',
      confidence: Math.min(trendingScore, 1.0)
    }
  } else {
    return {
      market: 'ranging',
      confidence: Math.min(rangingScore, 1.0)
    }
  }
}

export const getAvailableTickers = (): string[] => {
  const tickers = Object.values(assetBuckets).flat()
  const uniqueTickers = [...new Set(tickers)]
    // .filter((ticker: string) => ticker !== 'BTC' && ticker !== 'ETH' && ticker !== 'USDT' && ticker !== 'XRP' && ticker !== 'BNB' && ticker !== 'SOL' && ticker !== 'USDC' && ticker !== 'TRX' && ticker !== 'DOGE' && ticker !== 'ADA' && ticker !== 'HYPE' && ticker !== 'SUI' && ticker !== 'BCH' && ticker !== 'LINK' && ticker !== 'LEO' && ticker !== 'XLM' && ticker !== 'AVAX' && ticker !== 'TON' && ticker !== 'SHIB' && ticker !== 'LTC' && ticker !== 'HBAR' && ticker !== 'XMR' && ticker !== 'DOT' && ticker !== 'USDe' && ticker !== 'DAI' && ticker !== 'BGB' && ticker !== 'UNI' && ticker !== 'PEPE' && ticker !== 'PI' && ticker !== 'AAVE' && ticker !== 'OKB' && ticker !== 'TAO' && ticker !== 'APT' && ticker !== 'CRO' && ticker !== 'ICP' && ticker !== 'NEAR' && ticker !== 'ETC' && ticker !== 'ONDO' && ticker !== 'USD1' && ticker !== 'MNT' && ticker !== 'POL' && ticker !== 'GT' && ticker !== 'KAS' && ticker !== 'TRUMP' && ticker !== 'VET' && ticker !== 'SKY' && ticker !== 'ENA' && ticker !== 'RENDER' && ticker !== 'FET' && ticker !== 'FIL')
  return uniqueTickers
}


export const createIndicatorConstructs = (tickers: string[]): any[] => {
  const indicators = [
    { indicator: 'ema', period: 20 },
    { indicator: 'ema', period: 100 },
    { indicator: 'adx', period: 14 },
    { indicator: 'sma', period: 50 },
    { indicator: 'volatility', period: 14 },
    { indicator: 'price', period: 1 }
  ]

  // Create constructs with each ticker appearing 3 times for different intervals
  const construct = tickers.flatMap((ticker: string) => {
    const isCrypto = allCryptos.includes(ticker)
    const intervals = ['1h', '4h', '1d']

    return intervals.map(interval => ({
      type: isCrypto ? 'crypto' : 'stocks',
      symbol: isCrypto ? `${ticker}/USDT` : ticker,
      interval: interval,
      indicators: indicators
    }))
  })

  // Split construct into groups of 3
  return construct.reduce((acc: any, item: any, index: number) => {
    const group = Math.floor(index / 3)
    acc[group] = acc[group] || []
    acc[group].push(item)
    return acc
  }, [])
}

/**
 * Fetches indicator data from API with rate limiting
 */
export const fetchIndicatorData = async (constructGroups: any[], result: ScanAllAssetsResult): Promise<any[]> => {
  const assets = []

  for (let i = 0; i < constructGroups.length; i++) {
    const group = constructGroups[i]

    if (i > 0) {
      await new Promise(resolve => setTimeout(resolve, 2000))
    }

    try {
      const data = await axios.post('https://api.taapi.io/bulk', {
        secret: process.env.TAAPI_KEY,
        construct: group,
      })
      assets.push(data.data)
      logger.info(`✅ Processed group ${i + 1}/${constructGroups.length}`)
    } catch (error) {
      logger.error(`❌ Error processing group ${i + 1}:`, error)
      result.errors.push(`Group ${i + 1} failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  return assets.map((asset: any) => asset.data).flat()
}

/**
 * Organizes raw API data into structured format
 */
export const organizeIndicatorData = (assetsData: any[]): any[] => {
  return assetsData.reduce((acc: any[], asset: any) => {
    const ticker = asset.id.split('_')[1]
    const timeframe = asset.id.split('_')[2]
    const speed = asset.id.split('_')[4]
    let indicator = asset.indicator
    const value = asset.result.value

    if (indicator === 'ema') {
      indicator = speed === '100' ? 'emaSlow' : 'emaFast'
    }

    const existingAsset = acc.find((a: any) => a.ticker === ticker && a.timeframe === timeframe)
    if (existingAsset) {
      existingAsset.indicators.push({ indicator, value })
    } else {
      acc.push({
        ticker,
        timeframe,
        indicators: [{ indicator, value }]
      })
    }
    return acc
  }, [])
}

/**
 * Analyzes market regime and saves results to database
 */
export const analyzeAndSaveResults = async (organizedAssets: any[]): Promise<number> => {
  const assetsWithMarket = organizedAssets.map((asset: any) => {
    const analysis = analyzeMarketRegime(asset.indicators)
    return {
      ...asset,
      market: analysis.market,
      confidence: analysis.confidence
    }
  })

  logger.info(`🧠 Analyzed ${assetsWithMarket.length} asset-timeframe combinations`)

  await prisma.scanner_assets.createMany({
    data: assetsWithMarket.map((asset: any) => ({
      ticker: asset.ticker,
      timeframe: asset.timeframe,
      market: asset.market,
      confidence: asset.confidence,
    }))
  })

  return assetsWithMarket.length
}
