"""
Sample Data Scraper - Generates sample Philadelphia events
This ensures you always have events to see while we work on real scrapers
"""

from .base_scraper import BaseScraper
from datetime import datetime, timedelta
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class SampleDataScraper(BaseScraper):
    """Generate sample Philadelphia events"""

    def __init__(self):
        super().__init__(
            source_name="Sample Philadelphia Events",
            source_url="https://philadelphia.example.com"
        )

    def scrape(self) -> List[Dict]:
        """Generate sample events for Philadelphia"""
        events = []
        now = datetime.now()

        # Running Events
        events.append(self.create_event(
            title="Philadelphia Marathon Weekend",
            description="Join thousands of runners for the annual Philadelphia Marathon. The course showcases the city's historic landmarks and finishes on Benjamin Franklin Parkway with spectacular views of the Art Museum.",
            start_date=now.replace(hour=7, minute=0, second=0, microsecond=0) + timedelta(days=15),
            location="Benjamin Franklin Parkway, Philadelphia, PA",
            category="running",
            price="$100-$150 registration",
            source_url="https://philadelphiamarathon.com"
        ))

        events.append(self.create_event(
            title="Weekly Kelly Drive Group Run",
            description="Free community group run along scenic Kelly Drive. All paces welcome! Meet at Boathouse Row.",
            start_date=now.replace(hour=18, minute=0, second=0, microsecond=0) + timedelta(days=3),
            location="Boathouse Row, Kelly Drive, Philadelphia, PA",
            category="running",
            price="Free",
            source_url="https://philadelphiarunner.com"
        ))

        # Arts & Culture Events
        events.append(self.create_event(
            title="First Friday Art Walk - Old City",
            description="Explore Old City's vibrant art scene with gallery openings, artist receptions, and special exhibitions. Free and open to the public on the first Friday of every month.",
            start_date=now.replace(hour=18, minute=0, second=0, microsecond=0) + timedelta(days=5),
            location="Old City Arts District, Philadelphia, PA",
            category="artsAndCulture",
            price="Free",
            source_url="https://oldcitydistrict.org"
        ))

        events.append(self.create_event(
            title="Philadelphia Museum of Art - New Exhibition Opening",
            description="Grand opening of contemporary art exhibition featuring local and international artists. Special curator talk at 6 PM.",
            start_date=now.replace(hour=18, minute=0, second=0, microsecond=0) + timedelta(days=7),
            location="Philadelphia Museum of Art, 2600 Benjamin Franklin Pkwy",
            category="artsAndCulture",
            price="$25 adults, $23 seniors, Free for members",
            source_url="https://philamuseum.org"
        ))

        events.append(self.create_event(
            title="Live Theater: A Philadelphia Story",
            description="Classic performance at the Walnut Street Theatre, America's oldest theater. Evening performance with pre-show reception.",
            start_date=now.replace(hour=19, minute=30, second=0, microsecond=0) + timedelta(days=10),
            location="Walnut Street Theatre, 825 Walnut St, Philadelphia, PA",
            category="artsAndCulture",
            price="$35-$75",
            source_url="https://walnutstreettheatre.org"
        ))

        # Music Events
        events.append(self.create_event(
            title="Jazz Night at Chris' Jazz Cafe",
            description="Live jazz performances featuring local musicians and touring artists. Intimate venue with full dinner menu and cocktails.",
            start_date=now.replace(hour=20, minute=0, second=0, microsecond=0) + timedelta(days=2),
            location="Chris' Jazz Cafe, 1421 Sansom St, Philadelphia, PA",
            category="music",
            price="$20-$30 cover",
            source_url="https://chrisjazzcafe.com"
        ))

        events.append(self.create_event(
            title="Concert at The Fillmore Philadelphia",
            description="National touring act performing at this historic music venue. Doors open at 7 PM, show starts at 8 PM.",
            start_date=now.replace(hour=20, minute=0, second=0, microsecond=0) + timedelta(days=12),
            location="The Fillmore Philadelphia, 29 E Allen St",
            category="music",
            price="$45-$65",
            source_url="https://thefillmorephilly.com"
        ))

        events.append(self.create_event(
            title="Free Outdoor Concert - Dilworth Park",
            description="Summer concert series featuring local bands. Bring a blanket and enjoy music with skyline views. Food trucks available.",
            start_date=now.replace(hour=18, minute=0, second=0, microsecond=0) + timedelta(days=6),
            location="Dilworth Park, 1 S 15th St, Philadelphia, PA",
            category="music",
            price="Free",
            source_url="https://centercityphila.org/explore-center-city/dilworth-park"
        ))

        # Food & Drink Events
        events.append(self.create_event(
            title="Reading Terminal Market Food Tour",
            description="Guided culinary tour of Reading Terminal Market sampling the best foods from various vendors. Learn about the market's rich history while tasting Philly favorites.",
            start_date=now.replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=4),
            location="Reading Terminal Market, 51 N 12th St, Philadelphia, PA",
            category="foodAndDrink",
            price="$50 per person",
            source_url="https://readingterminalmarket.org"
        ))

        events.append(self.create_event(
            title="Craft Beer Tasting at Yards Brewing",
            description="Sample seasonal and year-round beers at one of Philadelphia's premier breweries. Tour includes behind-the-scenes look at brewing process.",
            start_date=now.replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=8),
            location="Yards Brewing Company, 500 Spring Garden St, Philadelphia, PA",
            category="foodAndDrink",
            price="$25 includes tastings",
            source_url="https://yardsbrewing.com"
        ))

        events.append(self.create_event(
            title="Philly Food Festival",
            description="Annual celebration of Philadelphia's diverse food scene. Sample dishes from 50+ restaurants, food trucks, and local vendors.",
            start_date=now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=20),
            location="Penn's Landing, Columbus Blvd, Philadelphia, PA",
            category="foodAndDrink",
            price="$10 admission, food tickets sold separately",
            source_url="https://delawareriverwaterfront.com"
        ))

        # Community Events
        events.append(self.create_event(
            title="Clark Park Farmers Market",
            description="Weekly farmers market featuring fresh produce, baked goods, artisanal products, and live music. Supporting local farmers and vendors since 2001.",
            start_date=now.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1),
            location="Clark Park, 43rd & Baltimore Ave, Philadelphia, PA",
            category="community",
            price="Free admission",
            source_url="https://thefoodtrust.org"
        ))

        events.append(self.create_event(
            title="Rittenhouse Square Community Day",
            description="Family-friendly festival with activities, live music, food vendors, and kids' activities. Celebrating Philadelphia's most beautiful urban park.",
            start_date=now.replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=9),
            location="Rittenhouse Square, 210 W Rittenhouse Square, Philadelphia, PA",
            category="community",
            price="Free",
            source_url="https://centercityphila.org"
        ))

        events.append(self.create_event(
            title="South Street Spring Festival",
            description="Annual street festival along historic South Street featuring live music on multiple stages, art vendors, food stands, and entertainment.",
            start_date=now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=25),
            location="South Street, Philadelphia, PA",
            category="community",
            price="Free",
            source_url="https://southstreet.com"
        ))

        events.append(self.create_event(
            title="Free Community Yoga in Love Park",
            description="Weekly outdoor yoga session for all levels. Bring your own mat and water. Led by certified instructors from local studios.",
            start_date=now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=2),
            location="LOVE Park, 1599 JFK Blvd, Philadelphia, PA",
            category="community",
            price="Free (donations welcome)",
            source_url="https://lovepark.org"
        ))

        logger.info(f"Generated {len(events)} sample Philadelphia events")
        return events
