import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

# Import types will be handled at runtime to avoid circular imports

logger = logging.getLogger(__name__)


@dataclass
class CheckpointData:
    """Represents a saved checkpoint for resumable downloads"""
    plan_id: str
    ticker: str
    timeframe: str
    start_date: str  # ISO format
    end_date: str    # ISO format
    total_chunks: int
    completed_chunks: int
    failed_chunks: int
    chunk_states: List[Dict[str, Any]]  # Serialized chunk data
    created_at: str
    last_updated: str
    
    
class CheckpointManager:
    """
    Manages checkpoint files for resumable bulk downloads
    
    Features:
    - Save/load download progress across sessions
    - Resume partially completed downloads
    - Cleanup completed/expired checkpoints
    - Progress validation and recovery
    """
    
    def __init__(self, checkpoint_dir: str = "data/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Separate directories for active and completed checkpoints
        self.active_dir = self.checkpoint_dir / "active"
        self.completed_dir = self.checkpoint_dir / "completed"
        self.active_dir.mkdir(exist_ok=True)
        self.completed_dir.mkdir(exist_ok=True)
        
        logger.info(f"CheckpointManager initialized with directory: {self.checkpoint_dir}")
    
    def save_checkpoint(self, plan, plan_id: str) -> bool:
        """
        Save current download plan as checkpoint
        
        Args:
            plan: DownloadPlan to checkpoint
            plan_id: Unique identifier for the plan
            
        Returns:
            True if checkpoint saved successfully
        """
        try:
            # Serialize chunk data
            chunk_states = []
            for chunk in plan.chunks:
                chunk_data = {
                    'start_date': chunk.start_date.isoformat(),
                    'end_date': chunk.end_date.isoformat(),
                    'timeframe': chunk.timeframe,
                    'ticker': chunk.ticker,
                    'status': chunk.status,
                    'error': chunk.error,
                    'attempt': chunk.attempt,
                    'max_attempts': chunk.max_attempts
                }
                chunk_states.append(chunk_data)
            
            checkpoint = CheckpointData(
                plan_id=plan_id,
                ticker=plan.ticker,
                timeframe=plan.timeframe,
                start_date=plan.start_date.isoformat(),
                end_date=plan.end_date.isoformat(),
                total_chunks=plan.total_chunks,
                completed_chunks=plan.completed_chunks,
                failed_chunks=plan.failed_chunks,
                chunk_states=chunk_states,
                created_at=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat()
            )
            
            checkpoint_file = self.active_dir / f"{plan_id}.json"
            with open(checkpoint_file, 'w') as f:
                json.dump(asdict(checkpoint), f, indent=2)
            
            logger.info(f"Checkpoint saved: {checkpoint_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint for {plan_id}: {e}")
            return False
    
    def load_checkpoint(self, plan_id: str):
        """
        Load checkpoint and reconstruct DownloadPlan
        
        Args:
            plan_id: Checkpoint identifier to load
            
        Returns:
            Reconstructed DownloadPlan or None if not found
        """
        try:
            checkpoint_file = self.active_dir / f"{plan_id}.json"
            if not checkpoint_file.exists():
                logger.warning(f"Checkpoint not found: {checkpoint_file}")
                return None
            
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            
            checkpoint = CheckpointData(**checkpoint_data)
            
            # Import classes at runtime to avoid circular imports
            from .bulk_fetcher import DownloadChunk, DownloadPlan
            
            # Reconstruct chunks
            chunks = []
            for chunk_data in checkpoint.chunk_states:
                chunk = DownloadChunk(
                    start_date=datetime.fromisoformat(chunk_data['start_date']),
                    end_date=datetime.fromisoformat(chunk_data['end_date']),
                    timeframe=chunk_data['timeframe'],
                    ticker=chunk_data['ticker'],
                    status=chunk_data['status'],
                    error=chunk_data.get('error'),
                    attempt=chunk_data['attempt'],
                    max_attempts=chunk_data['max_attempts']
                )
                chunks.append(chunk)
            
            # Reconstruct DownloadPlan
            plan = DownloadPlan(
                ticker=checkpoint.ticker,
                timeframe=checkpoint.timeframe,
                start_date=datetime.fromisoformat(checkpoint.start_date),
                end_date=datetime.fromisoformat(checkpoint.end_date),
                chunks=chunks,
                total_chunks=checkpoint.total_chunks,
                completed_chunks=checkpoint.completed_chunks,
                failed_chunks=checkpoint.failed_chunks
            )
            
            logger.info(f"Checkpoint loaded: {plan_id} ({plan.completed_chunks}/{plan.total_chunks} chunks completed)")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint {plan_id}: {e}")
            return None
    
    def update_checkpoint(self, plan, plan_id: str) -> bool:
        """
        Update existing checkpoint with current progress
        
        Args:
            plan: Updated DownloadPlan
            plan_id: Checkpoint identifier
            
        Returns:
            True if update successful
        """
        try:
            checkpoint_file = self.active_dir / f"{plan_id}.json"
            if not checkpoint_file.exists():
                logger.warning(f"Cannot update non-existent checkpoint: {plan_id}")
                return self.save_checkpoint(plan, plan_id)
            
            # Load existing checkpoint to preserve metadata
            with open(checkpoint_file, 'r') as f:
                existing_data = json.load(f)
            
            # Update with current plan state
            chunk_states = []
            for chunk in plan.chunks:
                chunk_data = {
                    'start_date': chunk.start_date.isoformat(),
                    'end_date': chunk.end_date.isoformat(),
                    'timeframe': chunk.timeframe,
                    'ticker': chunk.ticker,
                    'status': chunk.status,
                    'error': chunk.error,
                    'attempt': chunk.attempt,
                    'max_attempts': chunk.max_attempts
                }
                chunk_states.append(chunk_data)
            
            existing_data.update({
                'completed_chunks': plan.completed_chunks,
                'failed_chunks': plan.failed_chunks,
                'chunk_states': chunk_states,
                'last_updated': datetime.now().isoformat()
            })
            
            with open(checkpoint_file, 'w') as f:
                json.dump(existing_data, f, indent=2)
            
            logger.debug(f"Checkpoint updated: {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update checkpoint {plan_id}: {e}")
            return False
    
    def complete_checkpoint(self, plan_id: str) -> bool:
        """
        Mark checkpoint as completed and move to completed directory
        
        Args:
            plan_id: Checkpoint identifier to complete
            
        Returns:
            True if completion successful
        """
        try:
            active_file = self.active_dir / f"{plan_id}.json"
            if not active_file.exists():
                logger.warning(f"Cannot complete non-existent checkpoint: {plan_id}")
                return False
            
            # Move to completed directory
            completed_file = self.completed_dir / f"{plan_id}.json"
            active_file.rename(completed_file)
            
            logger.info(f"Checkpoint completed and archived: {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete checkpoint {plan_id}: {e}")
            return False
    
    def delete_checkpoint(self, plan_id: str, completed: bool = False) -> bool:
        """
        Delete checkpoint file
        
        Args:
            plan_id: Checkpoint identifier
            completed: Look in completed directory if True
            
        Returns:
            True if deletion successful
        """
        try:
            directory = self.completed_dir if completed else self.active_dir
            checkpoint_file = directory / f"{plan_id}.json"
            
            if checkpoint_file.exists():
                checkpoint_file.unlink()
                logger.info(f"Checkpoint deleted: {plan_id}")
                return True
            else:
                logger.warning(f"Checkpoint not found for deletion: {plan_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete checkpoint {plan_id}: {e}")
            return False
    
    def list_active_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List all active (resumable) checkpoints
        
        Returns:
            List of checkpoint summaries
        """
        checkpoints = []
        
        try:
            for checkpoint_file in self.active_dir.glob("*.json"):
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                
                checkpoint_info = {
                    'plan_id': data['plan_id'],
                    'ticker': data['ticker'],
                    'timeframe': data['timeframe'],
                    'progress': f"{data['completed_chunks']}/{data['total_chunks']}",
                    'progress_percent': int((data['completed_chunks'] / data['total_chunks']) * 100),
                    'failed_chunks': data['failed_chunks'],
                    'created_at': data['created_at'],
                    'last_updated': data['last_updated'],
                    'can_resume': data['completed_chunks'] < data['total_chunks']
                }
                checkpoints.append(checkpoint_info)
                
        except Exception as e:
            logger.error(f"Error listing active checkpoints: {e}")
        
        return sorted(checkpoints, key=lambda x: x['last_updated'], reverse=True)
    
    def get_resumable_downloads(self, ticker: str = None, timeframe: str = None) -> List[str]:
        """
        Get list of plan IDs that can be resumed
        
        Args:
            ticker: Filter by ticker (optional)
            timeframe: Filter by timeframe (optional)
            
        Returns:
            List of resumable plan IDs
        """
        resumable = []
        
        for checkpoint in self.list_active_checkpoints():
            if not checkpoint['can_resume']:
                continue
                
            if ticker and checkpoint['ticker'] != ticker:
                continue
                
            if timeframe and checkpoint['timeframe'] != timeframe:
                continue
                
            resumable.append(checkpoint['plan_id'])
        
        return resumable
    
    def cleanup_old_checkpoints(self, days: int = 7) -> int:
        """
        Clean up old completed checkpoints
        
        Args:
            days: Delete checkpoints older than this many days
            
        Returns:
            Number of checkpoints deleted
        """
        deleted_count = 0
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        try:
            for checkpoint_file in self.completed_dir.glob("*.json"):
                if checkpoint_file.stat().st_mtime < cutoff_date:
                    checkpoint_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old checkpoint: {checkpoint_file.name}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old checkpoints")
                
        except Exception as e:
            logger.error(f"Error during checkpoint cleanup: {e}")
        
        return deleted_count
    
    def get_checkpoint_stats(self) -> Dict[str, Any]:
        """Get statistics about checkpoint system"""
        try:
            active_checkpoints = list(self.active_dir.glob("*.json"))
            completed_checkpoints = list(self.completed_dir.glob("*.json"))
            
            # Calculate total disk usage
            total_size = sum(f.stat().st_size for f in active_checkpoints + completed_checkpoints)
            
            stats = {
                'active_checkpoints': len(active_checkpoints),
                'completed_checkpoints': len(completed_checkpoints),
                'total_disk_usage_bytes': total_size,
                'total_disk_usage_mb': round(total_size / (1024 * 1024), 2),
                'checkpoint_directory': str(self.checkpoint_dir)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting checkpoint stats: {e}")
            return {}
    
    def validate_checkpoint(self, plan_id: str) -> Dict[str, Any]:
        """
        Validate checkpoint integrity and provide recovery suggestions
        
        Args:
            plan_id: Checkpoint to validate
            
        Returns:
            Validation results and suggestions
        """
        try:
            plan = self.load_checkpoint(plan_id)
            if not plan:
                return {'valid': False, 'error': 'Checkpoint not found'}
            
            # Basic validation
            issues = []
            suggestions = []
            
            # Check for failed chunks
            failed_chunks = [c for c in plan.chunks if c.status == 'failed']
            if failed_chunks:
                issues.append(f"{len(failed_chunks)} failed chunks")
                suggestions.append("Consider retrying failed chunks")
            
            # Check for inconsistent counts
            actual_completed = len([c for c in plan.chunks if c.status == 'completed'])
            if actual_completed != plan.completed_chunks:
                issues.append("Inconsistent completed chunk count")
                suggestions.append("Checkpoint may need repair")
            
            # Check for old checkpoint
            try:
                checkpoint_file = self.active_dir / f"{plan_id}.json"
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                last_updated = datetime.fromisoformat(data['last_updated'])
                age_hours = (datetime.now() - last_updated).total_seconds() / 3600
                
                if age_hours > 24:
                    issues.append(f"Checkpoint is {age_hours:.1f} hours old")
                    suggestions.append("Consider starting fresh download")
            except:
                pass
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'suggestions': suggestions,
                'total_chunks': plan.total_chunks,
                'completed_chunks': plan.completed_chunks,
                'failed_chunks': plan.failed_chunks,
                'can_resume': plan.completed_chunks < plan.total_chunks
            }
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}