"""
MilkBoy Philadelphia Events Scraper
Fetches real events from MilkBoy using JSON-LD structured data
"""

import requests
import json
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class MilkBoyScraper(BaseScraper):
    """Scrape events from MilkBoy Philadelphia via JSON-LD"""

    URL = 'https://milkboyphilly.com/events'

    def __init__(self):
        super().__init__(
            source_name="MilkBoy Philadelphia",
            source_url="https://milkboyphilly.com/events"
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

            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') == 'Event':
                            event = self._parse_event(item)
                            if event:
                                events.append(event)
                except (json.JSONDecodeError, AttributeError):
                    continue

        except Exception as e:
            logger.error(f"Error scraping MilkBoy: {e}")

        logger.info(f"MilkBoy: {len(events)} events")
        return events

    def _parse_event(self, item: Dict) -> Optional[Dict]:
        try:
            title = item.get('name', '').strip()
            if not title:
                return None

            start_date = self._parse_date(item.get('startDate', ''))
            if not start_date or start_date < datetime.now():
                return None

            end_date = self._parse_date(item.get('endDate', ''))

            loc = item.get('location', {})
            if isinstance(loc, dict):
                location = loc.get('name', 'MilkBoy Philadelphia, 1100 Chestnut St, Philadelphia, PA')
            else:
                location = 'MilkBoy Philadelphia, 1100 Chestnut St, Philadelphia, PA'

            offers = item.get('offers', {})
            price = None
            if isinstance(offers, dict):
                pv = offers.get('price', '')
                price = 'Free' if pv in ('0', 0, '') else (f'${pv}' if pv else None)
            elif isinstance(offers, list) and offers:
                pv = offers[0].get('price', '')
                price = 'Free' if pv in ('0', 0) else (f'${pv}' if pv else None)

            image = item.get('image', '')
            if isinstance(image, dict):
                image = image.get('url', '')

            return self.create_event(
                title=title,
                description=item.get('description', '')[:500].strip(),
                start_date=start_date,
                end_date=end_date,
                location=location,
                category='music',
                price=price,
                source_url=item.get('url', self.URL),
                image_url=image
            )
        except Exception as e:
            logger.error(f"Error parsing MilkBoy event: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.split('+')[0].split('Z')[0])
        except Exception:
            try:
                from dateutil import parser
                return parser.parse(date_str)
            except Exception:
                return None
