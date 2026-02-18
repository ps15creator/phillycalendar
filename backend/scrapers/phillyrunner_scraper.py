"""
Philadelphia Runner Events Scraper
Fetches Philadelphia Runner-sponsored races from their PR Races page
and linked RunSignUp/external race registration pages.
Philadelphia Runner is a local running store that organizes several
signature Philadelphia races each year.
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

# Philadelphia Runner's known sponsored races with their RunSignUp or external pages
# These are stable annual races — we fetch live data from their registration pages
PR_RACES = [
    {
        'name': 'Cold Hearts 5K',
        'runsignup_url': 'https://runsignup.com/Race/PA/Philadelphia/ColdHearts5K',
        'info_url': 'https://www.philadelphiarunner.com/content/pr-races',
    },
    {
        'name': 'Philly Run Fest',
        'runsignup_url': 'https://runsignup.com/Race/PA/Philadelphia/PhillyRunFest',
        'info_url': 'https://www.phillyrunfest.com/',
    },
    {
        'name': 'The Philly 10K',
        'runsignup_url': 'https://runsignup.com/Race/PA/Philadelphia/ThePhilly10K',
        'info_url': 'https://www.thephilly10k.com/',
    },
    {
        'name': 'Philadelphia Distance Run',
        'runsignup_url': 'https://runsignup.com/Race/PA/Philadelphia/PhiladelphiaDistanceRun',
        'info_url': 'https://www.philadelphiadistancerun.com/',
    },
]

RUNSIGNUP_RACE_API = 'https://runsignup.com/rest/race/{race_id}'
RUNSIGNUP_SEARCH_API = 'https://runsignup.com/rest/races'


class PhillyRunnerScraper(BaseScraper):
    """Scrape Philadelphia Runner-sponsored races"""

    def __init__(self):
        super().__init__(
            source_name="Philadelphia Runner",
            source_url="https://www.philadelphiarunner.com/content/pr-races"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/html,*/*',
        }

    def scrape(self) -> List[Dict]:
        events = []
        seen = set()

        for race_def in PR_RACES:
            try:
                race_events = self._fetch_race_from_runsignup(race_def, seen)
                if race_events:
                    events.extend(race_events)
                else:
                    # Fallback: try to get date from external race website
                    event = self._fetch_from_race_site(race_def, seen)
                    if event:
                        events.append(event)
            except Exception as e:
                logger.error(f"Error fetching PR race '{race_def['name']}': {e}")

        logger.info(f"Philadelphia Runner: {len(events)} events")
        return events

    def _fetch_race_from_runsignup(self, race_def: dict, seen: set) -> List[Dict]:
        """Search RunSignUp for this race by name and fetch its details"""
        events = []
        try:
            race_name = race_def['name']
            today = datetime.now()

            params = {
                'search': race_name,
                'state': 'PA',
                'events': 'T',
                'format': 'json',
                'start_date': today.strftime('%Y-%m-%d'),
                'results_per_page': 10,
            }

            response = requests.get(
                RUNSIGNUP_SEARCH_API,
                headers=self.headers,
                params=params,
                timeout=12
            )
            response.raise_for_status()
            data = response.json()
            races = data.get('races', [])

            for race_wrapper in races:
                race = race_wrapper.get('race', {})
                r_name = race.get('name', '').strip()

                # Match by name similarity
                if not self._names_match(race_name, r_name):
                    continue

                address = race.get('address', {})
                state = address.get('state', '').upper()
                if state and state != 'PA':
                    continue

                street = address.get('street', '').strip()
                city = address.get('city', 'Philadelphia')
                zipcode = address.get('zipcode', '').strip()
                if street:
                    location = f"{street}, {city}, PA {zipcode}".strip(', ')
                else:
                    location = f"{city}, PA"

                description = self._clean_description(race.get('description', ''))
                race_url = race.get('url', race_def['info_url'])

                sub_events = race.get('events', [])
                if sub_events:
                    for sub_wrapper in sub_events:
                        sub = sub_wrapper.get('event', {}) if isinstance(sub_wrapper, dict) else {}
                        sub_name = sub.get('name', '').strip()
                        start_time_str = sub.get('start_time', '')
                        if not start_time_str:
                            continue
                        start_date = self._parse_datetime(start_time_str)
                        if not start_date or start_date < datetime.now():
                            continue

                        if sub_name and sub_name.lower() not in r_name.lower():
                            title = f"{r_name} – {sub_name}"
                        else:
                            title = r_name

                        key = f"{title}_{start_time_str[:16]}"
                        if key in seen:
                            continue
                        seen.add(key)

                        price = self._extract_price(sub.get('registration_periods', []))
                        distance = sub.get('distance', '')
                        dist_unit = sub.get('distance_unit', '')
                        dist_str = f"{distance} {dist_unit}".strip() if distance else ''
                        full_desc = f"{dist_str} race. {description}".strip() if dist_str else description

                        events.append(self.create_event(
                            title=title,
                            description=full_desc[:500],
                            start_date=start_date,
                            location=location,
                            category='running',
                            source_url=race_url,
                            price=price,
                        ))
                else:
                    next_date_str = race.get('next_date', '')
                    if not next_date_str:
                        continue
                    start_date = self._parse_mmddyyyy(next_date_str)
                    if not start_date or start_date < datetime.now():
                        continue

                    key = f"{r_name}_{next_date_str}"
                    if key in seen:
                        continue
                    seen.add(key)

                    events.append(self.create_event(
                        title=r_name,
                        description=description[:500],
                        start_date=start_date,
                        location=location,
                        category='running',
                        source_url=race_url,
                    ))
                break  # Found a match, don't process more

        except Exception as e:
            logger.error(f"RunSignUp search error for '{race_def['name']}': {e}")

        return events

    def _fetch_from_race_site(self, race_def: dict, seen: set) -> Optional[Dict]:
        """Fallback: try to extract date from the race's own website JSON-LD"""
        try:
            info_url = race_def.get('info_url', '')
            if not info_url or 'philadelphiarunner.com' in info_url:
                return None

            response = requests.get(info_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try JSON-LD
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string or '')
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('@type') in ('Event', 'SportsEvent', 'MusicEvent', 'Race'):
                            start_str = item.get('startDate', '')
                            if not start_str:
                                continue
                            from dateutil import parser as du_parser
                            start_date = du_parser.parse(start_str)
                            if start_date.tzinfo:
                                start_date = start_date.replace(tzinfo=None)
                            if start_date < datetime.now():
                                continue

                            title = item.get('name', race_def['name'])
                            key = f"{title}_{start_str[:10]}"
                            if key in seen:
                                return None
                            seen.add(key)

                            loc_obj = item.get('location', {})
                            addr = loc_obj.get('address', {}) if isinstance(loc_obj, dict) else {}
                            if isinstance(addr, dict):
                                location = (
                                    f"{addr.get('streetAddress', '')}, "
                                    f"{addr.get('addressLocality', 'Philadelphia')}, PA"
                                ).strip(', ')
                            else:
                                location = loc_obj.get('name', 'Philadelphia, PA') if isinstance(loc_obj, dict) else 'Philadelphia, PA'

                            return self.create_event(
                                title=title,
                                description=item.get('description', '')[:500],
                                start_date=start_date,
                                location=location,
                                category='running',
                                source_url=info_url,
                            )
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Fallback site scrape failed for {race_def['name']}: {e}")

        return None

    def _names_match(self, query: str, candidate: str) -> bool:
        """Check if race names are similar enough"""
        q = re.sub(r'[^a-z0-9 ]', '', query.lower())
        c = re.sub(r'[^a-z0-9 ]', '', candidate.lower())
        # Check if key words from query appear in candidate
        q_words = set(q.split())
        c_words = set(c.split())
        # Ignore common words
        stop = {'the', 'a', 'an', 'and', 'run', 'race'}
        q_key = q_words - stop
        if not q_key:
            return False
        overlap = q_key & c_words
        return len(overlap) / len(q_key) >= 0.5

    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
        try:
            from dateutil import parser as du_parser
            dt = du_parser.parse(dt_str)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except Exception:
            return None

    def _parse_mmddyyyy(self, date_str: str, hour: int = 8) -> Optional[datetime]:
        try:
            dt = datetime.strptime(date_str, '%m/%d/%Y')
            return dt.replace(hour=hour)
        except Exception:
            return None

    def _extract_price(self, periods: list) -> Optional[str]:
        prices = []
        for pw in periods:
            p = pw.get('registration_period', pw)
            fee = p.get('race_fee', '')
            if fee:
                try:
                    prices.append(float(str(fee).replace('$', '').replace(',', '')))
                except ValueError:
                    pass
        if prices:
            min_p = min(prices)
            return f"${min_p:.2f}" if min_p > 0 else 'Free'
        return None

    def _clean_description(self, html: str) -> str:
        if not html:
            return ''
        try:
            from bs4 import BeautifulSoup as BS
            return BS(html, 'html.parser').get_text(' ', strip=True)[:500]
        except Exception:
            return re.sub(r'<[^>]+>', ' ', html).strip()[:500]
