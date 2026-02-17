"""
Mural Arts Philadelphia Events Scraper
Fetches real events from Mural Arts Philadelphia website
"""

import requests
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


class MuralArtsScraper(BaseScraper):
    """Scrape events from Mural Arts Philadelphia"""

    URL = 'https://muralarts.org/events/'

    def __init__(self):
        super().__init__(
            source_name="Mural Arts Philadelphia",
            source_url="https://muralarts.org/events/"
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
            soup = BeautifulSoup(response.content, 'html.parser')

            seen = set()

            # Mural Arts uses WordPress with post cards
            # Try article/post elements
            cards = (
                soup.find_all('article') or
                soup.find_all('div', class_=lambda c: c and 'post' in str(c).lower() and 'event' in str(c).lower()) or
                soup.find_all('div', class_=lambda c: c and 'event' in str(c).lower())
            )

            for card in cards[:50]:
                event = self._parse_card(card, seen)
                if event:
                    events.append(event)

        except Exception as e:
            logger.error(f"Error scraping Mural Arts: {e}")

        logger.info(f"Mural Arts: {len(events)} events")
        return events

    def _parse_card(self, card, seen: set) -> Optional[Dict]:
        try:
            title_elem = card.find(['h2', 'h3', 'h4'])
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)
            if not title or title in seen or len(title) < 4:
                return None

            card_text = card.get_text(' ', strip=True)

            # Find date in card text
            start_date = self._extract_date(card_text)

            # Try <time> element
            if not start_date:
                time_elem = card.find('time')
                if time_elem:
                    date_str = time_elem.get('datetime', '') or time_elem.get_text(strip=True)
                    start_date = self._parse_date_str(date_str)

            if not start_date or start_date < datetime.now():
                return None

            seen.add(title)

            link = card.find('a', href=True)
            event_url = link['href'] if link else self.URL
            if event_url and not event_url.startswith('http'):
                event_url = 'https://muralarts.org' + event_url

            img = card.find('img')
            image_url = img.get('src', '') if img else ''

            desc_elem = card.find('p')
            description = desc_elem.get_text(strip=True)[:400] if desc_elem else ''

            return self.create_event(
                title=title,
                description=description,
                start_date=start_date,
                location='Philadelphia, PA',
                category='artsAndCulture',
                source_url=event_url,
                image_url=image_url
            )
        except Exception as e:
            logger.error(f"Error parsing Mural Arts card: {e}")
            return None

    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract date from text like 'Feb 15', 'February 15, 2026'"""
        pattern = re.compile(
            r'(january|february|march|april|may|june|july|august|september|october|november|december|'
            r'jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})(?:,?\s+(20\d{2}))?',
            re.IGNORECASE
        )
        match = pattern.search(text)
        if match:
            month_str = match.group(1).lower()
            day = int(match.group(2))
            year = int(match.group(3)) if match.group(3) else datetime.now().year
            month = MONTH_MAP.get(month_str)
            if month:
                try:
                    dt = datetime(year, month, day, 10, 0)
                    # If no year in text and date is in the past, try next year
                    if not match.group(3) and dt < datetime.now():
                        dt = datetime(year + 1, month, day, 10, 0)
                    return dt
                except ValueError:
                    pass
        return None

    def _parse_date_str(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.split('+')[0].split('Z')[0])
        except Exception:
            try:
                from dateutil import parser
                return parser.parse(date_str)
            except Exception:
                return None
