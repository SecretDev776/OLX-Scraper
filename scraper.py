import json
import hashlib
from datetime import datetime
import os
from typing import List, Dict, Optional
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OLXScraper:
    def __init__(self, base_url: str = "https://www.olx.pt/coracaodejesus/?search%5Bdist%5D=15"):
        self.base_url = base_url
        self.data_file = "data.json"
        self.last_scrape_time = None
        self.load_existing_data()
        self.setup_driver()

    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.wait = WebDriverWait(self.driver, 20)

    def load_existing_data(self):
        """Load existing listings from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.existing_listings = json.load(f)
            else:
                self.existing_listings = []
                self.save_data()
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
            self.existing_listings = []

    def save_data(self):
        """Save listings to JSON file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.existing_listings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def generate_listing_id(self, title: str, price: str) -> str:
        """Generate unique ID for a listing"""
        return hashlib.md5(f"{title}{price}".encode()).hexdigest()

    def wait_for_element(self, by: By, value: str, timeout: int = 10):
        """Wait for an element to be present and visible"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {value}")
            return None

    def parse_listing(self, element) -> Optional[Dict]:
        """Parse a single listing element using Selenium"""
        try:
            logger.debug(f"Parsing element HTML: {element.get_attribute('outerHTML')}")

            try:
                title_element = element.find_element(By.CSS_SELECTOR, 'h4.css-1g61gc2')
                title = title_element.text.strip()
                link_element = title_element.find_element(By.XPATH, './..') 
                link = link_element.get_attribute('href')
            except NoSuchElementException:
                logger.warning("Could not find title element")
                return None

            if not link or not title:
                logger.warning("Missing link or title")
                return None

            try:
                price_element = element.find_element(By.CSS_SELECTOR, 'p[data-testid="ad-price"]')
                price = price_element.text.strip()
            except NoSuchElementException:
                price = "Price not available"

            try:
                location_element = element.find_element(By.CSS_SELECTOR, 'p[data-testid="location-date"]')
                location_text = location_element.text.strip()
                if ' - ' in location_text:
                    location, date = location_text.split(' - ', 1)
                else:
                    location = location_text
                    date = "Unknown"
            except NoSuchElementException:
                location = "Location not available"
                date = "Unknown"

            try:
                image_element = element.find_element(By.CSS_SELECTOR, 'img.css-8wsg1m')
                image_url = image_element.get_attribute('src')
                if image_url == "/app/static/media/no_thumbnail.15f456ec5.svg":
                    image_url = None
            except NoSuchElementException:
                image_url = None

            listing_id = self.generate_listing_id(title, price)
            
            return {
                "id": listing_id,
                "title": title,
                "price": price,
                "location": location,
                "date": date,
                "link": link,
                "image_url": image_url,
                "scraped_at": datetime.now().isoformat(),
                "is_new": True,
                "seen": False
            }
        except StaleElementReferenceException:
            logger.warning("Element became stale, retrying...")
            return None
        except Exception as e:
            logger.error(f"Error parsing listing: {e}")
            return None

    def scrape_page(self, page: int = 1) -> List[Dict]:
        """Scrape a single page of listings using Selenium"""
        url = f"{self.base_url}&page={page}"
        
        try:
            logger.info(f"Scraping page {page}: {url}")
            self.driver.get(url)
            
            time.sleep(5)  
            
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-cy="l-card"]')))
            except TimeoutException:
                logger.warning("No listings found on page")
                return []

            listing_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-cy="l-card"]')
            
            if not listing_elements:
                logger.warning(f"No listings found on page {page}")
                return []

            logger.info(f"Found {len(listing_elements)} potential listings on page {page}")
            
            listings = []
            for element in listing_elements:
                listing = self.parse_listing(element)
                if listing:
                    listings.append(listing)
            
            logger.info(f"Successfully parsed {len(listings)} listings on page {page}")
            return listings
        except Exception as e:
            logger.error(f"Error scraping page {page}: {e}")
            return []

    def scrape(self, pages: int = 3) -> List[Dict]:
        """Scrape multiple pages and return new listings"""
        try:
            all_listings = []
            for page in range(1, pages + 1):
                listings = self.scrape_page(page)
                all_listings.extend(listings)
                if not listings: 
                    break
                time.sleep(3) 

            existing_ids = {listing['id'] for listing in self.existing_listings}
            new_listings = [listing for listing in all_listings if listing['id'] not in existing_ids]
            if new_listings:
          
                self.existing_listings.extend(new_listings)
                self.save_data()
                logger.info(f"Added {len(new_listings)} new listings")
            else:
                logger.info("No new listings found")

            self.last_scrape_time = datetime.now()
            return new_listings
        finally:
            self.driver.quit()  

    def mark_as_seen(self, listing_ids: List[str]):
        """Mark listings as seen"""
        for listing in self.existing_listings:
            if listing['id'] in listing_ids:
                listing['seen'] = True
        self.save_data()

    def get_unseen_listings(self) -> List[Dict]:
        """Get all unseen listings"""
        return [listing for listing in self.existing_listings if not listing.get('seen', False)]

    def export_to_csv(self, filename: str = "listings.csv", include_seen: bool = True):
        """Export listings to CSV file"""
        try:
            listings = self.existing_listings if include_seen else self.get_unseen_listings()
            if not listings:
                logger.warning("No listings to export")
                return

            df = pd.DataFrame(listings)
            columns = ['title', 'price', 'location', 'date', 'link', 'image_url', 'scraped_at', 'seen']
            df = df[columns]
            
            export_dir = Path("exports")
            export_dir.mkdir(exist_ok=True)
            
            filepath = export_dir / filename
            df.to_csv(filepath, index=False, encoding='utf-8')
            logger.info(f"Exported {len(listings)} listings to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")

    def export_to_excel(self, filename: str = "listings.xlsx", include_seen: bool = True):
        """Export listings to Excel file"""
        try:
            listings = self.existing_listings if include_seen else self.get_unseen_listings()
            if not listings:
                logger.warning("No listings to export")
                return

            df = pd.DataFrame(listings)
            columns = ['title', 'price', 'location', 'date', 'link', 'image_url', 'scraped_at', 'seen']
            df = df[columns]
            
            export_dir = Path("exports")
            export_dir.mkdir(exist_ok=True)
            
            filepath = export_dir / filename
            df.to_excel(filepath, index=False, engine='openpyxl')
            logger.info(f"Exported {len(listings)} listings to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")

if __name__ == "__main__":
    scraper = OLXScraper()
    new_listings = scraper.scrape()
    print(f"Found {len(new_listings)} new listings")
    
    scraper.export_to_csv()

    
    scraper.export_to_csv("unseen_listings.csv", include_seen=False)
