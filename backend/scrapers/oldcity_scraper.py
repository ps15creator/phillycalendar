"""
Old City District Philadelphia Events Scraper
Fetches real events from oldcitydistrict.org (Drupal CMS)
"""

import requests
import re
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class OldCityScraper(BaseScraper):
    """Scrape events from Old City District Philadelphia"""

    URL = 'https://oldcitydistrict.org/things-do/upcoming-events'

    def __init__(self):
        super().__init__(
            source_name="Old City District",
            source_url="https://oldcitydistrict.org/things-do/upcoming-events"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

    def scrape(self) -> List[Dict]:
        events = []
        seen_urls = set()
        try:
            response = requests.get(self.URL, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Page uses <time datetime="ISO"> elements — pair each time with nearby title
            # Find all <time> elements with valid datetime
            time_elements = soup.find_all('time', datetime=True)

            for time_elem in time_elements:
                event = self._parse_time_elem(time_elem, seen_urls)
                if event:
                    events.append(event)

        except Exception as e:
            logger.error(f"Error scraping Old City District: {e}")

        logger.info(f"Old City District: {len(events)} events")
        return events

    def _parse_time_elem(self, time_elem, seen_urls: set) -> Optional[Dict]:
        try:
            date_str = time_elem.get('datetime', '')
            start_date = self._parse_date_str(date_str)
            if not start_date or start_date < datetime.now():
                return None

            # Walk up DOM to find the event container
            container = time_elem
            for _ in range(6):
                container = container.parent
                if not container:
                    break
                title_elem = container.find(['h2', 'h3', 'h4'])
                if title_elem:
                    break

            if not container:
                return None

            title_elem = container.find(['h2', 'h3', 'h4'])
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            if not title or len(title) < 4:
                return None

            # Find link
            link = container.find('a', href=True)
            event_url = link['href'] if link else self.URL
            if event_url and not event_url.startswith('http'):
                event_url = 'https://oldcitydistrict.org' + event_url

            if event_url in seen_urls:
                return None
            seen_urls.add(event_url)

            # Image
            img = container.find('img')
            image_url = img.get('src', '') if img else ''

            # Description
            desc_elem = container.find('p')
            description = desc_elem.get_text(strip=True)[:400] if desc_elem else ''

            # Category from title keywords
            title_lower = title.lower()
            if any(w in title_lower for w in ['run', 'walk', 'race', 'fitness']):
                category = 'running'
            elif any(w in title_lower for w in ['food', 'drink', 'dinner', 'brunch', 'market']):
                category = 'foodAndDrink'
            elif any(w in title_lower for w in ['art', 'music', 'jazz', 'gallery', 'exhibit']):
                category = 'artsAndCulture'
            else:
                category = 'community'

            return self.create_event(
                title=title,
                description=description,
                start_date=start_date,
                location='Old City, Philadelphia, PA',
                category=category,
                source_url=event_url,
                image_url=image_url
            )
        except Exception as e:
            logger.error(f"Error parsing Old City time elem: {e}")
            return None

    def _parse_date_str(self, date_str: str) -> Optional[datetime]:
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
                return dp.parse(date_str).replace(tzinfo=None)
            except Exception:
                return None
