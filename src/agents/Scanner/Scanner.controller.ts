import { logger } from '@/utils/fns'
import { getAllLatestMarketData } from '@/hyperion/repository'
import {
  ScannerAsset,
  getAvailableTickers,
  analyzeMarketRegime,
  createIndicatorConstructs,
  fetchIndicatorData,
  organizeIndicatorData,
  analyzeAndSaveResults
} from './Scanner.helper'
import { prisma } from '@/app'

export interface ScanAllAssetsResult {
  totalScanned: number
  totalSaved: number
  errors: string[]
  duration: number
}

/**
 * Creates indicator constructs for API requests
 */

/**
 * Scans all available assets across all timeframes and saves results to database
 * This is the main function that runs on the cron schedule
 */
export const scanAllAssets = async (): Promise<ScanAllAssetsResult> => {
  const startTime = Date.now()
  logger.info('🔍 Starting comprehensive asset scan...')

  const result: ScanAllAssetsResult = {
    totalScanned: 0,
    totalSaved: 0,
    errors: [],
    duration: 0
  }

  try {
    // Get list of all available tickers
    const availableTickers = getAvailableTickers()
    logger.info(`📊 Scanning ${availableTickers.length} assets...`)

    // Create indicator constructs for API requests
    const constructGroups = createIndicatorConstructs(availableTickers)
    logger.info(`📦 Created ${constructGroups.length} construct groups`)

    // Fetch indicator data from API
    const assetsData = await fetchIndicatorData(constructGroups, result)
    logger.info(`📊 Fetched data for ${assetsData.length} asset indicators`)

    // Organize raw data into structured format
    const organizedAssets = organizeIndicatorData(assetsData)
    logger.info(`🔧 Organized ${organizedAssets.length} asset-timeframe combinations`)

    // Analyze market regime and save to database
    const savedCount = await analyzeAndSaveResults(organizedAssets)

    // Update result tracking
    result.totalScanned = availableTickers.length
    result.totalSaved = savedCount
    result.duration = Date.now() - startTime

    logger.info(`✅ Asset scan completed: ${result.totalScanned} assets scanned, ${result.totalSaved} results saved in ${result.duration}ms`)

    if (result.errors.length > 0) {
      logger.warn(`⚠️  ${result.errors.length} errors occurred during scan`)
    }

  } catch (error) {
    const errorMsg = `Critical error in scanAllAssets: ${error instanceof Error ? error.message : 'Unknown error'}`
    logger.error(errorMsg)
    result.errors.push(errorMsg)
    result.duration = Date.now() - startTime
  }

  return result
}

/**
 * Gets filtered list of assets by market regime with confidence-based ordering
 */
export const getListAssetsByMarket = async ({
  listOfAssets,
  market,
  filter = {},
  date
}: {
  listOfAssets: string[],
  market: 'trending' | 'ranging',
  filter?: { limit?: number, order?: 'asc' | 'desc' },
  date?: string,
}): Promise<ScannerAsset[]> => {
  // Log function entry
  console.log('🔍 [Scanner Controller] getListAssetsByMarket called');
  console.log(`  📊 Assets: ${listOfAssets.length} | 📈 ${market} | 📅 ${date || 'current'}`);

  const startTime = Date.now();
  
  logger.info(`🔍 Getting ${market} assets for all timeframes (1h, 4h, 1d)`)

  try {
    const results = await prisma.scanner_assets.findMany({
      where: {
        ticker: {
          in: listOfAssets
        },
        market: market,
        created_at: {
          lte: date ? new Date(date) : undefined
        }
      },
      orderBy: { confidence: filter.order || 'desc' },
      take: filter.limit,
    })

    const mappedResults = results.map((result: any) => ({
      symbol: result.ticker,
      timeframe: result.timeframe as '1h' | '4h' | '1d',
      market: result.market as 'trending' | 'ranging',
      confidence: result.confidence // Convert back to decimal
    }));

    const duration = Date.now() - startTime;
    console.log(`✅ [Scanner Controller] Found ${mappedResults.length} results across all timeframes in ${duration}ms`);
    const resultsWithConfOver07 = mappedResults.filter((result: any) => result.confidence > 0.7)
    console.log(`  📊 ${resultsWithConfOver07.length} assets with confidence > 0.7`);

    return mappedResults;

  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`❌ [Scanner Controller] Failed in ${duration}ms:`, error instanceof Error ? error.message : 'Unknown error');
    
    logger.error(`❌ Error retrieving scanner results:`, error)
    return []
  }
}
