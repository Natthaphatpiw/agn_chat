"""
Web scraper for AGN Health Q&A forums.
Scrapes medical Q&A threads and stores them in MongoDB.
"""
import logging
import time
import random
from typing import Optional, Dict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from pymongo import MongoClient, errors
from pymongo.errors import DuplicateKeyError

import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AGNHealthScraper:
    """Scraper for AGN Health Q&A forums."""

    def __init__(self):
        """Initialize the scraper with MongoDB connection and Selenium driver."""
        self.mongo_client = None
        self.db = None
        self.collection = None
        self.driver = None
        self._setup_mongodb()
        self._setup_selenium()

    def _setup_mongodb(self):
        """Set up MongoDB connection and ensure indexes."""
        try:
            self.mongo_client = MongoClient(config.MONGODB_URL)
            self.db = self.mongo_client[config.MONGODB_DATABASE]
            self.collection = self.db[config.MONGODB_COLLECTION]

            # Create unique index on thread_id to prevent duplicates
            self.collection.create_index("thread_id", unique=True)
            logger.info("MongoDB connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _setup_selenium(self):
        """Set up Selenium WebDriver with Chrome."""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            raise

    def scrape_thread(self, thread_id: int) -> Optional[Dict]:
        """
        Scrape a single Q&A thread.

        Args:
            thread_id: The thread ID to scrape

        Returns:
            Dictionary with scraped data or None if failed
        """
        url = f"{config.BASE_URL}/{thread_id}"

        try:
            logger.info(f"Scraping thread {thread_id}...")
            self.driver.get(url)

            # Wait for page to load (wait for the main content area)
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))

            # Small delay to ensure dynamic content loads
            time.sleep(1)

            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # Extract data using CSS selectors and fallback methods
            data = {
                'thread_id': thread_id,
                'date': self._extract_date(soup),
                'topic': self._extract_topic(soup),
                'question': self._extract_question(soup),
                'answer': self._extract_answer(soup)
            }

            # Validate that we have at least question or topic
            if not data['question'] and not data['topic']:
                logger.warning(f"Thread {thread_id}: No valid content found")
                return None

            logger.info(f"Thread {thread_id}: Successfully scraped")
            return data

        except TimeoutException:
            logger.warning(f"Thread {thread_id}: Timeout - page may not exist")
            return None
        except Exception as e:
            logger.error(f"Thread {thread_id}: Error during scraping - {e}")
            return None

    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract date from the page."""
        try:
            # Try multiple selectors
            date_elem = soup.select_one('time span.text-sm.text-gray-500')
            if date_elem:
                return date_elem.get_text(strip=True)

            # Fallback: look for any date-like text in time tags
            time_elem = soup.select_one('time')
            if time_elem:
                return time_elem.get_text(strip=True)

            return ""
        except Exception as e:
            logger.debug(f"Date extraction error: {e}")
            return ""

    def _extract_topic(self, soup: BeautifulSoup) -> str:
        """Extract topic from the page."""
        try:
            # Try multiple selectors
            topic_elem = soup.select_one('article p.font-bold')
            if topic_elem:
                return topic_elem.get_text(strip=True)

            # Fallback: look for any bold paragraph in article
            topic_elem = soup.select_one('article div.flex-col p')
            if topic_elem:
                return topic_elem.get_text(strip=True)

            return ""
        except Exception as e:
            logger.debug(f"Topic extraction error: {e}")
            return ""

    def _extract_question(self, soup: BeautifulSoup) -> str:
        """Extract question from the page."""
        try:
            # Try multiple selectors
            question_elem = soup.select_one('span.font-bold.text-lg')
            if question_elem:
                return question_elem.get_text(strip=True)

            # Fallback: look for question-like divs
            question_div = soup.select_one('div.rounded-2xl.border.border-blue-100 span')
            if question_div:
                return question_div.get_text(strip=True)

            # Another fallback: first section span
            section = soup.select_one('section.space-y-4 span.font-bold')
            if section:
                return section.get_text(strip=True)

            return ""
        except Exception as e:
            logger.debug(f"Question extraction error: {e}")
            return ""

    def _extract_answer(self, soup: BeautifulSoup) -> str:
        """Extract answer from the page (may include multiple paragraphs)."""
        try:
            answer_parts = []

            # Try to find answer in list items
            li_elements = soup.select('section.space-y-4 ul li p')
            if li_elements:
                for elem in li_elements:
                    text = elem.get_text(strip=True)
                    if text:
                        answer_parts.append(text)

            # Also check for direct paragraph answers
            if not answer_parts:
                p_elements = soup.select('section.space-y-4 p.mt-4')
                for elem in p_elements:
                    text = elem.get_text(strip=True)
                    if text:
                        answer_parts.append(text)

            # Fallback: any paragraph in the section
            if not answer_parts:
                p_elements = soup.select('section ul li p, section p')
                for elem in p_elements:
                    text = elem.get_text(strip=True)
                    # Filter out short or title-like text
                    if text and len(text) > 20:
                        answer_parts.append(text)

            return "\n\n".join(answer_parts) if answer_parts else ""
        except Exception as e:
            logger.debug(f"Answer extraction error: {e}")
            return ""

    def save_to_mongodb(self, data: Dict) -> bool:
        """
        Save scraped data to MongoDB.

        Args:
            data: Dictionary containing thread data

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            self.collection.insert_one(data)
            logger.info(f"Thread {data['thread_id']}: Saved to MongoDB")
            return True
        except DuplicateKeyError:
            logger.info(f"Thread {data['thread_id']}: Already exists in database, skipping")
            return False
        except Exception as e:
            logger.error(f"Thread {data['thread_id']}: Failed to save to MongoDB - {e}")
            return False

    def scrape_all(self, start_id: int = None, end_id: int = None):
        """
        Scrape all threads in the specified range.

        Args:
            start_id: Starting thread ID (default from config)
            end_id: Ending thread ID (default from config)
        """
        start_id = start_id or config.SCRAPER_START_ID
        end_id = end_id or config.SCRAPER_END_ID

        logger.info(f"Starting scraper for threads {start_id} to {end_id}")

        success_count = 0
        skip_count = 0
        error_count = 0

        for thread_id in range(start_id, end_id + 1):
            try:
                # Scrape the thread
                data = self.scrape_thread(thread_id)

                if data:
                    # Save to MongoDB
                    if self.save_to_mongodb(data):
                        success_count += 1
                    else:
                        skip_count += 1
                else:
                    error_count += 1

                # Add random delay to avoid rate limiting
                delay = random.uniform(config.SCRAPER_MIN_DELAY, config.SCRAPER_MAX_DELAY)
                time.sleep(delay)

                # Log progress every 50 threads
                if thread_id % 50 == 0:
                    logger.info(f"Progress: {thread_id}/{end_id} - Success: {success_count}, Skipped: {skip_count}, Errors: {error_count}")

            except KeyboardInterrupt:
                logger.info("Scraping interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error processing thread {thread_id}: {e}")
                error_count += 1
                continue

        logger.info(f"Scraping completed! Success: {success_count}, Skipped: {skip_count}, Errors: {error_count}")

    def close(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
            logger.info("Selenium driver closed")
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed")


def main():
    """Main function to run the scraper."""
    scraper = None
    try:
        scraper = AGNHealthScraper()
        scraper.scrape_all()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    main()
