"""
Barnes Foundation Philadelphia Events Scraper
Fetches exhibitions and events from the Barnes Foundation website
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


class BarnesScraper(BaseScraper):
    """Scrape exhibitions and events from Barnes Foundation"""

    URL = 'https://www.barnesfoundation.org/whats-on'

    def __init__(self):
        super().__init__(
            source_name="Barnes Foundation",
            source_url="https://www.barnesfoundation.org/whats-on"
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

            cards = soup.find_all('div', class_=lambda c: c and 'card' in str(c).lower())
            seen = set()

            for card in cards:
                event = self._parse_card(card, seen)
                if event:
                    events.append(event)

        except Exception as e:
            logger.error(f"Error scraping Barnes Foundation: {e}")

        logger.info(f"Barnes Foundation: {len(events)} events")
        return events

    def _parse_card(self, card, seen: set) -> Optional[Dict]:
        try:
            title_elem = card.find(['h2', 'h3', 'h4'])
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)
            if not title or title in seen or len(title) < 4:
                return None

            # Skip generic nav/footer cards
            if any(skip in title.lower() for skip in ['visit', 'membership', 'newsletter', 'donate', 'contact', 'shop']):
                return None

            card_text = card.get_text(' ', strip=True)

            # Skip permanent/ongoing exhibitions without upcoming dates
            if 'permanent' in card_text.lower() and 'ongoing' in card_text.lower():
                return None

            # Try to extract date from card text
            start_date = self._extract_date(card_text)
            if not start_date:
                return None
            if start_date < datetime.now():
                return None

            seen.add(title)

            link = card.find('a', href=True)
            event_url = link['href'] if link else self.URL
            if event_url and not event_url.startswith('http'):
                event_url = 'https://www.barnesfoundation.org' + event_url

            img = card.find('img')
            image_url = img.get('src', '') if img else ''

            desc_elem = card.find('p')
            description = desc_elem.get_text(strip=True)[:400] if desc_elem else ''

            return self.create_event(
                title=title,
                description=description,
                start_date=start_date,
                location='Barnes Foundation, 2025 Benjamin Franklin Pkwy, Philadelphia, PA',
                category='artsAndCulture',
                source_url=event_url,
                image_url=image_url
            )
        except Exception as e:
            logger.error(f"Error parsing Barnes card: {e}")
            return None

    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract a date from card text like 'Until February 22, 2026' or 'March 15, 2026'"""
        text_lower = text.lower()

        # Pattern: Month Day, Year (e.g., February 22, 2026)
        pattern = re.compile(
            r'(january|february|march|april|may|june|july|august|september|october|november|december|'
            r'jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2}),?\s+(20\d{2})',
            re.IGNORECASE
        )
        match = pattern.search(text)
        if match:
            month_str = match.group(1).lower()
            day = int(match.group(2))
            year = int(match.group(3))
            month = MONTH_MAP.get(month_str)
            if month:
                try:
                    return datetime(year, month, day, 10, 0)
                except ValueError:
                    pass

        return None
