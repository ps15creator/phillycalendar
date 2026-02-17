"""
Johnny Brenda's Philadelphia Events Scraper
Fetches real events from Johnny Brenda's static HTML (rhpSingleEvent cards)
"""

import requests
import re
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class JohnnyBrendasScraper(BaseScraper):
    """Scrape events from Johnny Brenda's Philadelphia"""

    URL = 'https://johnnybrendas.com/events'

    def __init__(self):
        super().__init__(
            source_name="Johnny Brenda's",
            source_url="https://johnnybrendas.com/events"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

    def scrape(self) -> List[Dict]:
        events = []
        try:
            response = requests.get(self.URL, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Events are in div.rhpSingleEvent cards
            cards = soup.find_all('div', class_='rhpSingleEvent')
            for card in cards:
                event = self._parse_card(card)
                if event:
                    events.append(event)

        except Exception as e:
            logger.error(f"Error scraping Johnny Brenda's: {e}")

        logger.info(f"Johnny Brenda's: {len(events)} events")
        return events

    def _parse_card(self, card) -> Optional[Dict]:
        try:
            # Title
            title_elem = card.find(class_='eventTitleDiv') or card.find(['h2', 'h3', 'h4'])
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)
            if not title:
                return None

            # Date
            date_elem = card.find(class_='singleEventDate') or card.find('time')
            date_str = ''
            if date_elem:
                date_str = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
            start_date = self._parse_date(date_str)
            if not start_date or start_date < datetime.now():
                return None

            # Link
            link = card.find('a', href=True)
            event_url = link['href'] if link else self.URL
            if event_url and not event_url.startswith('http'):
                event_url = 'https://johnnybrendas.com' + event_url

            # Price
            price_elem = card.find(class_='eventCost')
            price = price_elem.get_text(strip=True) if price_elem else None
            if price and price.lower() in ('free', '$0', '0'):
                price = 'Free'

            # Image
            img = card.find('img')
            image_url = img.get('src', '') if img else ''

            # Description
            desc_elem = card.find('p') or card.find(class_='eventDescription')
            description = desc_elem.get_text(strip=True)[:400] if desc_elem else ''

            return self.create_event(
                title=title,
                description=description,
                start_date=start_date,
                location="Johnny Brenda's, 1201 Frankford Ave, Philadelphia, PA",
                category='music',
                price=price,
                source_url=event_url,
                image_url=image_url
            )
        except Exception as e:
            logger.error(f"Error parsing Johnny Brenda's card: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        date_str = date_str.strip()
        try:
            return datetime.fromisoformat(date_str.split('+')[0].split('Z')[0])
        except Exception:
            try:
                from dateutil import parser
                return parser.parse(date_str)
            except Exception:
                return None
