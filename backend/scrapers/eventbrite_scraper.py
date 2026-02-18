"""
Eventbrite Philadelphia Events Scraper
Fetches real events from Eventbrite using JSON-LD structured data
"""

import requests
import json
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class EventbriteScraper(BaseScraper):
    """Scrape real events from Eventbrite Philadelphia using JSON-LD structured data"""

    CATEGORY_URLS = {
        'music': 'https://www.eventbrite.com/d/pa--philadelphia/music/',
        'foodAndDrink': 'https://www.eventbrite.com/d/pa--philadelphia/food-and-drink/',
        'artsAndCulture': 'https://www.eventbrite.com/d/pa--philadelphia/arts/',
        'running': 'https://www.eventbrite.com/d/pa--philadelphia/health/',
        'community': 'https://www.eventbrite.com/d/pa--philadelphia/community/',
        'business': 'https://www.eventbrite.com/d/pa--philadelphia/business/',
    }

    KEYWORD_CATEGORY_MAP = {
        'run': 'running', 'race': 'running', 'marathon': 'running',
        '5k': 'running', '10k': 'running', 'yoga': 'running', 'fitness': 'running',
        'jazz': 'music', 'concert': 'music', 'band': 'music', 'dj': 'music',
        'live music': 'music',
        'food': 'foodAndDrink', 'drink': 'foodAndDrink', 'beer': 'foodAndDrink',
        'wine': 'foodAndDrink', 'tasting': 'foodAndDrink', 'dining': 'foodAndDrink',
        'brunch': 'foodAndDrink', 'cocktail': 'foodAndDrink',
        'art': 'artsAndCulture', 'museum': 'artsAndCulture', 'gallery': 'artsAndCulture',
        'theatre': 'artsAndCulture', 'theater': 'artsAndCulture', 'film': 'artsAndCulture',
        'comedy': 'artsAndCulture', 'dance': 'artsAndCulture', 'exhibition': 'artsAndCulture',
        'network': 'business', 'entrepreneur': 'business', 'startup': 'business',
        'career': 'business', 'professional': 'business',
    }

    def __init__(self):
        super().__init__(
            source_name="Eventbrite",
            source_url="https://www.eventbrite.com/d/pa--philadelphia/events/"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

    # Number of listing pages to fetch per category (each page ~20 events)
    PAGES_PER_CATEGORY = 5

    def scrape(self) -> List[Dict]:
        """Fetch real Philadelphia events from Eventbrite across all categories"""
        all_events = []
        seen_urls = set()

        for category, base_url in self.CATEGORY_URLS.items():
            try:
                events = self._scrape_category_all_pages(base_url, category, seen_urls)
                all_events.extend(events)
                logger.info(f"Eventbrite {category}: {len(events)} events fetched")
            except Exception as e:
                logger.error(f"Error scraping Eventbrite {category}: {e}")

        logger.info(f"Eventbrite total: {len(all_events)} real events")
        return all_events

    def _scrape_category_all_pages(self, base_url: str, default_category: str, seen_urls: set) -> List[Dict]:
        """Scrape multiple pages of an Eventbrite category listing"""
        all_events = []
        import time

        for page_num in range(1, self.PAGES_PER_CATEGORY + 1):
            url = base_url if page_num == 1 else f"{base_url}?page={page_num}"
            try:
                events = self._scrape_category_page(url, default_category, seen_urls)
                all_events.extend(events)
                if not events:
                    # No events on this page — stop paginating early
                    break
                if page_num < self.PAGES_PER_CATEGORY:
                    time.sleep(0.5)  # Be polite between pages
            except Exception as e:
                logger.error(f"Error scraping Eventbrite page {page_num} for {default_category}: {e}")
                break

        return all_events

    def _scrape_category_page(self, url: str, default_category: str, seen_urls: set) -> List[Dict]:
        """Scrape a single Eventbrite category page via JSON-LD"""
        events = []

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    items = data.get('itemListElement', [])
                    for item in items:
                        ev = item.get('item', {})
                        if not ev:
                            continue

                        event_url = ev.get('url', '')
                        if event_url in seen_urls:
                            continue
                        seen_urls.add(event_url)

                        event = self._parse_event(ev, default_category)
                        if event:
                            events.append(event)
                except (json.JSONDecodeError, AttributeError):
                    continue

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")

        return events

    def _parse_event(self, ev: Dict, default_category: str) -> Optional[Dict]:
        """Parse a single event from Eventbrite JSON-LD data"""
        try:
            title = ev.get('name', '').strip()
            if not title:
                return None

            start_date = self._parse_date_str(ev.get('startDate', ''))
            if not start_date:
                return None

            if start_date < datetime.now():
                return None

            end_date = self._parse_date_str(ev.get('endDate', ''))

            # Build location string
            location_data = ev.get('location', {})
            if isinstance(location_data, dict):
                venue_name = location_data.get('name', '')
                address = location_data.get('address', {})
                if isinstance(address, dict):
                    street = address.get('streetAddress', '')
                    city = address.get('addressLocality', 'Philadelphia')
                    state = address.get('addressRegion', 'PA')
                    # Skip events not in Pennsylvania
                    if state and state.upper() not in ('PA', 'PENNSYLVANIA'):
                        return None
                    parts = [p for p in [venue_name, street, city, state] if p]
                    location = ', '.join(parts)
                else:
                    location = venue_name or 'Philadelphia, PA'
            else:
                location = 'Philadelphia, PA'

            if not location.strip():
                location = 'Philadelphia, PA'

            # Extract price
            offers = ev.get('offers', {})
            price = None
            if isinstance(offers, dict):
                price_val = offers.get('price', '')
                if price_val in ('0', 0, ''):
                    price = 'Free'
                elif price_val:
                    price = f"${price_val}"
            elif isinstance(offers, list) and offers:
                price_val = offers[0].get('price', '')
                price = 'Free' if price_val in ('0', 0) else (f"${price_val}" if price_val else None)

            category = self._categorize(title, default_category)

            return self.create_event(
                title=title,
                description=ev.get('description', '')[:500].strip(),
                start_date=start_date,
                end_date=end_date,
                location=location,
                category=category,
                price=price,
                source_url=ev.get('url', ''),
                image_url=ev.get('image', '')
            )

        except Exception as e:
            logger.error(f"Error parsing Eventbrite event: {e}")
            return None

    def _parse_date_str(self, date_str: str) -> Optional[datetime]:
        """Parse Eventbrite date string (ISO format)"""
        if not date_str:
            return None
        try:
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.split('+')[0].split('Z')[0])
            else:
                return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            try:
                from dateutil import parser
                return parser.parse(date_str)
            except Exception:
                return None

    def _categorize(self, title: str, default_category: str) -> str:
        """Determine event category from title keywords"""
        title_lower = title.lower()
        for keyword, category in self.KEYWORD_CATEGORY_MAP.items():
            if keyword in title_lower:
                return category
        return default_category
