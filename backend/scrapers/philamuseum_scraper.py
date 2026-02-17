"""
Philadelphia Museum of Art Events Scraper
Fetches real events via Sanity.io GROQ API (no auth required for published content)
"""

import requests
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote
from .base_scraper import BaseScraper

# Eastern time offset (UTC-5 standard, UTC-4 daylight)
# Python's datetime doesn't auto-detect DST for a naive target, so we use
# the zoneinfo module (Python 3.9+) for proper DST-aware conversion.
try:
    from zoneinfo import ZoneInfo
    _EASTERN = ZoneInfo('America/New_York')
except ImportError:
    _EASTERN = None

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
        # Use current UTC time as the cutoff so we match the Sanity UTC timestamps
        now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        # GROQ query: get events with upcoming active occurrences
        # Limit to next 3 occurrences per event to avoid flooding the calendar
        groq_query = f'''*[_type=="event"] {{
  title,
  "slug": slug.current,
  cardDescription,
  "upcomingOccurrences": occurrences[
    status=="active" && start >= "{now_utc}"
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

                # Deduplicate by title+full datetime (multiple time slots per day exist)
                key = f"{title}_{start_str[:16]}"
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
        """Parse a UTC ISO timestamp and convert to Eastern local time (naive datetime)."""
        if not date_str:
            return None
        try:
            # Sanity returns UTC timestamps like "2026-02-20T23:00:00.000Z"
            # Parse as UTC-aware datetime, then convert to Eastern
            clean = date_str.rstrip('Z')
            if '.' in clean:
                clean = clean.split('.')[0]  # strip milliseconds
            # Parse as UTC
            dt_utc = datetime.fromisoformat(clean).replace(tzinfo=timezone.utc)
            # Convert to Eastern time — try zoneinfo first (DST-aware), then dateutil, then fixed offset
            if _EASTERN:
                dt_eastern = dt_utc.astimezone(_EASTERN)
            else:
                try:
                    from dateutil import tz as dateutil_tz
                    eastern = dateutil_tz.gettz('America/New_York')
                    dt_eastern = dt_utc.astimezone(eastern)
                except Exception:
                    # Last resort: fixed UTC-5 (EST). May be 1hr off during EDT but better than UTC.
                    dt_eastern = dt_utc.astimezone(timezone(timedelta(hours=-5)))
            # Return as naive datetime (strip timezone info) — stored as Eastern time
            return dt_eastern.replace(tzinfo=None)
        except Exception as e:
            logger.debug(f"Date parse error for '{date_str}': {e}")
            return None
