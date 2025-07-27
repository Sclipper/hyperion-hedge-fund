import logging
import time
from typing import Dict, List, Optional, Callable, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd

from .client import AlphaVantageClient
from .checkpoint_manager import CheckpointManager

logger = logging.getLogger(__name__)


@dataclass
class DownloadChunk:
    """Represents a single download chunk"""
    start_date: datetime
    end_date: datetime
    timeframe: str
    ticker: str
    status: str = 'pending'  # pending, downloading, completed, failed
    data: Optional[pd.DataFrame] = None
    error: Optional[str] = None
    attempt: int = 0
    max_attempts: int = 3


@dataclass
class DownloadPlan:
    """Represents a complete download plan for a ticker/timeframe"""
    ticker: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    chunks: List[DownloadChunk]
    total_chunks: int
    completed_chunks: int = 0
    failed_chunks: int = 0


class BulkDataFetcher:
    """
    Efficient bulk data fetching with chunking for Alpha Vantage
    
    Features:
    - Optimal chunk sizing based on timeframe and API limits
    - Parallel downloading with rate limiting
    - Progress tracking and resumable downloads
    - Automatic retry with exponential backoff
    """
    
    # Optimal chunk sizes based on Alpha Vantage limits and timeframe
    CHUNK_STRATEGIES = {
        '60min': {
            'months_per_chunk': 2,     # ~1,460 data points (2 months × 30 days × 24 hours)
            'max_years_per_request': 2  # Alpha Vantage limit
        },
        '240min': {
            'months_per_chunk': 6,     # ~1,080 data points (6 months × 30 days × 6 periods)
            'max_years_per_request': 2
        },
        'daily': {
            'months_per_chunk': 24,    # ~504 data points (24 months × 21 trading days)
            'max_years_per_request': 20
        }
    }
    
    def __init__(self, client: AlphaVantageClient, checkpoint_dir: str = "data/checkpoints"):
        self.client = client
        self.active_downloads = {}  # Track active download plans
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        
        # Initialize error handler
        from .error_handler import ErrorRecoveryStrategy
        self.error_handler = ErrorRecoveryStrategy(max_retries=3)
        
    def create_download_plan(
        self,
        ticker: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> DownloadPlan:
        """
        Create an optimal download plan with chunking strategy
        
        Args:
            ticker: Symbol to download
            timeframe: Data timeframe 
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DownloadPlan with optimized chunks
        """
        # Convert our timeframe format to Alpha Vantage format
        av_timeframe = self._convert_timeframe(timeframe)
        
        if av_timeframe not in self.CHUNK_STRATEGIES:
            raise ValueError(f"Unsupported timeframe for bulk fetching: {timeframe}")
        
        strategy = self.CHUNK_STRATEGIES[av_timeframe]
        months_per_chunk = strategy['months_per_chunk']
        
        # Calculate chunks
        chunks = []
        current_date = start_date
        
        while current_date < end_date:
            chunk_end = min(
                current_date + timedelta(days=months_per_chunk * 30),
                end_date
            )
            
            chunk = DownloadChunk(
                start_date=current_date,
                end_date=chunk_end,
                timeframe=timeframe,
                ticker=ticker
            )
            chunks.append(chunk)
            
            current_date = chunk_end + timedelta(days=1)
        
        plan = DownloadPlan(
            ticker=ticker,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            chunks=chunks,
            total_chunks=len(chunks)
        )
        
        logger.info(f"Created download plan for {ticker} {timeframe}: "
                   f"{len(chunks)} chunks from {start_date.date()} to {end_date.date()}")
        
        return plan
    
    def execute_download_plan(
        self,
        plan: DownloadPlan,
        progress_callback: Optional[Callable[[str, int, Dict], None]] = None,
        max_parallel: int = 3,
        enable_checkpoints: bool = True,
        checkpoint_interval: int = 5
    ) -> pd.DataFrame:
        """
        Execute a download plan with progress tracking and checkpointing
        
        Args:
            plan: DownloadPlan to execute
            progress_callback: Optional callback(status, progress_percent, stats)
            max_parallel: Maximum parallel downloads
            enable_checkpoints: Enable checkpoint saving for resumable downloads
            checkpoint_interval: Save checkpoint every N completed chunks
            
        Returns:
            Combined DataFrame with all data
        """
        plan_id = f"{plan.ticker}_{plan.timeframe}_{int(time.time())}"
        self.active_downloads[plan_id] = plan
        
        logger.info(f"Executing download plan {plan_id}: {plan.total_chunks} chunks")
        
        # Save initial checkpoint if enabled
        if enable_checkpoints:
            self.checkpoint_manager.save_checkpoint(plan, plan_id)
            logger.info(f"Initial checkpoint saved for {plan_id}")
        
        try:
            # Process chunks with rate limiting
            completed_data = []
            
            for i, chunk in enumerate(plan.chunks):
                # Skip chunks that are already completed (for resumed downloads)
                if chunk.status == 'completed':
                    logger.debug(f"Skipping already completed chunk {i+1}/{plan.total_chunks}")
                    continue
                    
                if progress_callback:
                    progress_stats = {
                        'completed_chunks': plan.completed_chunks,
                        'total_chunks': plan.total_chunks,
                        'failed_chunks': plan.failed_chunks,
                        'current_chunk': i + 1,
                        'plan_id': plan_id
                    }
                    progress_callback(
                        f"Downloading chunk {i+1}/{plan.total_chunks} for {plan.ticker}",
                        int((plan.completed_chunks / plan.total_chunks) * 100),
                        progress_stats
                    )
                
                chunk_data = self._download_chunk(chunk)
                
                if chunk_data is not None and not chunk_data.empty:
                    completed_data.append(chunk_data)
                    plan.completed_chunks += 1
                    chunk.status = 'completed'
                    logger.info(f"Completed chunk {i+1}/{plan.total_chunks}: {len(chunk_data)} records")
                    
                    # Save checkpoint periodically
                    if enable_checkpoints and plan.completed_chunks % checkpoint_interval == 0:
                        self.checkpoint_manager.update_checkpoint(plan, plan_id)
                        logger.debug(f"Checkpoint updated at {plan.completed_chunks}/{plan.total_chunks} chunks")
                        
                else:
                    plan.failed_chunks += 1
                    chunk.status = 'failed'
                    logger.warning(f"Failed chunk {i+1}/{plan.total_chunks}")
                    
                    # Update checkpoint after failures too
                    if enable_checkpoints:
                        self.checkpoint_manager.update_checkpoint(plan, plan_id)
            
            # Combine all data
            if completed_data:
                combined_df = pd.concat(completed_data, ignore_index=False)
                combined_df = combined_df.sort_index()
                combined_df = combined_df.drop_duplicates()
                
                # Add metadata
                combined_df.attrs['provider_source'] = 'alpha_vantage'
                combined_df.attrs['timeframe'] = plan.timeframe
                combined_df.attrs['ticker'] = plan.ticker
                combined_df.attrs['bulk_download'] = True
                combined_df.attrs['total_chunks'] = plan.total_chunks
                combined_df.attrs['completed_chunks'] = plan.completed_chunks
                
                # Validate combined data
                try:
                    from .data_validator import DataValidator
                    validator = DataValidator()
                    
                    # Determine asset type
                    from ..alpha_vantage.provider import AlphaVantageProvider
                    provider = AlphaVantageProvider()
                    asset_type = 'crypto' if provider._is_crypto_symbol(plan.ticker) else 'stock'
                    
                    validation_result = validator.validate_dataframe(
                        combined_df, plan.ticker, plan.timeframe, asset_type
                    )
                    
                    # Add validation metadata
                    combined_df.attrs['validation_passed'] = validation_result.is_valid
                    combined_df.attrs['validation_errors'] = len(validation_result.errors)
                    combined_df.attrs['validation_warnings'] = len(validation_result.warnings)
                    
                    if not validation_result.is_valid:
                        logger.warning(f"Bulk download validation failed for {plan.ticker}: "
                                     f"{len(validation_result.errors)} errors")
                        # Apply repairs
                        combined_df = validator.repair_data(combined_df, validation_result)
                        logger.info(f"Applied validation repairs to bulk download for {plan.ticker}")
                        
                except Exception as e:
                    logger.warning(f"Could not validate bulk download data: {e}")
                    combined_df.attrs['validation_passed'] = None
                
                if progress_callback:
                    final_stats = {
                        'completed_chunks': plan.completed_chunks,
                        'total_chunks': plan.total_chunks,
                        'failed_chunks': plan.failed_chunks,
                        'total_records': len(combined_df)
                    }
                    progress_callback("Download complete", 100, final_stats)
                
                logger.info(f"Bulk download complete for {plan.ticker} {plan.timeframe}: "
                           f"{len(combined_df)} total records from {plan.completed_chunks} chunks")
                
                # Mark checkpoint as completed
                if enable_checkpoints:
                    self.checkpoint_manager.complete_checkpoint(plan_id)
                    logger.info(f"Checkpoint completed and archived: {plan_id}")
                
                return combined_df
            else:
                logger.error(f"No data retrieved for {plan.ticker} {plan.timeframe}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error executing download plan {plan_id}: {e}")
            # Save checkpoint on error for potential resume
            if enable_checkpoints:
                self.checkpoint_manager.update_checkpoint(plan, plan_id)
                logger.info(f"Checkpoint saved on error for potential resume: {plan_id}")
            raise
        finally:
            # Clean up active downloads
            if plan_id in self.active_downloads:
                del self.active_downloads[plan_id]
    
    def _download_chunk(self, chunk: DownloadChunk) -> Optional[pd.DataFrame]:
        """
        Download a single chunk with retry logic
        
        Args:
            chunk: DownloadChunk to process
            
        Returns:
            DataFrame with chunk data or None if failed
        """
        while chunk.attempt < chunk.max_attempts:
            chunk.attempt += 1
            chunk.status = 'downloading'
            
            try:
                logger.debug(f"Downloading chunk {chunk.ticker} {chunk.timeframe} "
                           f"{chunk.start_date.date()} to {chunk.end_date.date()} "
                           f"(attempt {chunk.attempt})")
                
                # Use the client to fetch data for this chunk
                data = self.client.fetch_data(
                    ticker=chunk.ticker,
                    timeframe=chunk.timeframe,
                    start_date=chunk.start_date,
                    end_date=chunk.end_date
                )
                
                if data is not None and not data.empty:
                    chunk.data = data
                    chunk.status = 'completed'
                    return data
                else:
                    logger.warning(f"No data returned for chunk {chunk.ticker} {chunk.timeframe}")
                    
            except Exception as e:
                chunk.error = str(e)
                logger.warning(f"Chunk download attempt {chunk.attempt} failed: {e}")
                
                if chunk.attempt < chunk.max_attempts:
                    # Exponential backoff
                    wait_time = 2 ** chunk.attempt
                    logger.info(f"Retrying chunk in {wait_time} seconds...")
                    time.sleep(wait_time)
        
        # All attempts failed
        chunk.status = 'failed'
        logger.error(f"Chunk download failed after {chunk.max_attempts} attempts: {chunk.error}")
        return None
    
    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert our timeframe format to Alpha Vantage format"""
        mapping = {
            '1h': '60min',
            '4h': '60min',  # We'll process 4h by resampling 1h data
            '1d': 'daily'
        }
        return mapping.get(timeframe, timeframe)
    
    def get_active_downloads(self) -> Dict[str, Dict]:
        """Get status of all active downloads"""
        status = {}
        for plan_id, plan in self.active_downloads.items():
            status[plan_id] = {
                'ticker': plan.ticker,
                'timeframe': plan.timeframe,
                'total_chunks': plan.total_chunks,
                'completed_chunks': plan.completed_chunks,
                'failed_chunks': plan.failed_chunks,
                'progress_percent': int((plan.completed_chunks / plan.total_chunks) * 100),
                'status': 'downloading'
            }
        return status
    
    def estimate_download_time(
        self,
        ticker: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, float]:
        """
        Estimate download time for a bulk request
        
        Returns:
            Dict with time estimates
        """
        plan = self.create_download_plan(ticker, timeframe, start_date, end_date)
        
        # Alpha Vantage rate limit: 75 requests per minute
        requests_per_minute = 75
        chunk_count = len(plan.chunks)
        
        # Add overhead for processing and rate limiting
        estimated_minutes = (chunk_count / requests_per_minute) * 1.2
        
        return {
            'total_chunks': chunk_count,
            'estimated_minutes': estimated_minutes,
            'estimated_seconds': estimated_minutes * 60,
            'requests_per_minute': requests_per_minute,
            'timeframe': timeframe,
            'date_range_days': (end_date - start_date).days
        }
    
    def resume_download(self, plan_id: str, 
                       progress_callback: Optional[Callable[[str, int, Dict], None]] = None) -> pd.DataFrame:
        """
        Resume a download from checkpoint
        
        Args:
            plan_id: Checkpoint identifier to resume
            progress_callback: Optional progress callback
            
        Returns:
            Combined DataFrame with all data
        """
        logger.info(f"Attempting to resume download: {plan_id}")
        
        # Load checkpoint
        plan = self.checkpoint_manager.load_checkpoint(plan_id)
        if not plan:
            raise ValueError(f"Cannot resume: checkpoint {plan_id} not found")
        
        # Validate checkpoint
        validation = self.checkpoint_manager.validate_checkpoint(plan_id)
        if not validation['can_resume']:
            raise ValueError(f"Cannot resume: {validation.get('error', 'download already complete')}")
        
        logger.info(f"Resuming {plan_id}: {plan.completed_chunks}/{plan.total_chunks} chunks completed")
        
        # Execute remaining chunks
        return self.execute_download_plan(
            plan=plan,
            progress_callback=progress_callback,
            enable_checkpoints=True
        )
    
    def list_resumable_downloads(self, ticker: str = None, timeframe: str = None) -> List[Dict[str, Any]]:
        """
        List downloads that can be resumed
        
        Args:
            ticker: Filter by ticker (optional)
            timeframe: Filter by timeframe (optional)
            
        Returns:
            List of resumable download information
        """
        return [
            checkpoint for checkpoint in self.checkpoint_manager.list_active_checkpoints()
            if checkpoint['can_resume'] and
               (ticker is None or checkpoint['ticker'] == ticker) and
               (timeframe is None or checkpoint['timeframe'] == timeframe)
        ]
    
    def cleanup_checkpoints(self, days: int = 7) -> int:
        """
        Clean up old completed checkpoints
        
        Args:
            days: Delete checkpoints older than this many days
            
        Returns:
            Number of checkpoints deleted
        """
        return self.checkpoint_manager.cleanup_old_checkpoints(days)
    
    def get_checkpoint_status(self, plan_id: str = None) -> Dict[str, Any]:
        """
        Get checkpoint system status
        
        Args:
            plan_id: Specific checkpoint to check (optional)
            
        Returns:
            Checkpoint status information
        """
        if plan_id:
            return self.checkpoint_manager.validate_checkpoint(plan_id)
        else:
            return self.checkpoint_manager.get_checkpoint_stats()