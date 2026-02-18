"""
Active.com Philadelphia Running Events Scraper
Fetches running races and fitness events in the Philadelphia area
via the Active.com search API (JSON endpoint).
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Active.com search API — returns JSON with event listings
ACTIVE_API = 'https://www.active.com/api/search'

# Fallback: Active search page for scraping if API changes
ACTIVE_SEARCH_URL = 'https://www.active.com/philadelphia-pa/running/races'


class ActiveScraper(BaseScraper):
    """Scrape Philadelphia running events from Active.com"""

    def __init__(self):
        super().__init__(
            source_name="Active.com",
            source_url=ACTIVE_SEARCH_URL
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    def scrape(self) -> List[Dict]:
        events = []
        seen = set()

        today = datetime.now()
        end_date = today + timedelta(days=548)

        # Active.com uses a REST search endpoint
        params = {
            'query': 'running race philadelphia',
            'location': 'Philadelphia, PA',
            'lat': '39.9526',
            'lng': '-75.1652',
            'radius': '25',            # 25-mile radius around Philly
            'category': 'running',
            'startDate': today.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'pageSize': 50,
            'pageNum': 1,
        }

        try:
            resp = requests.get(ACTIVE_API, headers=self.headers, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results', data.get('data', data.get('items', [])))
                for item in results:
                    event = self._parse_active_event(item, seen)
                    if event:
                        events.append(event)
        except Exception as e:
            logger.warning(f"Active.com API failed ({e}), trying HTML fallback")

        # HTML fallback — scrape the search results page with JSON-LD
        if not events:
            events = self._scrape_html(seen)

        logger.info(f"Active.com: {len(events)} events")
        return events

    def _scrape_html(self, seen: set) -> List[Dict]:
        """HTML fallback: scrape Active.com search results page"""
        import json
        from bs4 import BeautifulSoup

        events = []
        urls = [
            'https://www.active.com/philadelphia-pa/running/races',
            'https://www.active.com/local/philadelphia-pa/running',
        ]

        for url in urls:
            try:
                resp = requests.get(url, headers=self.headers, timeout=15)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.content, 'html.parser')

                # Try JSON-LD
                for script in soup.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(script.string or '')
                        if isinstance(data, list):
                            items = data
                        elif data.get('@type') == 'ItemList':
                            items = [i.get('item', i) for i in data.get('itemListElement', [])]
                        elif data.get('@type') == 'Event':
                            items = [data]
                        else:
                            items = []
                        for item in items:
                            ev = self._parse_jsonld(item, seen)
                            if ev:
                                events.append(ev)
                    except Exception:
                        continue

                # Try __NEXT_DATA__ or window.__data
                for script in soup.find_all('script'):
                    txt = script.string or ''
                    if '"events"' in txt or '"races"' in txt:
                        try:
                            # Find JSON blob
                            import re
                            match = re.search(r'\{.*"events"\s*:\s*\[.*?\]\s*\}', txt, re.DOTALL)
                            if match:
                                blob = json.loads(match.group(0))
                                for item in blob.get('events', []):
                                    ev = self._parse_active_event(item, seen)
                                    if ev:
                                        events.append(ev)
                        except Exception:
                            pass

                if events:
                    break
            except Exception as e:
                logger.error(f"Active.com HTML scrape failed for {url}: {e}")

        return events

    def _parse_active_event(self, item: dict, seen: set) -> Optional[Dict]:
        """Parse an event dict from Active.com API response"""
        try:
            title = (item.get('title') or item.get('name') or '').strip()
            if not title:
                return None

            # Deduplicate
            key = title.lower()
            if key in seen:
                return None

            # Parse date
            start_str = (
                item.get('startDate') or item.get('start_date') or
                item.get('activityStartDate') or item.get('date') or ''
            )
            start_date = self._parse_date(start_str)
            if not start_date or start_date < datetime.now():
                return None

            # Skip if > 18 months out (sanity cap)
            if start_date > datetime.now() + timedelta(days=548):
                return None

            seen.add(key)

            location = (
                item.get('location') or item.get('city') or
                item.get('place', {}).get('name', '') or 'Philadelphia, PA'
            )
            if isinstance(location, dict):
                location = location.get('name', 'Philadelphia, PA')

            description = (item.get('description') or item.get('body') or '')[:500].strip()
            url = item.get('url') or item.get('assetGuid') or self.source_url
            if url and not url.startswith('http'):
                url = 'https://www.active.com' + url

            price_raw = item.get('price') or item.get('minPrice') or ''
            price = None
            if price_raw:
                try:
                    p = float(str(price_raw).replace('$', '').replace(',', ''))
                    price = 'Free' if p == 0 else f'${p:.2f}'
                except Exception:
                    price = str(price_raw)

            return self.create_event(
                title=title,
                description=description,
                start_date=start_date,
                location=str(location),
                category='running',
                source_url=str(url),
                price=price,
            )
        except Exception as e:
            logger.error(f"Active.com parse error: {e}")
            return None

    def _parse_jsonld(self, item: dict, seen: set) -> Optional[Dict]:
        """Parse a JSON-LD Event item"""
        try:
            if item.get('@type') not in ('Event', None, ''):
                if item.get('@type') and item['@type'] != 'Event':
                    return None

            title = item.get('name', '').strip()
            if not title:
                return None

            key = title.lower()
            if key in seen:
                return None

            start_date = self._parse_date(item.get('startDate', ''))
            if not start_date or start_date < datetime.now():
                return None
            if start_date > datetime.now() + timedelta(days=548):
                return None

            seen.add(key)

            loc = item.get('location', {})
            if isinstance(loc, dict):
                location = loc.get('name', '') or loc.get('address', {}).get('addressLocality', 'Philadelphia, PA')
            else:
                location = str(loc) or 'Philadelphia, PA'

            offers = item.get('offers', {})
            price = None
            if isinstance(offers, dict):
                pv = offers.get('price', '')
                price = 'Free' if pv in ('0', 0, '') else (f'${pv}' if pv else None)

            return self.create_event(
                title=title,
                description=item.get('description', '')[:500].strip(),
                start_date=start_date,
                location=location,
                category='running',
                source_url=item.get('url', self.source_url),
                price=price,
            )
        except Exception as e:
            logger.error(f"Active.com JSON-LD parse error: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        date_str = str(date_str).strip()
        formats = [
            '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M',
            '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
            '%Y-%m-%d', '%m/%d/%Y',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str[:len(fmt) + 2].strip(), fmt)
            except ValueError:
                continue
        try:
            # Strip timezone suffix and try ISO parse
            clean = date_str.split('+')[0].split('Z')[0].strip()
            return datetime.fromisoformat(clean)
        except Exception:
            pass
        try:
            from dateutil import parser as du
            dt = du.parse(date_str)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except Exception:
            return None
