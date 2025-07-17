import { hyperionAgentsMCP } from '@/app'
import { z } from 'zod'
import { getListAssetsByMarket } from './Scanner.controller'
import { ScannerAsset } from './Scanner.helper'

export type ListOfAssets = {
	symbol: string,
	timeframe: '1h' | '4h' | '1d',
	market: 'trending' | 'ranging'
	confidence: number
}


hyperionAgentsMCP.tool(
	'get_list_assets_by_market',
	'Get a list of assets by market regime (trending/ranging) with confidence scores',
	{
		listOfAssets: z.array(z.string()).describe('A list of assets to scan "AAPL", "TSLA", "NVDA", etc... Leave empty to scan all available assets'),
		timeframe: z.enum(['1h', '4h', '1d']).describe('The timeframe to scan the assets'),
		market: z.enum(['trending', 'ranging']).describe('The market regime to filter assets by'),
		filter: z.object({
			limit: z.number().optional().describe('Maximum number of results to return'),
			order: z.enum(['asc', 'desc']).optional().describe('Sort order by confidence score'),
		}).describe('Filter options for the results'),
		date: z.string().describe('The date allows you to go back in time and do the trade decision for a point in the past').optional(),
	},
	{
		output: z.object({
			content: z.array(z.object({
				type: z.literal('text'),
				text: z.string().describe('JSON string containing the tickers array with symbol, timeframe, market, and confidence data'),
			})).describe('List of assets filtered by market regime with confidence scores'),
		}),
	},
	async ({ listOfAssets, timeframe, market, filter, date }: {
		listOfAssets: string[],
		timeframe: '1h' | '4h' | '1d',
		market: 'trending' | 'ranging',
		filter: { limit?: number, order?: 'asc' | 'desc' },
		date?: string
	}) => {

		try {
			// Call the scanner service to get filtered assets
			const result = await getListAssetsByMarket({
				listOfAssets,
				market,
				filter,
				date
			}
			)

			const response = {
				tickers: result.map((ticker: ScannerAsset) => ({
					symbol: ticker.symbol,
					timeframe: ticker.timeframe,
					market: ticker.market,
					confidence: ticker.confidence
				}))
			}

			return {
				content: [
					{
						type: 'text',
						text: JSON.stringify(response, null, 2),
					},
				],
			}

		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'

			return {
				content: [
					{
						type: 'text',
						text: JSON.stringify({
							error: 'Failed to get assets by market',
							message: errorMessage,
							tickers: []
						}, null, 2),
					},
				],
			}
		}
	},
)
