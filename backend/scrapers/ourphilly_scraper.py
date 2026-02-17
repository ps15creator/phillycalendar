"""
OurPhilly.org Events Scraper
Fetches real events via OurPhilly's public Supabase REST API
360+ annual Philadelphia events including Penn Relays, ODUNDE, Flower Show, etc.
"""

import requests
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

SUPABASE_URL = 'https://qdartpzrxmftmaftfdbd.supabase.co/rest/v1/events'
SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFkYXJ0cHpyeG1mdG1hZnRmZGJkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDMxMDc3OTgsImV4cCI6MjA1ODY4Mzc5OH0.maFYGLz62w4n-BVERIvbxhIewzjPkkqJgXAn61FmIA8'


class OurPhillyScraper(BaseScraper):
    """Scrape events from OurPhilly.org via Supabase REST API"""

    def __init__(self):
        super().__init__(
            source_name="OurPhilly",
            source_url="https://ourphilly.org/events"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': f'Bearer {SUPABASE_ANON_KEY}',
            'Accept': 'application/json',
        }

    def scrape(self) -> List[Dict]:
        events = []
        today = datetime.now().strftime('%Y-%m-%d')
        try:
            response = requests.get(
                SUPABASE_URL,
                headers=self.headers,
                params={
                    'select': '*',
                    'Dates': f'gte.{today}',
                    'order': 'Dates.asc',
                    'limit': 200
                },
                timeout=15
            )
            response.raise_for_status()
            rows = response.json()

            for row in rows:
                event = self._parse_row(row)
                if event:
                    events.append(event)

        except Exception as e:
            logger.error(f"Error scraping OurPhilly: {e}")

        logger.info(f"OurPhilly: {len(events)} events")
        return events

    def _parse_row(self, row: Dict) -> Optional[Dict]:
        try:
            title = (row.get('E Name') or '').strip()
            if not title:
                return None

            date_str = row.get('Dates') or row.get('start_time') or ''
            start_date = self._parse_date(date_str)
            if not start_date or start_date < datetime.now():
                return None

            end_str = row.get('End Date') or ''
            end_date = self._parse_date(end_str)

            description = (
                row.get('E Description') or
                row.get('longDescription') or ''
            )
            if isinstance(description, list):
                description = ' '.join(str(d) for d in description)
            description = re.sub(r'<[^>]+>', ' ', str(description)).strip()[:500]

            location_parts = [
                row.get('address', ''),
                'Philadelphia, PA'
            ]
            location = ', '.join(p for p in location_parts if p) or 'Philadelphia, PA'

            image_url = row.get('E Image') or ''
            event_url = row.get('E Link') or row.get('slug') or self.source_url
            if event_url and not event_url.startswith('http'):
                event_url = f'https://ourphilly.org/events/{event_url}'

            # Category from Type field
            event_type = (row.get('Type') or '').lower()
            if any(w in event_type for w in ['music', 'concert', 'jazz']):
                category = 'music'
            elif any(w in event_type for w in ['food', 'drink', 'market', 'festival']):
                category = 'foodAndDrink'
            elif any(w in event_type for w in ['run', 'race', 'walk', 'sport']):
                category = 'running'
            elif any(w in event_type for w in ['art', 'culture', 'exhibit', 'museum']):
                category = 'artsAndCulture'
            else:
                category = 'community'

            return self.create_event(
                title=title,
                description=description,
                start_date=start_date,
                end_date=end_date,
                location=location,
                category=category,
                source_url=event_url,
                image_url=str(image_url)
            )
        except Exception as e:
            logger.error(f"Error parsing OurPhilly row: {e}")
            return None

    def _parse_date(self, date_str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            date_str = str(date_str)
            clean = date_str.split('+')[0].split('Z')[0]
            if 'T' in clean and len(clean) > 19:
                clean = clean[:19]
            return datetime.fromisoformat(clean)
        except Exception:
            try:
                from dateutil import parser as dp
                return dp.parse(str(date_str)).replace(tzinfo=None)
            except Exception:
                return None
