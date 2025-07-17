import * as cron from 'node-cron'
import { logger } from '@/utils/fns'
import { scanAllAssets } from './Scanner.controller'

let scannerScheduler: cron.ScheduledTask | null = null
let isScanning = false

/**
 * Starts the Scanner cron job that runs every 30 minutes
 */
export const startScannerScheduler = (): void => {
  logger.info('🕒 Starting Scanner scheduler (every 30 minutes)...')
  
  // Stop existing scheduler if any
  if (scannerScheduler) {
    scannerScheduler.stop()
  }
  
  // Create new scheduler - runs every 30 minutes
  scannerScheduler = cron.schedule('*/60 * * * *', async () => {
    if (isScanning) {
      logger.warn('⚠️  Scanner already running, skipping this cycle')
      return
    }
    
    isScanning = true
    logger.info('🔍 Cron triggered: Starting asset scan...')
    
    try {
      const result = await scanAllAssets()
      
      logger.info(`✅ Cron scan completed:`, {
        totalScanned: result.totalScanned,
        totalSaved: result.totalSaved,
        duration: `${result.duration}ms`,
        errors: result.errors.length
      })
      
      if (result.errors.length > 0) {
        logger.error('❌ Scan errors:', result.errors)
      }
      
    } catch (error) {
      logger.error('❌ Critical error in scheduled scan:', error)
    } finally {
      isScanning = false
    }
  })
  
  // Start the scheduler
  scannerScheduler.start()
  
  logger.info('✅ Scanner scheduler started successfully')
}

/**
 * Stops the Scanner scheduler
 */
export const stopScannerScheduler = (): void => {
  if (scannerScheduler) {
    scannerScheduler.stop()
    scannerScheduler = null
    logger.info('⏹️  Scanner scheduler stopped')
  }
}

/**
 * Gets the status of the Scanner scheduler
 */
export const getScannerSchedulerStatus = (): {
  isActive: boolean
  isCurrentlyScanning: boolean
  nextRunTime?: string
} => {
  return {
    isActive: scannerScheduler ? scannerScheduler.getStatus() === 'scheduled' : false,
    isCurrentlyScanning: isScanning,
    nextRunTime: scannerScheduler ? 'Every 30 minutes' : undefined
  }
}

/**
 * Triggers a manual scan (outside of the schedule)
 */
export const triggerManualScan = async (): Promise<void> => {
  if (isScanning) {
    throw new Error('Scanner is already running')
  }
  
  logger.info('🔄 Manual scan triggered...')
  isScanning = true
  
  try {
    const result = await scanAllAssets()
    
    logger.info(`✅ Manual scan completed:`, {
      totalScanned: result.totalScanned,
      totalSaved: result.totalSaved,
      duration: `${result.duration}ms`,
      errors: result.errors.length
    })
    
    if (result.errors.length > 0) {
      logger.error('❌ Manual scan errors:', result.errors)
    }
    
  } catch (error) {
    logger.error('❌ Critical error in manual scan:', error)
    throw error
  } finally {
    isScanning = false
  }
}

// Different cron schedule options for reference:
// '*/30 * * * *' - Every 30 minutes
// '*/15 * * * *' - Every 15 minutes 
// '0 */1 * * *'  - Every hour
// '0 9-17 * * 1-5' - Every hour from 9am-5pm, weekdays only
// '0 9,12,15,18 * * 1-5' - At 9am, 12pm, 3pm, 6pm on weekdays 