"""
Visit Philadelphia Events Scraper
Scrapes real events from the official Philadelphia tourism website
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


class VisitPhillyScraper(BaseScraper):
    """Scrape real events from Visit Philadelphia"""

    PAGES = [
        'https://www.visitphilly.com/events/',
        'https://www.visitphilly.com/things-to-do/arts-culture/',
        'https://www.visitphilly.com/things-to-do/food-drink/',
        'https://www.visitphilly.com/things-to-do/outdoor-recreation/',
    ]

    KEYWORD_CATEGORY_MAP = {
        'run': 'running', 'race': 'running', 'marathon': 'running',
        '5k': 'running', '10k': 'running', 'walk': 'running',
        'jazz': 'music', 'concert': 'music', 'band': 'music', 'music': 'music',
        'performance': 'music', 'symphony': 'music', 'orchestra': 'music',
        'food': 'foodAndDrink', 'drink': 'foodAndDrink', 'beer': 'foodAndDrink',
        'wine': 'foodAndDrink', 'tasting': 'foodAndDrink', 'restaurant': 'foodAndDrink',
        'art': 'artsAndCulture', 'museum': 'artsAndCulture', 'gallery': 'artsAndCulture',
        'theater': 'artsAndCulture', 'theatre': 'artsAndCulture', 'film': 'artsAndCulture',
        'exhibition': 'artsAndCulture', 'show': 'artsAndCulture',
        'festival': 'community', 'fair': 'community', 'market': 'community',
        'parade': 'community', 'community': 'community',
    }

    def __init__(self):
        super().__init__(
            source_name="Visit Philadelphia",
            source_url="https://www.visitphilly.com/events/"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

    def scrape(self) -> List[Dict]:
        """Fetch real Philadelphia events from Visit Philadelphia"""
        all_events = []
        seen_titles = set()

        for page_url in self.PAGES:
            try:
                events = self._scrape_page(page_url, seen_titles)
                all_events.extend(events)
                logger.info(f"VisitPhilly {page_url}: {len(events)} events")
            except Exception as e:
                logger.error(f"Error scraping VisitPhilly {page_url}: {e}")

        logger.info(f"VisitPhilly total: {len(all_events)} real events")
        return all_events

    def _scrape_page(self, url: str, seen_titles: set) -> List[Dict]:
        """Scrape a single Visit Philadelphia page"""
        events = []

        try:
            response = requests.get(url, headers=self.headers, timeout=12)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try JSON-LD first
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    # Handle array of items
                    if isinstance(data, list):
                        items = data
                    elif data.get('@type') == 'ItemList':
                        items = [i.get('item', i) for i in data.get('itemListElement', [])]
                    elif data.get('@type') == 'Event':
                        items = [data]
                    else:
                        items = []

                    for item in items:
                        event = self._parse_jsonld_event(item, seen_titles)
                        if event:
                            events.append(event)
                except (json.JSONDecodeError, AttributeError):
                    continue

            # If no JSON-LD events, try HTML parsing
            if not events:
                events = self._parse_html_events(soup, url, seen_titles)

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")

        return events

    def _parse_jsonld_event(self, item: Dict, seen_titles: set) -> Optional[Dict]:
        """Parse an event from JSON-LD data"""
        try:
            if item.get('@type') not in ('Event', None):
                if item.get('@type') and item.get('@type') != 'Event':
                    return None

            title = item.get('name', '').strip()
            if not title or title in seen_titles:
                return None

            start_date_str = item.get('startDate', '')
            if not start_date_str:
                return None

            start_date = self._parse_date_str(start_date_str)
            if not start_date or start_date < datetime.now():
                return None

            seen_titles.add(title)
            end_date = self._parse_date_str(item.get('endDate', ''))

            # Location
            loc = item.get('location', {})
            if isinstance(loc, dict):
                location = loc.get('name', '') or loc.get('address', {}).get('addressLocality', 'Philadelphia, PA')
            else:
                location = 'Philadelphia, PA'

            description = item.get('description', '')[:500].strip()
            event_url = item.get('url', url)
            image_url = item.get('image', '')
            if isinstance(image_url, dict):
                image_url = image_url.get('url', '')

            # Price
            offers = item.get('offers', {})
            price = None
            if isinstance(offers, dict):
                price_val = offers.get('price', '')
                price = 'Free' if price_val in ('0', 0, '') else (f"${price_val}" if price_val else None)
            elif isinstance(offers, list) and offers:
                price_val = offers[0].get('price', '')
                price = 'Free' if price_val in ('0', 0) else (f"${price_val}" if price_val else None)

            category = self._categorize(title + ' ' + description)

            return self.create_event(
                title=title,
                description=description,
                start_date=start_date,
                end_date=end_date,
                location=location,
                category=category,
                price=price,
                source_url=event_url,
                image_url=image_url
            )
        except Exception as e:
            logger.error(f"Error parsing Visit Philly JSON-LD event: {e}")
            return None

    def _parse_html_events(self, soup: BeautifulSoup, page_url: str, seen_titles: set) -> List[Dict]:
        """Fallback HTML parsing for Visit Philadelphia"""
        events = []

        # Try various card selectors
        cards = (
            soup.find_all('article') or
            soup.find_all('div', class_=lambda c: c and ('card' in c.lower() or 'event' in c.lower())) or
            soup.find_all('li', class_=lambda c: c and 'event' in c.lower())
        )

        for card in cards[:20]:
            try:
                title_elem = card.find(['h2', 'h3', 'h4'])
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                if not title or title in seen_titles:
                    continue

                link_elem = card.find('a', href=True)
                event_url = link_elem['href'] if link_elem else page_url
                if event_url and not event_url.startswith('http'):
                    event_url = 'https://www.visitphilly.com' + event_url

                date_elem = card.find('time') or card.find(class_=lambda c: c and 'date' in c.lower())
                date_str = (date_elem.get('datetime') or date_elem.get_text(strip=True)) if date_elem else ''
                start_date = self._parse_date_str(date_str) if date_str else None
                if not start_date or start_date < datetime.now():
                    continue

                seen_titles.add(title)
                desc_elem = card.find('p')
                description = desc_elem.get_text(strip=True)[:300] if desc_elem else ''

                img_elem = card.find('img')
                image_url = img_elem.get('src', '') if img_elem else ''

                category = self._categorize(title + ' ' + description)

                events.append(self.create_event(
                    title=title,
                    description=description,
                    start_date=start_date,
                    location='Philadelphia, PA',
                    category=category,
                    source_url=event_url,
                    image_url=image_url
                ))

            except Exception as e:
                logger.error(f"Error parsing Visit Philly HTML card: {e}")

        return events

    def _parse_date_str(self, date_str: str) -> Optional[datetime]:
        """Parse various date string formats"""
        if not date_str:
            return None
        date_str = date_str.strip()
        try:
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.split('+')[0].split('Z')[0])
            elif re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                return datetime.strptime(date_str, '%Y-%m-%d')
            else:
                from dateutil import parser
                return parser.parse(date_str)
        except Exception:
            return None

    def _categorize(self, text: str) -> str:
        """Determine event category from text"""
        text_lower = text.lower()
        for keyword, category in self.KEYWORD_CATEGORY_MAP.items():
            if keyword in text_lower:
                return category
        return 'community'
