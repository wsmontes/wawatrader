"""
Log Cleanup and Organization Script

Standardizes all log files to a consistent pattern and removes outdated formats.

STANDARD LOG PATTERN:
- All logs in logs/ directory
- JSONL format (JSON Lines - one JSON object per line)
- Naming: <category>.jsonl (e.g., decisions.jsonl, market_data.jsonl)
- One log type per file
- Rotate daily/weekly for large files

DEPRECATED PATTERNS TO REMOVE:
- Multiple conversation logs (llm_conversations.jsonl, llm_conversations_v2.jsonl)
- JSON files (should be JSONL)
- System logs with timestamps in name
- Duplicate logs

Usage:
    python scripts/cleanup_logs.py              # Dry run (show what would be done)
    python scripts/cleanup_logs.py --execute    # Actually perform cleanup
    python scripts/cleanup_logs.py --archive    # Archive old logs before cleanup
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
import shutil
from typing import Dict, List
from loguru import logger

from config import settings


class LogCleanup:
    """Standardize and clean up log files"""
    
    # Standard log files we want to keep
    STANDARD_LOGS = {
        'decisions.jsonl': 'Trading decisions and LLM analysis',
        'market_data.jsonl': 'Market data fetched from Alpaca',
        'account_snapshots.jsonl': 'Account state over time',
        'position_snapshots.jsonl': 'Position details over time',
        'order_executions.jsonl': 'Order submissions and fills',
        'llm_conversations.jsonl': 'LLM prompts and responses',
        'system.log': 'System/application logs (loguru)',
    }
    
    # Files to remove (deprecated or duplicate)
    DEPRECATED_FILES = [
        'llm_conversations_v2.jsonl',  # Duplicate - merge into llm_conversations.jsonl
        'overnight_analysis.json',  # Should be JSONL
        'overnight_summary.jsonl',  # Part of decisions.jsonl
        'earnings_analysis.jsonl',  # Part of decisions.jsonl
        'premarket_scanner.jsonl',  # Part of decisions.jsonl
        'nohup.log',  # Temporary process log
        'system_startup.log',  # Duplicate of system.log
    ]
    
    # Pattern-based files to remove
    DEPRECATED_PATTERNS = [
        'system.*.log',  # Timestamped system logs
    ]
    
    def __init__(self, log_dir: Path = None):
        self.log_dir = log_dir or settings.project_root / "logs"
        self.archive_dir = settings.project_root / "logs" / "archive"
        self.actions = []
    
    def scan(self):
        """Scan log directory and plan cleanup actions"""
        logger.info(f"Scanning {self.log_dir}...")
        
        if not self.log_dir.exists():
            logger.warning(f"Log directory {self.log_dir} does not exist")
            return
        
        # Get all files
        all_files = [f for f in self.log_dir.iterdir() if f.is_file()]
        
        logger.info(f"Found {len(all_files)} files")
        
        # Check for standard logs
        for standard_log, description in self.STANDARD_LOGS.items():
            log_path = self.log_dir / standard_log
            if log_path.exists():
                size_mb = log_path.stat().st_size / (1024 * 1024)
                logger.info(f"✅ {standard_log}: {size_mb:.2f} MB - {description}")
            else:
                logger.info(f"⚪ {standard_log}: Not yet created - {description}")
        
        # Check for deprecated files
        for deprecated in self.DEPRECATED_FILES:
            dep_path = self.log_dir / deprecated
            if dep_path.exists():
                size_mb = dep_path.stat().st_size / (1024 * 1024)
                self.actions.append({
                    'action': 'remove',
                    'file': dep_path,
                    'reason': f'Deprecated format ({size_mb:.2f} MB)'
                })
                logger.warning(f"🗑️  {deprecated}: {size_mb:.2f} MB - DEPRECATED")
        
        # Check for pattern-based deprecated files
        for pattern in self.DEPRECATED_PATTERNS:
            import fnmatch
            for file in all_files:
                if fnmatch.fnmatch(file.name, pattern) and file.name not in self.STANDARD_LOGS:
                    size_mb = file.stat().st_size / (1024 * 1024)
                    self.actions.append({
                        'action': 'remove',
                        'file': file,
                        'reason': f'Matches deprecated pattern: {pattern} ({size_mb:.2f} MB)'
                    })
                    logger.warning(f"🗑️  {file.name}: {size_mb:.2f} MB - DEPRECATED PATTERN")
    
    def merge_conversation_logs(self):
        """Merge v2 conversation log into main conversation log"""
        main_log = self.log_dir / 'llm_conversations.jsonl'
        v2_log = self.log_dir / 'llm_conversations_v2.jsonl'
        
        if not v2_log.exists():
            return
        
        logger.info("Merging llm_conversations_v2.jsonl into llm_conversations.jsonl...")
        
        # Read v2 entries
        v2_entries = []
        try:
            with open(v2_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        v2_entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error reading v2 log: {e}")
            return
        
        if not v2_entries:
            logger.info("No entries to merge from v2")
            return
        
        # Append to main log
        try:
            with open(main_log, 'a') as f:
                for entry in v2_entries:
                    f.write(json.dumps(entry) + '\n')
            
            logger.info(f"✅ Merged {len(v2_entries)} entries from v2 into main log")
        except Exception as e:
            logger.error(f"Error merging logs: {e}")
    
    def archive_old_logs(self):
        """Archive logs before cleanup"""
        if not self.actions:
            logger.info("No files to archive")
            return
        
        # Create archive directory
        self.archive_dir.mkdir(exist_ok=True, parents=True)
        
        # Create timestamped archive
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_subdir = self.archive_dir / f"cleanup_{timestamp}"
        archive_subdir.mkdir(exist_ok=True)
        
        logger.info(f"Archiving to {archive_subdir}...")
        
        archived_count = 0
        for action in self.actions:
            if action['action'] == 'remove':
                src = action['file']
                dst = archive_subdir / src.name
                
                try:
                    shutil.copy2(src, dst)
                    logger.info(f"✅ Archived: {src.name}")
                    archived_count += 1
                except Exception as e:
                    logger.error(f"Error archiving {src.name}: {e}")
        
        logger.info(f"✅ Archived {archived_count} files to {archive_subdir}")
    
    def execute_cleanup(self, archive_first: bool = True):
        """Execute planned cleanup actions"""
        if not self.actions:
            logger.info("No cleanup actions needed")
            return
        
        if archive_first:
            self.archive_old_logs()
        
        logger.info("\nExecuting cleanup...")
        
        removed_count = 0
        for action in self.actions:
            if action['action'] == 'remove':
                file_path = action['file']
                reason = action['reason']
                
                try:
                    file_path.unlink()
                    logger.info(f"✅ Removed: {file_path.name} - {reason}")
                    removed_count += 1
                except Exception as e:
                    logger.error(f"Error removing {file_path.name}: {e}")
        
        logger.info(f"\n✅ Cleanup complete: {removed_count} files removed")
    
    def show_summary(self):
        """Show summary of what will be done"""
        logger.info("\n" + "="*60)
        logger.info("CLEANUP SUMMARY")
        logger.info("="*60)
        
        if not self.actions:
            logger.info("✅ No cleanup needed - logs are already standardized!")
            return
        
        logger.info(f"\nTotal actions: {len(self.actions)}")
        
        remove_actions = [a for a in self.actions if a['action'] == 'remove']
        if remove_actions:
            logger.info(f"\n🗑️  Files to remove ({len(remove_actions)}):")
            for action in remove_actions:
                logger.info(f"   - {action['file'].name}: {action['reason']}")
        
        total_size = sum(a['file'].stat().st_size for a in remove_actions)
        size_mb = total_size / (1024 * 1024)
        logger.info(f"\n💾 Space to be freed: {size_mb:.2f} MB")
        
        logger.info("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description='Clean up and standardize log files')
    parser.add_argument('--execute', action='store_true',
                       help='Actually perform cleanup (default is dry run)')
    parser.add_argument('--archive', action='store_true',
                       help='Archive old logs before cleanup')
    parser.add_argument('--no-archive', action='store_true',
                       help='Skip archiving (delete directly)')
    
    args = parser.parse_args()
    
    # Create cleanup manager
    cleanup = LogCleanup()
    
    # Scan for issues
    cleanup.scan()
    
    # Merge conversation logs
    if args.execute:
        cleanup.merge_conversation_logs()
    
    # Show summary
    cleanup.show_summary()
    
    # Execute if requested
    if args.execute:
        archive = not args.no_archive if args.no_archive else args.archive
        cleanup.execute_cleanup(archive_first=archive)
        logger.info("\n✅ Log cleanup complete!")
        logger.info("\nStandard log structure is now in place:")
        logger.info("  - decisions.jsonl: Trading decisions")
        logger.info("  - market_data.jsonl: Market data")
        logger.info("  - account_snapshots.jsonl: Account state")
        logger.info("  - position_snapshots.jsonl: Position details")
        logger.info("  - order_executions.jsonl: Order activity")
        logger.info("  - llm_conversations.jsonl: LLM interactions")
        logger.info("  - system.log: System logs")
    else:
        logger.info("\n💡 This was a DRY RUN. Use --execute to perform cleanup.")
        logger.info("   Use --archive to archive old logs before cleanup.")


if __name__ == "__main__":
    main()
