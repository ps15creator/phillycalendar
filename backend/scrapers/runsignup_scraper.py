"""
RunSignUp Philadelphia Running Races Scraper
Fetches upcoming running races in Philadelphia via the RunSignUp public API.
Covers events promoted by: Love Run Philly, Philly Runners, and the broader
Philadelphia running community.
API docs: https://runsignup.com/API/races/GET
"""

import requests
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

RUNSIGNUP_API = 'https://runsignup.com/rest/races'

# Keywords that disqualify an event from being included
EXCLUDE_KEYWORDS = [
    'virtual', 'online', 'challenge only', 'fundraiser only',
]

# If these appear in the race NAME it is likely held outside Philadelphia
# (charity teams register with a Philly address for a race held elsewhere)
OUTSIDE_PHILLY_KEYWORDS = [
    'berlin marathon', 'boston marathon', 'new york marathon', 'chicago marathon',
    'london marathon', 'tokyo marathon', 'nyc marathon',
]


class RunSignUpScraper(BaseScraper):
    """Scrape Philadelphia running races from RunSignUp API"""

    def __init__(self):
        super().__init__(
            source_name="Philadelphia Running Races",
            source_url="https://runsignup.com/races/pa/philadelphia"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
        }

    def scrape(self) -> List[Dict]:
        events = []
        seen = set()

        # Query the RunSignUp API for Philadelphia races
        today = datetime.now()
        start_date = today.strftime('%Y-%m-%d')
        # Look up to 18 months ahead
        from datetime import timedelta
        end_date = (today + timedelta(days=548)).strftime('%Y-%m-%d')

        params = {
            'city': 'Philadelphia',
            'state': 'PA',
            'events': 'T',           # include sub-event details
            'format': 'json',
            'start_date': start_date,
            'end_date': end_date,
            'results_per_page': 50,
            'page': 1,
        }

        try:
            response = requests.get(
                RUNSIGNUP_API,
                headers=self.headers,
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            races = data.get('races', [])

            for race_wrapper in races:
                race = race_wrapper.get('race', {})
                parsed = self._parse_race(race, seen)
                events.extend(parsed)

        except Exception as e:
            logger.error(f"Error scraping RunSignUp Philadelphia races: {e}")

        logger.info(f"Philadelphia Running Races (RunSignUp): {len(events)} events")
        return events

    def _parse_race(self, race: dict, seen: set) -> List[Dict]:
        """Parse a single race entry; may produce multiple events for different distances"""
        results = []
        try:
            race_name = race.get('name', '').strip()
            if not race_name:
                return []

            # Skip charity teams for overseas races
            race_name_lower = race_name.lower()
            if any(kw in race_name_lower for kw in OUTSIDE_PHILLY_KEYWORDS):
                return []

            # Skip obviously non-Philadelphia/PA events (sanity check)
            address = race.get('address', {})
            state = address.get('state', '').upper()
            if state and state != 'PA':
                return []

            # Build location string
            street = address.get('street', '').strip()
            zipcode = address.get('zipcode', '').strip()
            city_display = address.get('city', 'Philadelphia')
            if street:
                location = f"{street}, {city_display}, PA {zipcode}".strip(', ')
            else:
                location = f"{city_display}, PA"

            race_url = race.get('url', self.source_url)
            description = self._clean_description(race.get('description', ''))

            # Get sub-events for specific distances/times
            # NOTE: API returns events as a flat list of dicts (not wrapped in {'event': ...})
            sub_events = race.get('events', [])

            if sub_events:
                # Check if any sub-events are non-virtual (in-person races)
                has_inperson = any(
                    'virtual' not in (
                        (s.get('event', s) if isinstance(s, dict) and 'event_id' not in s else s)
                        .get('event_type', '')
                    ).lower()
                    for s in sub_events
                )

                if not has_inperson:
                    # All sub-events are virtual — skip this race entirely
                    return []

                added_any = False
                for sub in sub_events:
                    # sub may be a plain dict OR wrapped in {'event': {...}}
                    if isinstance(sub, dict) and 'event_id' not in sub:
                        sub = sub.get('event', sub)
                    event = self._parse_sub_event(
                        race_name, sub, location, race_url, description, seen
                    )
                    if event:
                        results.append(event)
                        added_any = True

                if not added_any:
                    # All sub-events were past — try race level date as fallback
                    event = self._parse_race_level(race, location, race_url, description, seen)
                    if event:
                        results.append(event)
            else:
                # No sub-events — use the race-level next_date
                event = self._parse_race_level(race, location, race_url, description, seen)
                if event:
                    results.append(event)

        except Exception as e:
            logger.error(f"Error parsing RunSignUp race: {e}")

        return results

    def _parse_sub_event(
        self,
        race_name: str,
        sub: dict,
        location: str,
        race_url: str,
        description: str,
        seen: set
    ) -> Optional[Dict]:
        """Parse an individual race distance/category within a race"""
        try:
            sub_name = sub.get('name', '').strip()
            event_type = sub.get('event_type', '').lower()

            # Skip virtual/online events
            if 'virtual' in event_type:
                return None

            start_time_str = sub.get('start_time', '')
            if not start_time_str:
                return None

            start_date = self._parse_datetime(start_time_str)
            if not start_date or start_date < datetime.now():
                return None

            # Build a descriptive title
            # Only append sub_name if it adds useful info (distance/type)
            if sub_name and sub_name.lower() not in race_name.lower():
                # Clean up common noise in sub-event names
                clean_sub = sub_name.strip()
                # If sub-event name is just the race name repeated, skip it
                if len(clean_sub) > 3:
                    title = f"{race_name} – {clean_sub}"
                else:
                    title = race_name
            else:
                title = race_name

            # Skip virtual/online events by title keyword
            if any(kw in title.lower() for kw in EXCLUDE_KEYWORDS):
                return None

            # Dedup by title + start datetime (to date precision — same race, same day = one entry)
            key = f"{race_name}_{start_date.strftime('%Y-%m-%d')}"
            if key in seen:
                return None
            seen.add(key)

            # Extract price
            price = self._extract_price(sub.get('registration_periods', []))

            distance = sub.get('distance', '')
            distance_unit = sub.get('distance_unit', '')
            if distance and distance_unit:
                dist_str = f"{distance} {distance_unit}"
                if dist_str.lower() not in description.lower():
                    description = f"{dist_str} race. {description}".strip()

            return self.create_event(
                title=race_name,  # Use the main race name for clarity
                description=description[:500],
                start_date=start_date,
                location=location,
                category='running',
                source_url=race_url,
                price=price,
            )
        except Exception as e:
            logger.error(f"Error parsing RunSignUp sub-event: {e}")
            return None

    def _parse_race_level(
        self, race: dict, location: str, race_url: str, description: str, seen: set
    ) -> Optional[Dict]:
        """Parse race using the race-level next_date field"""
        try:
            title = race.get('name', '').strip()
            if not title:
                return None

            if any(kw in title.lower() for kw in EXCLUDE_KEYWORDS):
                return None

            next_date_str = race.get('next_date', '')
            if not next_date_str:
                return None

            # next_date is "MM/DD/YYYY"
            start_date = self._parse_mmddyyyy(next_date_str)
            if not start_date or start_date < datetime.now():
                return None

            key = f"{title}_{next_date_str}"
            if key in seen:
                return None
            seen.add(key)

            return self.create_event(
                title=title,
                description=description[:500],
                start_date=start_date,
                location=location,
                category='running',
                source_url=race_url,
            )
        except Exception as e:
            logger.error(f"Error parsing RunSignUp race level: {e}")
            return None

    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """Parse datetime string in multiple formats:
        - '2026-03-29 07:30:00'  (standard)
        - '3/29/2026 07:30'       (RunSignUp M/D/YYYY format)
        - '3/29/2026 07:30:00'
        """
        if not dt_str:
            return None
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%m/%d/%Y %H:%M:%S',
            '%m/%d/%Y %H:%M',
            '%m/%d/%Y',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(dt_str.strip(), fmt)
            except ValueError:
                continue
        try:
            from dateutil import parser as du_parser
            dt = du_parser.parse(dt_str)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except Exception:
            return None

    def _parse_mmddyyyy(self, date_str: str, hour: int = 8, minute: int = 0) -> Optional[datetime]:
        """Parse 'MM/DD/YYYY' format, defaulting to 8:00 AM race start"""
        try:
            dt = datetime.strptime(date_str, '%m/%d/%Y')
            return dt.replace(hour=hour, minute=minute)
        except Exception:
            return None

    def _extract_price(self, registration_periods: list) -> Optional[str]:
        """Get the cheapest registration price from the registration periods.
        RunSignUp returns fees as '$30.00' strings (with dollar sign included).
        """
        if not registration_periods:
            return None
        prices = []
        for period in registration_periods:
            # periods may be plain dicts or wrapped in {'registration_period': {...}}
            if isinstance(period, dict) and 'registration_period' in period:
                period = period['registration_period']
            fee = period.get('race_fee', '')
            if fee:
                try:
                    prices.append(float(str(fee).replace('$', '').replace(',', '').strip()))
                except ValueError:
                    pass
        if prices:
            min_price = min(prices)
            return f"${min_price:.2f}" if min_price > 0 else 'Free'
        return None

    def _clean_description(self, html_desc: str) -> str:
        """Strip HTML tags from description"""
        if not html_desc:
            return ''
        try:
            from bs4 import BeautifulSoup
            text = BeautifulSoup(html_desc, 'html.parser').get_text(' ', strip=True)
        except Exception:
            text = re.sub(r'<[^>]+>', ' ', html_desc)
        return ' '.join(text.split())[:500]
