"""
Mural Arts Philadelphia Events Scraper
Fetches events from window.events JS variable embedded in the page HTML
"""

import requests
import re
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class MuralArtsScraper(BaseScraper):
    """Scrape events from Mural Arts Philadelphia via embedded JS variable"""

    URL = 'https://muralarts.org/events/'

    def __init__(self):
        super().__init__(
            source_name="Mural Arts Philadelphia",
            source_url="https://muralarts.org/events/"
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
            content = response.text

            # Extract window.events = [...] from the page JS
            match = re.search(r'window\.events\s*=\s*(\[.*?\]);', content, re.DOTALL)
            if not match:
                match = re.search(r'var events\s*=\s*(\[.*?\]);', content, re.DOTALL)

            if match:
                try:
                    raw_events = json.loads(match.group(1))
                    for item in raw_events:
                        event = self._parse_item(item)
                        if event:
                            events.append(event)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parse error for Mural Arts events: {e}")
            else:
                logger.warning("Mural Arts: window.events not found in page")

        except Exception as e:
            logger.error(f"Error scraping Mural Arts: {e}")

        logger.info(f"Mural Arts Philadelphia: {len(events)} events")
        return events

    def _parse_item(self, item: Dict) -> Optional[Dict]:
        try:
            title = item.get('title', '').strip()
            if not title:
                return None

            date_str = item.get('start', '') or item.get('date', '')
            start_date = self._parse_date(date_str)
            if not start_date or start_date < datetime.now():
                return None

            end_str = item.get('end', '')
            end_date = self._parse_date(end_str)

            time_str = item.get('time', '')
            if time_str and start_date.hour == 0:
                start_date = self._apply_time(start_date, time_str)

            event_url = item.get('url', self.URL)
            if event_url and not event_url.startswith('http'):
                event_url = 'https://muralarts.org' + event_url

            image_url = item.get('thumbnail', '') or item.get('image', '')

            return self.create_event(
                title=title,
                description='',
                start_date=start_date,
                end_date=end_date,
                location='Philadelphia, PA',
                category='artsAndCulture',
                source_url=event_url,
                image_url=str(image_url)
            )
        except Exception as e:
            logger.error(f"Error parsing Mural Arts item: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        date_str = str(date_str).strip()
        try:
            return datetime.strptime(date_str, '%m/%d/%Y')
        except ValueError:
            pass
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

    def _apply_time(self, dt: datetime, time_str: str) -> datetime:
        try:
            time_str = time_str.strip().lower().replace(' ', '')
            if 'am' in time_str or 'pm' in time_str:
                t = datetime.strptime(time_str, '%I:%M%p') if ':' in time_str else datetime.strptime(time_str, '%I%p')
                return dt.replace(hour=t.hour, minute=t.minute)
        except Exception:
            pass
        return dt
