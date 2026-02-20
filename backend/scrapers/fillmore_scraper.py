"""
The Fillmore Philadelphia Events Scraper
Fetches real events from The Fillmore /shows page via JSON parsing
"""

import requests
import json
import re
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class FillmoreScraper(BaseScraper):
    """Scrape events from The Fillmore Philadelphia"""

    URL = 'https://www.thefillmorephilly.com/shows'

    def __init__(self):
        super().__init__(
            source_name="The Fillmore Philadelphia",
            source_url="https://www.thefillmorephilly.com/shows"
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

            # Try JSON-LD first
            soup = BeautifulSoup(content, 'html.parser')
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') == 'Event':
                            event = self._parse_jsonld(item)
                            if event:
                                events.append(event)
                except (json.JSONDecodeError, AttributeError):
                    continue

            # If no JSON-LD events, extract from Next.js RSC payload using regex
            if not events:
                events = self._parse_nextjs_payload(content)

        except Exception as e:
            logger.error(f"Error scraping Fillmore: {e}")

        logger.info(f"Fillmore: {len(events)} events")
        return events

    def _parse_jsonld(self, item: Dict) -> Optional[Dict]:
        try:
            title = item.get('name', '').strip()
            if not title:
                return None
            start_date = self._parse_date(item.get('startDate', ''))
            if not start_date or start_date < datetime.now():
                return None
            end_date = self._parse_date(item.get('endDate', ''))

            loc = item.get('location', {})
            location = loc.get('name', 'The Fillmore Philadelphia, 29 E Allen St, Philadelphia, PA') if isinstance(loc, dict) else 'The Fillmore Philadelphia, 29 E Allen St, Philadelphia, PA'

            offers = item.get('offers', {})
            price = None
            if isinstance(offers, dict):
                pv = offers.get('price', '')
                price = 'Free' if pv in ('0', 0, '') else (f'${pv}' if pv else None)

            return self.create_event(
                title=title,
                description=item.get('description', '')[:500].strip(),
                start_date=start_date,
                end_date=end_date,
                location=location,
                category='music',
                price=price,
                source_url=item.get('url', self.URL),
                image_url=item.get('image', '') if isinstance(item.get('image'), str) else ''
            )
        except Exception as e:
            logger.error(f"Error parsing Fillmore JSON-LD event: {e}")
            return None

    def _parse_nextjs_payload(self, content: str) -> List[Dict]:
        """Extract events from Next.js RSC stream payload using regex"""
        events = []
        seen = set()

        # Look for name+startDate pairs in the RSC payload
        # Pattern: "name":"Show Title" ... "startDate":"2026-..."
        name_pattern = re.compile(r'"name"\s*:\s*"([^"]{3,100})"')
        date_pattern = re.compile(r'"startDate"\s*:\s*"(\d{4}-\d{2}-\d{2}T[^"]+)"')
        url_pattern = re.compile(r'"url"\s*:\s*"(https://www\.thefillmorephilly\.com/[^"]+)"')

        names = name_pattern.findall(content)
        dates = date_pattern.findall(content)
        urls = url_pattern.findall(content)

        # Pair names with dates (they appear in sequence in RSC stream)
        # Find positions to match them
        name_positions = [(m.start(), m.group(1)) for m in name_pattern.finditer(content)]
        date_positions = [(m.start(), m.group(1)) for m in date_pattern.finditer(content)]
        url_positions = [(m.start(), m.group(1)) for m in url_pattern.finditer(content)]

        # Names to skip — venue/site names that are not actual event titles
        VENUE_NAMES = {'The Fillmore Philadelphia', 'Fillmore Philadelphia', 'The Fillmore'}

        for name_pos, name in name_positions:
            if name in VENUE_NAMES:
                continue

            # Find closest date after this name
            closest_date = None
            closest_date_dist = float('inf')
            for date_pos, date_str in date_positions:
                dist = abs(date_pos - name_pos)
                if dist < closest_date_dist and dist < 2000:
                    closest_date_dist = dist
                    closest_date = date_str

            if not closest_date:
                continue

            start_date = self._parse_date(closest_date)
            if not start_date or start_date < datetime.now():
                continue

            if name in seen:
                continue
            seen.add(name)

            # Find closest URL
            event_url = self.URL
            for url_pos, url in url_positions:
                if abs(url_pos - name_pos) < 2000:
                    event_url = url
                    break

            events.append(self.create_event(
                title=name,
                description='',
                start_date=start_date,
                location='The Fillmore Philadelphia, 29 E Allen St, Philadelphia, PA',
                category='music',
                source_url=event_url
            ))

        return events

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            # Strip timezone info to get naive datetime
            clean = date_str.split('+')[0].split('-0')[0].split('Z')[0]
            # Handle negative UTC offsets like 2026-02-17T20:00:00-05:00
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
