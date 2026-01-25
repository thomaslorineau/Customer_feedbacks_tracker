"""
PostgreSQL Database Backup Utility
===================================
Centralized backup functionality for PostgreSQL databases.
Replaces duplicate backup code across admin, worker, and scheduler modules.
"""
import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def create_postgres_backup(
    backup_type: str = 'manual',
    keep_backups: Optional[int] = None,
    backup_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Create a PostgreSQL database backup using pg_dump.
    
    Args:
        backup_type: Type of backup ('hourly', 'daily', 'manual')
        keep_backups: Number of backups to keep (None = no rotation)
        backup_dir: Directory for backups (None = auto-detect)
    
    Returns:
        Dict with status, backup_file, size_mb, etc.
    
    Raises:
        ValueError: If DATABASE_URL is not configured
        RuntimeError: If pg_dump fails
    """
    database_url = os.getenv('DATABASE_URL', '')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Parse DATABASE_URL: postgresql://user:password@host:port/database
    parsed = urlparse(database_url)
    db_user = parsed.username
    db_password = parsed.password
    db_host = parsed.hostname or 'localhost'
    db_port = parsed.port or 5432
    db_name = parsed.path.lstrip('/') or 'vibe_tracker'
    
    # Determine backup directory
    if backup_dir is None:
        # Try to detect from current file location
        current_file = Path(__file__)
        # backend/app/utils/backup.py -> backend/backups
        backup_dir = current_file.resolve().parents[2] / "backups"
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"postgres_backup_{backup_type}_{timestamp}.sql"
    backup_path = backup_dir / backup_filename
    
    # Set PGPASSWORD environment variable for pg_dump
    env = os.environ.copy()
    env['PGPASSWORD'] = db_password
    
    # Run pg_dump (plain text format for portability)
    cmd = [
        'pg_dump',
        '-h', db_host,
        '-p', str(db_port),
        '-U', db_user,
        '-d', db_name,
        '-F', 'p',  # Plain text format (portable)
        '-f', str(backup_path)
    ]
    
    logger.info(f"Creating PostgreSQL backup: {backup_filename}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    if result.returncode != 0:
        error_msg = result.stderr or "Unknown error"
        logger.error(f"pg_dump failed: {error_msg}")
        raise RuntimeError(f"Backup failed: {error_msg}")
    
    # Get backup size
    backup_size_mb = backup_path.stat().st_size / (1024 * 1024)
    logger.info(f"Backup completed: {backup_filename} ({backup_size_mb:.2f} MB)")
    
    # Rotate old backups if requested
    if keep_backups is not None:
        rotated = rotate_backups(backup_dir, backup_type, keep_backups)
        logger.info(f"Rotated backups: kept {keep_backups}, removed {rotated} old backups")
    
    return {
        'status': 'success',
        'backup_type': backup_type,
        'backup_file': backup_filename,
        'backup_path': str(backup_path),
        'size_mb': round(backup_size_mb, 2)
    }


def rotate_backups(backup_dir: Path, backup_type: str, keep_count: int) -> int:
    """
    Remove old backups, keeping only the most recent N backups.
    
    Args:
        backup_dir: Directory containing backups
        backup_type: Type of backup to rotate ('hourly', 'daily', 'manual')
        keep_count: Number of backups to keep
    
    Returns:
        Number of backups removed
    """
    pattern = f"postgres_backup_{backup_type}_*.sql"
    backups = sorted(
        backup_dir.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    if len(backups) <= keep_count:
        return 0
    
    removed = 0
    for old_backup in backups[keep_count:]:
        try:
            old_backup.unlink()
            logger.debug(f"Removed old backup: {old_backup.name}")
            removed += 1
        except Exception as e:
            logger.warning(f"Failed to remove old backup {old_backup.name}: {e}")
    
    return removed


def check_pg_dump_available() -> bool:
    """
    Check if pg_dump command is available in PATH.
    
    Returns:
        True if pg_dump is available, False otherwise
    """
    try:
        result = subprocess.run(
            ['pg_dump', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
