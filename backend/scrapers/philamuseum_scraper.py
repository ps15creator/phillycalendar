"""
Philadelphia Museum of Art Events Scraper
Fetches real events via Sanity.io GROQ API (no auth required for published content)
"""

import requests
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import quote
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

SANITY_PROJECT = 'r7hgx2l2'
SANITY_DATASET = 'production'
SANITY_API_URL = f'https://{SANITY_PROJECT}.api.sanity.io/v2021-10-21/data/query/{SANITY_DATASET}'


class PhilaMuseumScraper(BaseScraper):
    """Scrape events from Philadelphia Museum of Art via Sanity GROQ API"""

    def __init__(self):
        super().__init__(
            source_name="Philadelphia Museum of Art",
            source_url="https://philamuseum.org/events"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
        }

    def scrape(self) -> List[Dict]:
        events = []
        today = datetime.now().strftime('%Y-%m-%dT00:00:00Z')

        # GROQ query: get events with upcoming active occurrences
        groq_query = f'''*[_type=="event"] {{
  title,
  "slug": slug.current,
  cardDescription,
  "upcomingOccurrences": occurrences[
    status=="active" && start >= "{today}"
  ] | order(start asc) [0..5] {{start, end, status}}
}} [defined(upcomingOccurrences) && count(upcomingOccurrences) > 0]
| order(upcomingOccurrences[0].start asc) [0..100]'''

        try:
            response = requests.get(
                SANITY_API_URL,
                headers=self.headers,
                params={'query': groq_query},
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            results = data.get('result', [])

            seen = set()
            for item in results:
                parsed = self._parse_item(item, seen)
                events.extend(parsed)

        except Exception as e:
            logger.error(f"Error scraping Philadelphia Museum of Art: {e}")

        logger.info(f"Philadelphia Museum of Art: {len(events)} events")
        return events

    def _parse_item(self, item: Dict, seen: set) -> List[Dict]:
        """One item can have multiple occurrences — create one event per occurrence"""
        results = []
        try:
            title = item.get('title', '').strip()
            if not title:
                return []

            slug = item.get('slug', '')
            event_url = f'https://philamuseum.org/events/{slug}' if slug else self.source_url
            description = item.get('cardDescription', '')
            if isinstance(description, list):
                description = ' '.join(str(d) for d in description)
            description = str(description).strip()[:500]

            occurrences = item.get('upcomingOccurrences', [])
            for occ in occurrences:
                start_str = occ.get('start', '')
                start_date = self._parse_date(start_str)
                if not start_date or start_date < datetime.now():
                    continue

                # Deduplicate by title+date
                key = f"{title}_{start_str[:10]}"
                if key in seen:
                    continue
                seen.add(key)

                end_date = self._parse_date(occ.get('end', ''))

                results.append(self.create_event(
                    title=title,
                    description=description,
                    start_date=start_date,
                    end_date=end_date,
                    location='Philadelphia Museum of Art, 2600 Benjamin Franklin Pkwy, Philadelphia, PA',
                    category='artsAndCulture',
                    source_url=event_url,
                ))

        except Exception as e:
            logger.error(f"Error parsing PMA item: {e}")

        return results

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
                return dp.parse(date_str).replace(tzinfo=None)
            except Exception:
                return None
