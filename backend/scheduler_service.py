"""
Scheduler Service
=================
Standalone scheduler process for cron jobs.
Triggers jobs via Redis queue instead of running them directly.
"""
import os
import sys
import signal
import logging
from datetime import datetime

# Setup path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.job_queue import (
    enqueue_auto_scrape_job, enqueue_backup_job, get_job_queue
)
from app import db

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('scheduler')

# Suppress noisy APScheduler logs
logging.getLogger('apscheduler').setLevel(logging.WARNING)

# Scheduler instance
scheduler = BlockingScheduler()

# Graceful shutdown flag
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global _shutdown_requested
    logger.info(f"Received signal {signum}, initiating shutdown...")
    _shutdown_requested = True
    scheduler.shutdown(wait=False)


def trigger_auto_scrape():
    """Trigger automatic scraping via job queue."""
    try:
        job_id = enqueue_auto_scrape_job()
        logger.info(f"Triggered auto-scrape job: {job_id}")
    except Exception as e:
        logger.error(f"Failed to trigger auto-scrape: {e}")


def trigger_hourly_backup():
    """Trigger hourly backup via job queue."""
    try:
        job_id = enqueue_backup_job('hourly')
        logger.info(f"Triggered hourly backup job: {job_id}")
    except Exception as e:
        logger.error(f"Failed to trigger hourly backup: {e}")


def trigger_daily_backup():
    """Trigger daily backup via job queue."""
    try:
        job_id = enqueue_backup_job('daily')
        logger.info(f"Triggered daily backup job: {job_id}")
    except Exception as e:
        logger.error(f"Failed to trigger daily backup: {e}")


def log_queue_stats():
    """Log queue statistics."""
    try:
        queue = get_job_queue()
        stats = queue.get_queue_stats()
        logger.info(f"Queue stats: pending={stats['pending']}, "
                   f"processing={stats['processing']}, "
                   f"completed_today={stats['completed_today']}")
    except Exception as e:
        logger.warning(f"Could not get queue stats: {e}")


def setup_jobs():
    """Configure scheduled jobs."""
    # Auto-scrape: every 3 hours
    scheduler.add_job(
        trigger_auto_scrape,
        IntervalTrigger(hours=3),
        id='auto_scrape',
        name='Auto Scrape',
        replace_existing=True
    )
    
    # Hourly backup
    scheduler.add_job(
        trigger_hourly_backup,
        IntervalTrigger(hours=1),
        id='hourly_backup',
        name='Hourly Backup',
        replace_existing=True
    )
    
    # Daily backup at 2 AM
    scheduler.add_job(
        trigger_daily_backup,
        CronTrigger(hour=2, minute=0),
        id='daily_backup',
        name='Daily Backup',
        replace_existing=True
    )
    
    # Queue stats every 15 minutes
    scheduler.add_job(
        log_queue_stats,
        IntervalTrigger(minutes=15),
        id='queue_stats',
        name='Queue Stats',
        replace_existing=True
    )


def main():
    """Entry point."""
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("=" * 50)
    logger.info("VibeCoding Scheduler Started")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 50)
    
    # Initialize database (for any direct operations)
    try:
        db.init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database init warning: {e}")
    
    # Setup jobs
    setup_jobs()
    
    # Log configured jobs
    logger.info("Scheduled jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name}: {job.trigger}")
    
    # Run initial queue stats
    log_queue_stats()
    
    # Start scheduler (blocking)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("Scheduler stopped")


if __name__ == '__main__':
    main()
