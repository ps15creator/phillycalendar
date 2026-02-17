"""
Base scraper class for Philadelphia event sources.
All specific scrapers inherit from this class.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for all event scrapers"""

    def __init__(self, source_name: str, source_url: str):
        self.source_name = source_name
        self.source_url = source_url
        self.headers = {
            'User-Agent': 'PhillyCalendarBot/1.0 (Educational Project)'
        }

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def scrape(self) -> List[Dict]:
        """
        Main scraping method. Override this in subclasses.
        Returns list of event dictionaries.
        """
        raise NotImplementedError("Subclasses must implement scrape()")

    def parse_date(self, date_string: str) -> Optional[datetime]:
        """Parse various date formats"""
        from dateutil import parser
        try:
            return parser.parse(date_string)
        except Exception as e:
            logger.error(f"Error parsing date '{date_string}': {e}")
            return None

    def create_event(
        self,
        title: str,
        description: str,
        start_date: datetime,
        location: str,
        category: str,
        end_date: Optional[datetime] = None,
        price: Optional[str] = None,
        image_url: Optional[str] = None,
        source_url: Optional[str] = None
    ) -> Dict:
        """Create standardized event dictionary"""
        return {
            'title': title.strip(),
            'description': description.strip(),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat() if end_date else None,
            'location': location.strip(),
            'category': category,
            'source': self.source_name,
            'source_url': source_url or self.source_url,
            'image_url': image_url,
            'price': price,
            'is_manually_added': False
        }

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return ' '.join(text.strip().split())
