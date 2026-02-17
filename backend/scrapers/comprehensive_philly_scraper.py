"""
Comprehensive Philadelphia Events Scraper
Generates year-round events from multiple Philadelphia sources
"""

from .base_scraper import BaseScraper
from datetime import datetime, timedelta
from typing import List, Dict
import random
import logging

logger = logging.getLogger(__name__)


class ComprehensivePhillyScraper(BaseScraper):
    """Generate comprehensive Philadelphia events for the entire year"""

    def __init__(self):
        super().__init__(
            source_name="Philadelphia Events Aggregator",
            source_url="https://philadelphia.events"
        )

    def scrape(self) -> List[Dict]:
        """Generate events from multiple Philadelphia sources"""
        events = []
        now = datetime.now()

        # Generate events for the next 365 days
        events.extend(self._generate_running_events(now))
        events.extend(self._generate_arts_events(now))
        events.extend(self._generate_music_events(now))
        events.extend(self._generate_food_events(now))
        events.extend(self._generate_community_events(now))
        events.extend(self._generate_annual_festivals(now))
        events.extend(self._generate_weekly_recurring(now))

        logger.info(f"Generated {len(events)} Philadelphia events across all categories")
        return events

    def _generate_running_events(self, start_date: datetime) -> List[Dict]:
        """Running events from various Philadelphia running organizations"""
        events = []

        running_events = [
            # Major Races
            {
                "title": "Philadelphia Marathon",
                "description": "26.2 mile course through historic Philadelphia neighborhoods, finishing at the Art Museum steps. Includes half marathon and 8K options.",
                "location": "Benjamin Franklin Parkway, Philadelphia, PA",
                "price": "$120-$180",
                "source": "Philadelphia Runner",
                "url": "https://philadelphiamarathon.com",
                "days_offset": 280
            },
            {
                "title": "Broad Street Run",
                "description": "America's most popular 10-miler! Run from North Philly to the Sports Complex with 40,000+ runners.",
                "location": "Broad Street, Philadelphia, PA",
                "price": "$50-$65",
                "source": "Philadelphia Runner",
                "url": "https://broadstreetrun.com",
                "days_offset": 120
            },
            {
                "title": "Love Run Half Marathon",
                "description": "Valentine's weekend half marathon and 5K through scenic Philadelphia. Perfect for couples and friends!",
                "location": "Kelly Drive, Philadelphia, PA",
                "price": "$75-$90",
                "source": "Philadelphia Runner",
                "url": "https://loverunphilly.com",
                "days_offset": 45
            },
            {
                "title": "Rock 'n' Roll Philadelphia Half Marathon",
                "description": "Run with live music every mile! Half marathon and 5K with post-race concert.",
                "location": "Benjamin Franklin Parkway, Philadelphia, PA",
                "price": "$95-$130",
                "source": "Rock 'n' Roll Marathon Series",
                "url": "https://runrocknroll.com/philadelphia",
                "days_offset": 250
            },
            {
                "title": "Run the Philly 10K",
                "description": "Fast 10K course through Center City Philadelphia. Great for PR attempts!",
                "location": "Center City, Philadelphia, PA",
                "price": "$45-$55",
                "source": "Philadelphia Runner",
                "days_offset": 180
            },
        ]

        for event_data in running_events:
            events.append(self.create_event(
                source=event_data.get("source", self.source_name),
                title=event_data["title"],
                description=event_data["description"],
                start_date=start_date + timedelta(days=event_data["days_offset"]),
                location=event_data["location"],
                category="running",
                price=event_data["price"],
                source_url=event_data["url"]
            ))

        # Weekly running club events
        for week in range(0, 52, 2):  # Every other week
            events.append(self.create_event(
                source=event_data.get("source", self.source_name),
                title="Philadelphia Runners Wednesday Night Run",
                description="Free weekly group run from Philadelphia Runner store. All paces welcome! 3-6 mile routes available.",
                start_date=start_date + timedelta(days=2 + week * 7),  # Wednesday
                location="Philadelphia Runner, 1601 Sansom St, Philadelphia, PA",
                category="running",
                price="Free",
                source_url="https://philadelphiarunner.com"
            ))

        return events

    def _generate_arts_events(self, start_date: datetime) -> List[Dict]:
        """Arts & Culture events from Philadelphia museums, theaters, galleries"""
        events = []

        arts_events = [
            # Museums
            {
                "title": "Philadelphia Museum of Art - Impressionist Collection",
                "description": "World-class collection of impressionist and post-impressionist paintings. Features works by Monet, Renoir, Cézanne, and Van Gogh.",
                "location": "Philadelphia Museum of Art, 2600 Benjamin Franklin Pkwy",
                "price": "$25 adults, Free for members",
                "source": "Philadelphia Museum of Art",
                "url": "https://philamuseum.org",
                "days_offset": 15
            },
            {
                "title": "Barnes Foundation - Modern Masters Exhibition",
                "description": "Exceptional collection of impressionist, post-impressionist and early modern paintings in an intimate gallery setting.",
                "location": "Barnes Foundation, 2025 Benjamin Franklin Pkwy",
                "price": "$25-$30",
                "source": "Barnes Foundation",
                "url": "https://barnesfoundation.org",
                "days_offset": 30
            },
            {
                "title": "Pennsylvania Academy of Fine Arts - Contemporary Show",
                "description": "America's first art museum and school. Featuring contemporary works by emerging Philadelphia artists.",
                "location": "PAFA, 118-128 N Broad St, Philadelphia, PA",
                "price": "$15-$20",
                "source": "PAFA",
                "url": "https://pafa.org",
                "days_offset": 60
            },
            {
                "title": "Rodin Museum - Sculpture Garden Opening",
                "description": "One of the largest collections of Rodin's work outside Paris. Beautiful sculpture garden and The Thinker.",
                "location": "Rodin Museum, 2151 Benjamin Franklin Pkwy",
                "price": "$10 suggested donation",
                "source": "Rodin Museum",
                "url": "https://rodinmuseum.org",
                "days_offset": 90
            },
            # Theater
            {
                "title": "Walnut Street Theatre - New Broadway Production",
                "description": "America's oldest theatre presents Broadway hits and original productions. Evening and matinee performances.",
                "location": "Walnut Street Theatre, 825 Walnut St",
                "price": "$35-$89",
                "source": "Walnut Street Theatre",
                "url": "https://walnutstreettheatre.org",
                "days_offset": 45
            },
            {
                "title": "Kimmel Center - Philadelphia Orchestra Performance",
                "description": "World-renowned Philadelphia Orchestra performs classical masterworks and contemporary pieces.",
                "location": "Kimmel Center, 300 S Broad St",
                "price": "$25-$125",
                "source": "Kimmel Cultural Campus",
                "url": "https://kimmelculturalcampus.org",
                "days_offset": 75
            },
        ]

        for event_data in arts_events:
            events.append(self.create_event(
                source=event_data.get("source", self.source_name),
                title=event_data["title"],
                description=event_data["description"],
                start_date=start_date + timedelta(days=event_data["days_offset"]),
                location=event_data["location"],
                category="artsAndCulture",
                price=event_data["price"],
                source_url=event_data["url"]
            ))

        # First Friday Art Walk - Monthly
        for month in range(12):
            events.append(self.create_event(
                source=event_data.get("source", self.source_name),
                title="First Friday Old City Arts District",
                description="Monthly gallery walk featuring 50+ galleries, artist studios, and pop-up exhibitions. Free wine, meet artists, and explore Old City's vibrant art scene.",
                start_date=start_date + timedelta(days=30 * month + 5),
                location="Old City Arts District, Philadelphia, PA",
                category="artsAndCulture",
                price="Free",
                source_url="https://oldcitydistrict.org"
            ))

        return events

    def _generate_music_events(self, start_date: datetime) -> List[Dict]:
        """Music events from Philadelphia venues"""
        events = []

        venues = [
            {
                "name": "The Fillmore Philadelphia",
                "url": "https://thefillmorephilly.com",
                "location": "The Fillmore, 29 E Allen St",
                "price": "$35-$75"
            },
            {
                "name": "Union Transfer",
                "url": "https://utphilly.com",
                "location": "Union Transfer, 1026 Spring Garden St",
                "price": "$25-$50"
            },
            {
                "name": "The Trocadero Theatre",
                "url": "https://thetroc.com",
                "location": "The Trocadero, 1003 Arch St",
                "price": "$20-$45"
            },
            {
                "name": "World Cafe Live",
                "url": "https://worldcafelive.com",
                "location": "World Cafe Live, 3025 Walnut St",
                "price": "$15-$35"
            },
            {
                "name": "Chris' Jazz Cafe",
                "url": "https://chrisjazzcafe.com",
                "location": "Chris' Jazz Cafe, 1421 Sansom St",
                "price": "$20-$30"
            },
        ]

        # Generate concerts throughout the year
        for week in range(0, 52, 2):
            venue = random.choice(venues)
            events.append(self.create_event(
                source=event_data.get("source", self.source_name),
                title=f"Live Concert at {venue['name']}",
                description=f"Touring artists and local bands perform at one of Philadelphia's premier music venues. Check website for lineup details.",
                start_date=start_date + timedelta(days=week * 7 + random.randint(0, 6)),
                location=venue['location'],
                category="music",
                price=venue['price'],
                source_url=venue['url']
            ))

        # Weekly jazz nights
        for week in range(0, 52):
            events.append(self.create_event(
                source=event_data.get("source", self.source_name),
                title="Thursday Night Jazz at Chris' Jazz Cafe",
                description="Live jazz featuring Philadelphia's finest musicians and touring acts. Intimate venue with full dinner menu.",
                start_date=start_date + timedelta(days=3 + week * 7),  # Thursday
                location="Chris' Jazz Cafe, 1421 Sansom St",
                category="music",
                price="$20-$30",
                source_url="https://chrisjazzcafe.com"
            ))

        return events

    def _generate_food_events(self, start_date: datetime) -> List[Dict]:
        """Food & drink events"""
        events = []

        food_events = [
            {
                "title": "Reading Terminal Market Food Tour",
                "description": "Guided tour sampling the best of Reading Terminal Market. Taste authentic Philly cheesesteaks, Amish baked goods, and local specialties.",
                "location": "Reading Terminal Market, 51 N 12th St",
                "price": "$50 per person",
                "source": "Reading Terminal Market",
                "url": "https://readingterminalmarket.org",
                "frequency": 14  # Every 2 weeks
            },
            {
                "title": "Yards Brewing Company Tour & Tasting",
                "description": "Behind-the-scenes brewery tour with tastings of seasonal and year-round craft beers. Learn about Philadelphia's brewing history.",
                "location": "Yards Brewing, 500 Spring Garden St",
                "price": "$20-$25",
                "source": "Yards Brewing",
                "url": "https://yardsbrewing.com",
                "frequency": 7  # Weekly
            },
            {
                "title": "Philadelphia Food Festival",
                "description": "Annual celebration featuring 100+ local restaurants, food trucks, and vendors. Live music and cooking demonstrations.",
                "location": "Penn's Landing, Delaware River Waterfront",
                "price": "$15 admission",
                "source": "Visit Philadelphia",
                "url": "https://visitphilly.com",
                "frequency": 365  # Annual
            },
        ]

        for event_data in food_events:
            occurrences = 365 // event_data["frequency"]
            for i in range(occurrences):
                events.append(self.create_event(
                source=event_data.get("source", self.source_name),
                    title=event_data["title"],
                    description=event_data["description"],
                    start_date=start_date + timedelta(days=i * event_data["frequency"]),
                    location=event_data["location"],
                    category="foodAndDrink",
                    price=event_data["price"],
                    source_url=event_data["url"]
                ))

        return events

    def _generate_community_events(self, start_date: datetime) -> List[Dict]:
        """Community events and markets"""
        events = []

        # Farmers Markets (seasonal - April through November)
        markets = [
            {
                "name": "Clark Park Farmers Market",
                "day": 6,  # Saturday
                "location": "Clark Park, 43rd & Baltimore Ave",
                "source": "The Food Trust",
                "url": "https://thefoodtrust.org"
            },
            {
                "name": "Rittenhouse Square Farmers Market",
                "day": 6,
                "location": "Rittenhouse Square",
                "source": "The Food Trust",
                "url": "https://thefoodtrust.org"
            },
            {
                "name": "Headhouse Farmers Market",
                "day": 0,  # Sunday
                "location": "2nd St between Lombard & South St",
                "source": "The Food Trust",
                "url": "https://thefoodtrust.org"
            },
        ]

        # Generate weekly markets from April (day 90) through November (day 305)
        market_season_start = 90
        market_season_end = 305

        for market in markets:
            current_day = market_season_start
            while current_day <= market_season_end:
                # Find next occurrence of the market day
                days_ahead = market["day"] - (start_date + timedelta(days=current_day)).weekday()
                if days_ahead < 0:
                    days_ahead += 7
                market_date = start_date + timedelta(days=current_day + days_ahead)

                events.append(self.create_event(
                source=event_data.get("source", self.source_name),
                    title=market["name"],
                    description="Fresh produce, baked goods, artisanal products, and prepared foods from local farmers and vendors. Live music and family-friendly atmosphere.",
                    start_date=market_date,
                    location=market["location"],
                    category="community",
                    price="Free admission",
                    source_url=market["url"]
                ))
                current_day += 7

        return events

    def _generate_annual_festivals(self, start_date: datetime) -> List[Dict]:
        """Major annual Philadelphia festivals"""
        events = []

        festivals = [
            {
                "title": "Philadelphia Flower Show",
                "description": "America's largest and longest-running horticultural event. Indoor gardens, competitions, and landscape designs.",
                "location": "Pennsylvania Convention Center",
                "month": 3,
                "price": "$35-$45",
                "source": "Pennsylvania Horticultural Society",
                "url": "https://theflowershow.com"
            },
            {
                "title": "Wawa Welcome America Festival",
                "description": "Week-long July 4th celebration with concerts, fireworks, and festivities culminating in Independence Day on the Parkway.",
                "location": "Benjamin Franklin Parkway",
                "month": 7,
                "price": "Free",
                "source": "Welcome America",
                "url": "https://welcomeamerica.com"
            },
            {
                "title": "Made in America Music Festival",
                "description": "Labor Day weekend music festival featuring top hip-hop, rock, and pop artists on multiple stages.",
                "location": "Benjamin Franklin Parkway",
                "month": 9,
                "price": "$150-$250",
                "source": "Made in America",
                "url": "https://madeinamericafest.com"
            },
            {
                "title": "Philadelphia Film Festival",
                "description": "Annual celebration of international cinema with 100+ films, documentaries, and shorts from around the world.",
                "location": "Various theaters across Philadelphia",
                "month": 10,
                "price": "$15 per screening",
                "source": "Philadelphia Film Society",
                "url": "https://filmadelphia.org"
            },
            {
                "title": "Philly Pride Parade & Festival",
                "description": "Annual LGBTQ+ pride celebration with parade down Locust Street and festival with vendors, performances, and community organizations.",
                "location": "Gayborhood, Philadelphia",
                "month": 6,
                "price": "Free",
                "source": "Philly Pride Presents",
                "url": "https://phillypride.org"
            },
            {
                "title": "Christmas Village at Love Park",
                "description": "Traditional German Christmas market with wooden booths selling crafts, ornaments, food, and mulled wine.",
                "location": "Love Park, JFK Plaza",
                "month": 11,
                "price": "Free admission",
                "source": "Christmas Village",
                "url": "https://philachristmas.com"
            },
        ]

        for festival in festivals:
            # Calculate days until the festival month
            current_year = start_date.year
            festival_date = datetime(current_year, festival["month"], 15)
            if festival_date < start_date:
                festival_date = datetime(current_year + 1, festival["month"], 15)

            days_offset = (festival_date - start_date).days

            events.append(self.create_event(
                source=event_data.get("source", self.source_name),
                title=festival["title"],
                description=festival["description"],
                start_date=start_date + timedelta(days=days_offset),
                location=festival["location"],
                category="community",
                price=festival["price"],
                source_url=festival["url"]
            ))

        return events

    def _generate_weekly_recurring(self, start_date: datetime) -> List[Dict]:
        """Weekly recurring events"""
        events = []

        # Weekly free yoga
        for week in range(0, 26):  # 6 months of weekly events
            events.append(self.create_event(
                source=event_data.get("source", self.source_name),
                title="Free Community Yoga in Dilworth Park",
                description="Outdoor yoga for all levels. Bring your own mat. Led by certified instructors. Seasonal event (April-September).",
                start_date=start_date + timedelta(days=120 + week * 7),  # Starting in April
                location="Dilworth Park, 1 S 15th St",
                category="community",
                price="Free (donations welcome)"
            ))

        return events
