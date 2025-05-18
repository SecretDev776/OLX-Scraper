from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from scraper import OLXScraper
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScrapingScheduler:
    def __init__(self, interval_minutes: int = 5):
        self.scheduler = BackgroundScheduler()
        self.scraper = OLXScraper()
        self.interval_minutes = interval_minutes

    def scrape_job(self):
        """Job to be executed periodically"""
        try:
            logger.info(f"Starting scraping job at {datetime.now()}")
            new_listings = self.scraper.scrape()
            logger.info(f"Found {len(new_listings)} new listings")
        except Exception as e:
            logger.error(f"Error in scraping job: {e}")

    def start(self):
        """Start the scheduler"""
        self.scheduler.add_job(
            self.scrape_job,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id='scraping_job',
            name='Scrape OLX listings',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info(f"Scheduler started with {self.interval_minutes} minute interval")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

if __name__ == "__main__":
    scheduler = ScrapingScheduler()
    scheduler.start()
    
    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop() 