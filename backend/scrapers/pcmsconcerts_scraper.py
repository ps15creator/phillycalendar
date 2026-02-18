"""
Philadelphia Chamber Music Society (PCMS) Concerts Scraper
Fetches upcoming concerts from pcmsconcerts.org via HTML parsing + JSON-LD
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

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}

BASE_URL = 'https://www.pcmsconcerts.org'
CONCERTS_URL = 'https://www.pcmsconcerts.org/concerts/'


class PCMSConcertsScraper(BaseScraper):
    """Scrape chamber music concerts from Philadelphia Chamber Music Society"""

    def __init__(self):
        super().__init__(
            source_name="Philadelphia Chamber Music Society",
            source_url=CONCERTS_URL
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    def scrape(self) -> List[Dict]:
        events = []
        seen = set()

        # Scrape first 3 pages to get upcoming concerts
        for page in range(1, 4):
            url = CONCERTS_URL if page == 1 else f'{CONCERTS_URL}page/{page}/'
            page_events = self._scrape_page(url, seen)
            if not page_events:
                break
            events.extend(page_events)

        logger.info(f"Philadelphia Chamber Music Society: {len(events)} events")
        return events

    def _scrape_page(self, url: str, seen: set) -> List[Dict]:
        events = []
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try JSON-LD first (most reliable)
            json_ld_events = self._parse_json_ld(soup, seen)
            if json_ld_events:
                return json_ld_events

            # Fall back to HTML card parsing
            events = self._parse_html_cards(soup, seen)

        except Exception as e:
            logger.error(f"Error scraping PCMS page {url}: {e}")

        return events

    def _parse_json_ld(self, soup: BeautifulSoup, seen: set) -> List[Dict]:
        """Extract events from JSON-LD structured data"""
        events = []
        scripts = soup.find_all('script', type='application/ld+json')

        for script in scripts:
            try:
                data = json.loads(script.string or '')
                # Handle both single event and array
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if item.get('@type') in ('MusicEvent', 'Event'):
                        event = self._parse_ld_item(item, seen)
                        if event:
                            events.append(event)
            except Exception:
                continue

        return events

    def _parse_ld_item(self, item: dict, seen: set) -> Optional[Dict]:
        """Parse a single JSON-LD event item"""
        try:
            title = item.get('name', '').strip()
            if not title or title in seen:
                return None

            start_str = item.get('startDate', '')
            start_date = self._parse_date_str(start_str)
            if not start_date or start_date < datetime.now():
                return None

            seen.add(title)

            end_str = item.get('endDate', '')
            end_date = self._parse_date_str(end_str)

            # Location
            location_obj = item.get('location', {})
            venue_name = location_obj.get('name', 'Perelman Theater')
            address = location_obj.get('address', {})
            if isinstance(address, dict):
                street = address.get('streetAddress', '300 South Broad Street')
                city = address.get('addressLocality', 'Philadelphia')
                state = address.get('addressRegion', 'PA')
                location = f"{venue_name}, {street}, {city}, {state}"
            else:
                location = f"{venue_name}, Philadelphia, PA"

            # Price
            offers = item.get('offers', {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price = offers.get('price', '')
            if price:
                price = f"${price}" if not str(price).startswith('$') else str(price)

            # Description
            description = item.get('description', '')
            if isinstance(description, list):
                description = ' '.join(str(d) for d in description)
            description = str(description).strip()[:500]

            # URL
            event_url = item.get('url', CONCERTS_URL)

            return self.create_event(
                title=title,
                description=description,
                start_date=start_date,
                end_date=end_date,
                location=location,
                category='artsAndCulture',
                source_url=event_url,
                price=price or None,
            )
        except Exception as e:
            logger.error(f"Error parsing PCMS LD item: {e}")
            return None

    def _parse_html_cards(self, soup: BeautifulSoup, seen: set) -> List[Dict]:
        """Fall back: parse HTML anchor cards for concerts.
        PCMS structure: <a class='gridpost eqHeight' href='/concerts/slug/'>
                          <div class='gridpost__desc'>
                            <h4 class='gridpost__title'><span itemprop='name'>Name<br/>co-performer</span></h4>
                            Date text... - $price
                          </div>
                        </a>
        """
        events = []

        # Primary selector: anchor cards with class 'gridpost'
        cards = soup.find_all('a', class_='gridpost')
        if not cards:
            # Fallback: any anchor linking to a /concerts/slug/ page
            cards = soup.find_all('a', href=re.compile(r'/concerts/[^/]+/?$'))

        for card in cards:
            try:
                href = card.get('href', '')
                if not href:
                    continue

                # Skip navigation/utility links
                skip_slugs = {'livestreams', 'subscriptions', 'season-pass',
                              'group-tickets', 'season-at-a-glance', 'gala'}
                slug = href.rstrip('/').split('/')[-1]
                if slug in skip_slugs or not slug:
                    continue

                # Extract title from <h4> — replace <br> tags with ' / ' before getting text
                h4 = card.find('h4')
                if h4:
                    # Replace <br> tags with ' / ' separator for multiple performers
                    for br in h4.find_all('br'):
                        br.replace_with(' / ')
                    title = h4.get_text(' ', strip=True)
                    # Collapse multiple spaces
                    title = re.sub(r'\s+', ' ', title).strip()
                else:
                    title = card.get_text(' ', strip=True)[:80]
                    title = re.sub(r'\s+', ' ', title).strip()

                if not title or len(title) < 4:
                    continue

                card_text = card.get_text(' ', strip=True)

                # Extract date: "February 20, 2026 at 7:30 pm"
                start_date = self._extract_date_from_text(card_text)
                if not start_date or start_date < datetime.now():
                    continue

                # Dedup by title + start date
                key = f"{title}_{start_date.strftime('%Y-%m-%d')}"
                if key in seen:
                    continue
                seen.add(key)

                # Extract price
                price_match = re.search(r'\$\s*([\d.]+)', card_text)
                price = f"${price_match.group(1)}" if price_match else None

                event_url = href if href.startswith('http') else BASE_URL + href

                events.append(self.create_event(
                    title=title,
                    description='',
                    start_date=start_date,
                    location='Perelman Theater, 300 South Broad Street, Philadelphia, PA',
                    category='artsAndCulture',
                    source_url=event_url,
                    price=price,
                ))
            except Exception as e:
                logger.error(f"Error parsing PCMS HTML card: {e}")

        return events

    def _parse_date_str(self, date_str: str) -> Optional[datetime]:
        """Parse ISO or human-readable date string"""
        if not date_str:
            return None
        try:
            from dateutil import parser as du_parser
            return du_parser.parse(date_str)
        except Exception:
            return self._extract_date_from_text(date_str)

    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        """Extract date from text like 'February 20, 2026 at 7:30 pm'"""
        # Pattern: "Month Day, Year at H:MM am/pm"
        pattern = re.compile(
            r'(january|february|march|april|may|june|july|august|september|october|november|december|'
            r'jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2}),?\s+(20\d{2})'
            r'(?:\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm))?',
            re.IGNORECASE
        )
        match = pattern.search(text)
        if match:
            month_str = match.group(1).lower()
            day = int(match.group(2))
            year = int(match.group(3))
            month = MONTH_MAP.get(month_str)
            if not month:
                return None
            hour = 19  # default 7pm
            minute = 0
            if match.group(4):
                hour = int(match.group(4))
                minute = int(match.group(5))
                meridiem = match.group(6).lower()
                if meridiem == 'pm' and hour != 12:
                    hour += 12
                elif meridiem == 'am' and hour == 12:
                    hour = 0
            try:
                return datetime(year, month, day, hour, minute)
            except ValueError:
                pass
        return None
