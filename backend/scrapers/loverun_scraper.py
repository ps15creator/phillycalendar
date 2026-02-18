"""
Love Run Philadelphia Half Marathon + Broad Street Run Scraper
These are the two biggest Philadelphia running events, hosted on their own sites.
Also scrapes the Philadelphia Marathon site.
"""

import requests
import json
import logging
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class PhillyMajorRacesScraper(BaseScraper):
    """Scrape Philadelphia's major annual running races from their official sites"""

    RACE_SOURCES = [
        {
            'name': 'Broad Street Run',
            'url': 'https://www.broadstreetrun.com',
            'fallback_date_hint': 'May',
        },
        {
            'name': 'Love Run Philadelphia',
            'url': 'https://www.loverunphiladelphia.com',
            'fallback_date_hint': 'March',
        },
        {
            'name': 'Philadelphia Marathon',
            'url': 'https://www.philadelphiamarathon.com',
            'fallback_date_hint': 'November',
        },
        {
            'name': 'Philly 10K',
            'url': 'https://www.phillyruns.com',
            'fallback_date_hint': 'June',
        },
    ]

    def __init__(self):
        super().__init__(
            source_name="Philadelphia Major Races",
            source_url="https://www.broadstreetrun.com"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,*/*',
        }

    def scrape(self) -> List[Dict]:
        events = []
        seen = set()

        for race in self.RACE_SOURCES:
            try:
                ev = self._scrape_race_site(race, seen)
                if ev:
                    events.append(ev)
            except Exception as e:
                logger.error(f"Error scraping {race['name']}: {e}")

        logger.info(f"Philadelphia Major Races: {len(events)} events")
        return events

    def _scrape_race_site(self, race: dict, seen: set) -> Optional[Dict]:
        """Scrape a single race's official site for date/registration info"""
        try:
            resp = requests.get(race['url'], headers=self.headers, timeout=15)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.content, 'html.parser')
            race_name = race['name']

            if race_name in seen:
                return None

            start_date = None
            description = ''
            price = None
            source_url = race['url']

            # 1) Try JSON-LD first
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string or '')
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') == 'Event':
                            start_date = self._parse_date(item.get('startDate', ''))
                            description = item.get('description', '')[:400]
                            offers = item.get('offers', {})
                            if isinstance(offers, dict):
                                pv = offers.get('price', '')
                                price = 'Free' if pv in ('0', 0) else (f'${pv}' if pv else None)
                            loc_data = item.get('location', {})
                            if isinstance(loc_data, dict):
                                loc = loc_data.get('name', 'Philadelphia, PA')
                            else:
                                loc = 'Philadelphia, PA'
                            ev_url = item.get('url', source_url)
                            if start_date and start_date > datetime.now():
                                seen.add(race_name)
                                return self.create_event(
                                    title=race_name,
                                    description=description,
                                    start_date=start_date,
                                    location=loc,
                                    category='running',
                                    source_url=ev_url,
                                    price=price,
                                )
                except Exception:
                    continue

            # 2) Hunt for date patterns in page text
            if not start_date:
                text = soup.get_text(' ', strip=True)
                # Look for year-anchored patterns like "April 27, 2025" or "April 27, 2026"
                date_patterns = [
                    r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+20\d{2}',
                    r'\d{1,2}/\d{1,2}/20\d{2}',
                    r'20\d{2}-\d{2}-\d{2}',
                ]
                now = datetime.now()
                for pattern in date_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for m in matches:
                        try:
                            from dateutil import parser as du
                            dt = du.parse(m)
                            dt = dt.replace(tzinfo=None)
                            if dt > now and dt < now + timedelta(days=548):
                                start_date = dt
                                break
                        except Exception:
                            continue
                    if start_date:
                        break

            if not start_date:
                return None

            # Extract short description from meta or first paragraph
            meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            if meta_desc:
                description = (meta_desc.get('content') or '')[:400]
            if not description:
                p = soup.find('p')
                if p:
                    description = p.get_text(strip=True)[:300]

            seen.add(race_name)
            return self.create_event(
                title=race_name,
                description=description,
                start_date=start_date,
                location='Philadelphia, PA',
                category='running',
                source_url=source_url,
                price=price,
            )

        except Exception as e:
            logger.error(f"Error scraping {race['name']} at {race['url']}: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            clean = str(date_str).split('+')[0].split('Z')[0].strip()
            return datetime.fromisoformat(clean)
        except Exception:
            pass
        try:
            from dateutil import parser as du
            dt = du.parse(str(date_str))
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except Exception:
            return None
