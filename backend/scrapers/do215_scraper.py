"""
Do215 Philadelphia Events Scraper
Scrapes real events from do215.com (Philadelphia's local events guide)
"""

import requests
import re
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class Do215Scraper(BaseScraper):
    """Scrape real events from Do215 - Philadelphia's local events guide"""

    CATEGORY_MAP = {
        'music': 'music',
        'comedy': 'artsAndCulture',
        'food': 'foodAndDrink',
        'drink': 'foodAndDrink',
        'arts': 'artsAndCulture',
        'culture': 'artsAndCulture',
        'sports': 'running',
        'fitness': 'running',
        'film': 'artsAndCulture',
        'charity': 'community',
        'trivia': 'community',
        'other': 'community',
        'activism': 'community',
    }

    def __init__(self):
        super().__init__(
            source_name="Do215",
            source_url="https://do215.com/events"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

    def scrape(self) -> List[Dict]:
        """Fetch real Philadelphia events from Do215 for the next 30 days"""
        all_events = []
        seen_urls = set()
        now = datetime.now()

        # Scrape next 30 days
        pages = []
        for i in range(31):
            d = now + timedelta(days=i)
            if i == 0:
                pages.append('https://do215.com/events')
            else:
                pages.append(f'https://do215.com/events/{d.year}/{d.month}/{d.day}')

        for page_url in pages:
            try:
                events = self._scrape_page(page_url, seen_urls)
                all_events.extend(events)
                if events:
                    logger.info(f"Do215 {page_url}: {len(events)} events")
            except Exception as e:
                logger.error(f"Error scraping Do215 {page_url}: {e}")

        logger.info(f"Do215 total: {len(all_events)} real events")
        return all_events

    def _scrape_page(self, url: str, seen_urls: set) -> List[Dict]:
        """Scrape a single Do215 page"""
        events = []

        try:
            response = requests.get(url, headers=self.headers, timeout=12)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            cards = soup.find_all('div', class_='event-card')

            for card in cards:
                try:
                    event = self._parse_card(card, seen_urls)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.error(f"Error parsing Do215 card: {e}")

        except Exception as e:
            logger.error(f"Error fetching Do215 {url}: {e}")

        return events

    def _parse_card(self, card, seen_urls: set) -> Optional[Dict]:
        """Parse a single Do215 event card"""
        # Title
        title_el = card.find(itemprop='name')
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        if not title:
            return None

        # URL - skip weekly recurring events without a date
        url_el = card.find('a', class_='ds-listing-event-title')
        if not url_el or not url_el.get('href'):
            return None
        href = url_el['href']

        # Only process dated events (not /events/weekly/...)
        if '/weekly/' in href:
            return None

        event_url = 'https://do215.com' + href

        if event_url in seen_urls:
            return None
        seen_urls.add(event_url)

        # Date from data-permalink: /events/2026/2/17/...
        permalink = card.get('data-permalink', href)
        date_match = re.search(r'/events/(\d{4})/(\d+)/(\d+)/', permalink)
        if not date_match:
            return None

        year, month, day = date_match.groups()
        date_str = f'{year}-{month.zfill(2)}-{day.zfill(2)}'

        # Time
        time_el = card.find(class_='ds-event-time')
        time_str = time_el.get_text(strip=True) if time_el else '12:00PM'

        # Parse full datetime
        start_date = self._parse_datetime(date_str, time_str)
        if not start_date or start_date < datetime.now():
            return None

        # Venue
        venue_el = card.find(itemtype='http://schema.org/Place')
        if venue_el:
            venue_name_el = venue_el.find(itemprop='name')
            venue_name = venue_name_el.get_text(strip=True) if venue_name_el else ''
            location = f"{venue_name}, Philadelphia, PA" if venue_name else 'Philadelphia, PA'
        else:
            location = 'Philadelphia, PA'

        # Category from CSS class
        category = self._get_category(card)

        # Price
        price_el = card.find(class_=lambda c: c and 'price' in str(c).lower())
        price_text = price_el.get_text(strip=True) if price_el else None
        if price_text:
            if 'free' in price_text.lower():
                price = 'Free'
            elif re.search(r'\$[\d.]+', price_text):
                price = re.search(r'\$[\d.]+', price_text).group()
            else:
                price = price_text[:30]
        else:
            price = None

        # Cover image
        cover_el = card.find(class_='ds-cover-image')
        image_url = ''
        if cover_el:
            style = cover_el.get('style', '')
            img_match = re.search(r"url\('([^']+)'\)", style)
            if img_match:
                image_url = img_match.group(1)

        return self.create_event(
            title=title,
            description=f"Live event at {location.split(',')[0]}. See website for details and tickets.",
            start_date=start_date,
            location=location,
            category=category,
            price=price,
            source_url=event_url,
            image_url=image_url
        )

    def _parse_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Parse date + time strings into datetime"""
        try:
            full_str = f"{date_str} {time_str}"
            try:
                return datetime.strptime(full_str, '%Y-%m-%d %I:%M%p')
            except ValueError:
                pass
            return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            return None

    def _get_category(self, card) -> str:
        """Extract category from CSS class name"""
        classes = ' '.join(card.get('class', []))
        match = re.search(r'ds-event-category-([a-z-]+)', classes)
        if match:
            raw = match.group(1)
            for part in raw.split('-'):
                if part in self.CATEGORY_MAP:
                    return self.CATEGORY_MAP[part]
        return 'community'
