"""
Automated scheduler for scraping Philadelphia events
Runs scrapers periodically in the background
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from database import EventDatabase
from scrapers import SCRAPERS
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventScheduler:
    """Scheduler for automatic event scraping"""

    def __init__(self, db: EventDatabase):
        self.db = db
        self.scheduler = BackgroundScheduler()

    def scrape_all_sources(self):
        """Run all scrapers and update database"""
        logger.info(f"[{datetime.now()}] Starting scheduled scrape...")

        total_scraped = 0
        total_added = 0

        for ScraperClass in SCRAPERS:
            try:
                scraper = ScraperClass()
                events = scraper.scrape()
                added = self.db.add_events_batch(events)

                total_scraped += len(events)
                total_added += added

                logger.info(f"{scraper.source_name}: {len(events)} scraped, {added} added")

            except Exception as e:
                logger.error(f"Error scraping {ScraperClass.__name__}: {e}")

        logger.info(f"Scheduled scrape complete: {total_scraped} scraped, {total_added} added")

        # Clean up old events (older than 30 days)
        deleted = self.db.delete_old_events(days_old=30)
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old events")

        return total_added

    def start(self, interval_hours: int = 12):
        """
        Start the scheduler

        Args:
            interval_hours: How often to scrape (default: every 12 hours)
        """
        # Schedule scraping every X hours
        self.scheduler.add_job(
            func=self.scrape_all_sources,
            trigger=IntervalTrigger(hours=interval_hours),
            id='scrape_events',
            name='Scrape Philadelphia Events',
            replace_existing=True
        )

        # Also schedule daily cleanup at 3 AM
        self.scheduler.add_job(
            func=lambda: self.db.delete_old_events(days_old=30),
            trigger=CronTrigger(hour=3, minute=0),
            id='cleanup_old_events',
            name='Cleanup Old Events',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(f"Scheduler started. Will scrape every {interval_hours} hours.")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    def get_next_run_time(self):
        """Get when the next scrape will run"""
        job = self.scheduler.get_job('scrape_events')
        if job:
            return job.next_run_time
        return None


if __name__ == '__main__':
    # Test the scheduler
    db = EventDatabase()
    scheduler = EventScheduler(db)

    # Run one scrape immediately
    logger.info("Running initial scrape...")
    scheduler.scrape_all_sources()

    # Start scheduled scraping every 6 hours (for testing)
    scheduler.start(interval_hours=6)

    logger.info(f"Next scrape scheduled for: {scheduler.get_next_run_time()}")

    # Keep the script running
    try:
        import time
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.stop()
