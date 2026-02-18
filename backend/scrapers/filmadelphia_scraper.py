"""
Filmadelphia (Philadelphia Film Society) & Philadelphia Film Events Scraper

filmadelphia.org blocks all automated requests (403 Forbidden). The Philadelphia
Film Society does not currently list upcoming events on their Eventbrite organizer
page for regular showtimes.

This scraper instead fetches Philadelphia film events from Eventbrite's dedicated
film category pages (which include screenings, premieres, film festivals, and
cinema events from many Philadelphia venues and organizations).
"""

import requests
import json
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

# Eventbrite organizer page for Philadelphia Film Society (used as fallback)
PFS_EVENTBRITE_URL = 'https://www.eventbrite.com/o/philadelphia-film-society-73119306203'

# Eventbrite film category pages for Philadelphia (primary source)
FILM_SEARCH_URLS = [
    'https://www.eventbrite.com/d/pa--philadelphia/film/',
    'https://www.eventbrite.com/d/pa--philadelphia/film--screening/',
]


class FilmadelphiaScraper(BaseScraper):
    """
    Scrape Philadelphia film events from Eventbrite.
    Includes screenings, premieres, festivals, and film-related events
    from venues across the city.
    """

    def __init__(self):
        super().__init__(
            source_name="Philadelphia Film Events",
            source_url="https://filmadelphia.org/events/"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    def scrape(self) -> List[Dict]:
        events = []
        seen = set()

        # 1. Try the PFS Eventbrite organizer page for PFS-specific events
        org_events = self._scrape_eventbrite_organizer(seen)
        events.extend(org_events)

        # 2. Scrape Eventbrite film category pages for broader Philadelphia film events
        for url in FILM_SEARCH_URLS:
            search_events = self._scrape_eventbrite_film_page(url, seen)
            events.extend(search_events)

        logger.info(f"Philadelphia Film Events: {len(events)} events")
        return events

    def _scrape_eventbrite_organizer(self, seen: set) -> List[Dict]:
        """Scrape events directly from the PFS Eventbrite organizer page"""
        events = []
        try:
            response = requests.get(
                PFS_EVENTBRITE_URL,
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for JSON-LD structured data
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string or '')
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') in ('Event', 'ScreeningEvent', 'MusicEvent'):
                            event = self._parse_ld_event(item, seen)
                            if event:
                                events.append(event)
                        elif item.get('@type') == 'ItemList':
                            for elem in item.get('itemListElement', []):
                                ev = elem.get('item', elem)
                                if ev.get('@type') in ('Event', 'ScreeningEvent'):
                                    event = self._parse_ld_event(ev, seen)
                                    if event:
                                        events.append(event)
                except (json.JSONDecodeError, AttributeError):
                    continue

            # Also look for embedded __SERVER_DATA__ JSON (Eventbrite embeds data here)
            for script in soup.find_all('script'):
                text = script.string or ''
                if '__SERVER_DATA__' in text or 'window.__SERVER_DATA__' in text:
                    extra = self._parse_server_data(text, seen)
                    events.extend(extra)
                    break

        except Exception as e:
            logger.warning(f"Could not scrape PFS Eventbrite organizer page: {e}")

        return events

    def _parse_server_data(self, script_text: str, seen: set) -> List[Dict]:
        """Try to extract events from Eventbrite's window.__SERVER_DATA__ JS object"""
        events = []
        try:
            # Find the JSON object assigned to __SERVER_DATA__
            import re
            match = re.search(r'__SERVER_DATA__\s*=\s*(\{.*?\});?\s*(?:window\.|var\s|$)', script_text, re.DOTALL)
            if not match:
                return []
            data = json.loads(match.group(1))

            # Eventbrite's server data nests events under various keys
            # Try common paths
            def find_events(obj, depth=0):
                if depth > 8 or not isinstance(obj, (dict, list)):
                    return []
                found = []
                if isinstance(obj, list):
                    for item in obj:
                        found.extend(find_events(item, depth + 1))
                elif isinstance(obj, dict):
                    if obj.get('type') == 'Event' or ('start_date' in obj and 'name' in obj):
                        found.append(obj)
                    for v in obj.values():
                        found.extend(find_events(v, depth + 1))
                return found

            raw_events = find_events(data)
            for raw in raw_events:
                title = raw.get('name', {})
                if isinstance(title, dict):
                    title = title.get('text', '')
                title = str(title).strip()
                if not title or title in seen:
                    continue

                start = raw.get('start', {})
                if isinstance(start, dict):
                    start_str = start.get('local', start.get('utc', ''))
                else:
                    start_str = str(start)

                start_date = self._parse_date(start_str)
                if not start_date or start_date < datetime.now():
                    continue

                seen.add(title)

                event = self.create_event(
                    title=title,
                    description='',
                    start_date=start_date,
                    location='Philadelphia Film Society, Philadelphia, PA',
                    category='artsAndCulture',
                    source_url=raw.get('url', PFS_EVENTBRITE_URL),
                )
                events.append(event)

        except Exception as e:
            logger.debug(f"Server data parse error: {e}")

        return events

    def _scrape_eventbrite_film_page(self, url: str, seen: set) -> List[Dict]:
        """Scrape Eventbrite film category page for Philadelphia film events"""
        events = []
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string or '')
                    if isinstance(data, dict):
                        item_list = data.get('itemListElement', [])
                    elif isinstance(data, list):
                        item_list = data
                    else:
                        continue

                    for item in item_list:
                        # Eventbrite wraps each event in {'item': {...}}
                        ev = item.get('item', item) if isinstance(item, dict) else {}
                        if not isinstance(ev, dict):
                            continue

                        # Only include PA events
                        loc = ev.get('location', {})
                        if isinstance(loc, dict):
                            addr = loc.get('address', {})
                            if isinstance(addr, dict):
                                state = addr.get('addressRegion', 'PA').upper()
                                if state and state not in ('PA', 'PENNSYLVANIA'):
                                    continue

                        event = self._parse_ld_event(ev, seen)
                        if event:
                            events.append(event)
                except (json.JSONDecodeError, AttributeError):
                    continue

        except Exception as e:
            logger.debug(f"Eventbrite film page error ({url}): {e}")

        return events

    def _parse_ld_event(self, ev: dict, seen: set) -> Optional[Dict]:
        """Parse a JSON-LD event dict into a standardized event"""
        try:
            title = ev.get('name', '').strip()
            if not title or title in seen:
                return None

            start_str = ev.get('startDate', '')
            start_date = self._parse_date(start_str)
            if not start_date or start_date < datetime.now():
                return None

            seen.add(title)

            end_date = self._parse_date(ev.get('endDate', ''))

            # Location
            loc = ev.get('location', {})
            if isinstance(loc, dict):
                venue = loc.get('name', 'Philadelphia Film Society')
                addr = loc.get('address', {})
                if isinstance(addr, dict):
                    street = addr.get('streetAddress', '')
                    city = addr.get('addressLocality', 'Philadelphia')
                    state = addr.get('addressRegion', 'PA')
                    if state and state.upper() not in ('PA', 'PENNSYLVANIA'):
                        return None
                    location = ', '.join(p for p in [venue, street, city, state] if p)
                else:
                    location = f"{venue}, Philadelphia, PA"
            else:
                location = 'Philadelphia Film Society, Philadelphia, PA'

            # Price
            offers = ev.get('offers', {})
            price = None
            if isinstance(offers, dict):
                pv = offers.get('price', '')
                price = 'Free' if pv in ('0', 0, '') else (f"${pv}" if pv else None)
            elif isinstance(offers, list) and offers:
                pv = offers[0].get('price', '')
                price = 'Free' if pv in ('0', 0) else (f"${pv}" if pv else None)

            description = ev.get('description', '')[:500].strip()
            event_url = ev.get('url', PFS_EVENTBRITE_URL)

            return self.create_event(
                title=title,
                description=description,
                start_date=start_date,
                end_date=end_date,
                location=location,
                category='artsAndCulture',
                source_url=event_url,
                price=price,
            )
        except Exception as e:
            logger.error(f"Error parsing PFS event: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse ISO or human-readable date string"""
        if not date_str:
            return None
        try:
            # ISO format: "2026-03-15T19:30:00"
            if 'T' in date_str:
                clean = date_str.split('+')[0].split('Z')[0]
                return datetime.fromisoformat(clean)
            return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            try:
                from dateutil import parser as du
                dt = du.parse(date_str)
                return dt.replace(tzinfo=None) if dt.tzinfo else dt
            except Exception:
                return None
