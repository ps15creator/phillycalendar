"""
Reading Terminal Market Philadelphia Events Scraper
Fetches real events using JSON-LD structured data
"""

import requests
import json
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ReadingTerminalScraper(BaseScraper):
    """Scrape events from Reading Terminal Market"""

    URL = 'https://www.readingterminalmarket.org/events/'

    def __init__(self):
        super().__init__(
            source_name="Reading Terminal Market",
            source_url="https://www.readingterminalmarket.org/events/"
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

            # Fallback: HTML event cards (The Events Calendar plugin)
            if not events:
                events = self._parse_html(soup)

        except Exception as e:
            logger.error(f"Error scraping Reading Terminal Market: {e}")

        logger.info(f"Reading Terminal Market: {len(events)} events")
        return events

    # Titles that are NOT real events — RTM misuses the events plugin for these pages
    SKIP_TITLES = {
        'gift cards', 'gift card', 'become an ambassador', 'ambassador',
        'vendor application', 'vendor app', 'newsletter', 'subscribe',
        'contact us', 'about', 'parking', 'directions', 'hours',
    }

    # Skip events more than ~18 months in the future — these are usually permanent pages
    MAX_MONTHS_AHEAD = 18

    def _parse_event(self, item: Dict) -> Optional[Dict]:
        try:
            title = item.get('name', '').strip()
            if not title:
                return None

            # Skip known non-event promotional pages
            if title.lower() in self.SKIP_TITLES:
                return None

            start_date = self._parse_date(item.get('startDate', ''))
            if not start_date or start_date < datetime.now():
                return None

            # Skip events suspiciously far in the future (permanent promo pages)
            from datetime import timedelta
            max_future = datetime.now() + timedelta(days=self.MAX_MONTHS_AHEAD * 30)
            if start_date > max_future:
                return None

            end_date = self._parse_date(item.get('endDate', ''))

            loc = item.get('location', {})
            location = 'Reading Terminal Market, 51 N 12th St, Philadelphia, PA'
            if isinstance(loc, dict):
                name = loc.get('name', '')
                if name and 'Reading Terminal' not in name:
                    location = f'{name}, 51 N 12th St, Philadelphia, PA'

            image = item.get('image', '')
            if isinstance(image, dict):
                image = image.get('url', '')

            return self.create_event(
                title=title,
                description=item.get('description', '')[:500].strip(),
                start_date=start_date,
                end_date=end_date,
                location=location,
                category='community',
                price=None,
                source_url=item.get('url', self.URL),
                image_url=image
            )
        except Exception as e:
            logger.error(f"Error parsing Reading Terminal event: {e}")
            return None

    def _parse_html(self, soup) -> List[Dict]:
        events = []
        cards = soup.find_all('article', class_=lambda c: c and 'tribe' in str(c).lower())
        cards = cards or soup.find_all('div', class_=lambda c: c and 'tribe-event' in str(c).lower())

        for card in cards[:20]:
            try:
                title_elem = card.find(['h2', 'h3'])
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                time_elem = card.find('time')
                date_str = time_elem.get('datetime', '') if time_elem else ''
                start_date = self._parse_date(date_str)
                if not start_date or start_date < datetime.now():
                    continue

                link = card.find('a', href=True)
                event_url = link['href'] if link else self.URL

                events.append(self.create_event(
                    title=title,
                    description='',
                    start_date=start_date,
                    location='Reading Terminal Market, 51 N 12th St, Philadelphia, PA',
                    category='community',
                    source_url=event_url
                ))
            except Exception as e:
                logger.error(f"Error parsing Reading Terminal HTML card: {e}")

        return events

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            clean = date_str.split('+')[0].split('Z')[0]
            if 'T' in clean and len(clean) > 19:
                clean = clean[:19]
            return datetime.fromisoformat(clean)
        except Exception:
            try:
                from dateutil import parser as dp
                dt = dp.parse(date_str)
                return dt.replace(tzinfo=None)
            except Exception:
                return None
