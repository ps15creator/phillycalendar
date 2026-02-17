"""
Philadelphia Magic Gardens Events Scraper
Fetches real events via WordPress REST API (yks_ee_events custom post type)
"""

import requests
import json
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class PhillyMagicGardensScraper(BaseScraper):
    """Scrape events from Philadelphia Magic Gardens via WP REST API"""

    API_URL = 'https://www.phillymagicgardens.org/wp-json/wp/v2/yks_ee_events'
    BASE_URL = 'https://www.phillymagicgardens.org'

    def __init__(self):
        super().__init__(
            source_name="Philadelphia Magic Gardens",
            source_url="https://www.phillymagicgardens.org/events/"
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }

    def scrape(self) -> List[Dict]:
        events = []
        try:
            response = requests.get(
                self.API_URL,
                headers=self.headers,
                params={'per_page': 50, 'orderby': 'date', 'order': 'asc'},
                timeout=15
            )
            response.raise_for_status()
            posts = response.json()

            for post in posts:
                event = self._parse_post(post)
                if event:
                    events.append(event)

        except Exception as e:
            logger.error(f"Error scraping Philly Magic Gardens: {e}")

        logger.info(f"Philadelphia Magic Gardens: {len(events)} events")
        return events

    def _parse_post(self, post: Dict) -> Optional[Dict]:
        try:
            # Title
            title = post.get('title', {}).get('rendered', '').strip()
            if not title:
                return None
            # Remove HTML tags
            title = re.sub(r'<[^>]+>', '', title).strip()

            # Event URL
            event_url = post.get('link', self.source_url)

            # Description from content or excerpt
            content = post.get('content', {}).get('rendered', '')
            excerpt = post.get('excerpt', {}).get('rendered', '')
            desc_raw = excerpt or content
            description = re.sub(r'<[^>]+>', ' ', desc_raw).strip()[:400]

            # Date — try ACF fields first, then post date
            meta = post.get('meta', {}) or {}
            acf = post.get('acf', {}) or {}

            # Try various date field names used by Easy Events / ACF
            date_str = (
                acf.get('event_date') or
                acf.get('start_date') or
                meta.get('event_date') or
                meta.get('start_date') or
                post.get('date', '')
            )

            start_date = self._parse_date(date_str)
            if not start_date:
                # Fall back to post published date
                start_date = self._parse_date(post.get('date', ''))

            if not start_date:
                return None
            # Allow events posted recently (within last 7 days) even if date seems past
            from datetime import timedelta
            if start_date < datetime.now() - timedelta(days=7):
                return None

            # Image
            image_url = ''
            featured_media = post.get('_embedded', {}).get('wp:featuredmedia', [])
            if featured_media:
                image_url = featured_media[0].get('source_url', '')

            return self.create_event(
                title=title,
                description=description,
                start_date=start_date,
                location='Philadelphia Magic Gardens, 1020 South St, Philadelphia, PA',
                category='artsAndCulture',
                source_url=event_url,
                image_url=image_url
            )
        except Exception as e:
            logger.error(f"Error parsing Magic Gardens post: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            clean = date_str.split('+')[0].split('Z')[0]
            if 'T' in clean and len(clean) > 19:
                clean = clean[:19]
            return datetime.fromisoformat(clean)
        except Exception:
            try:
                from dateutil import parser as dp
                return dp.parse(date_str).replace(tzinfo=None)
            except Exception:
                return None
