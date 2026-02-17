import sys
sys.path.insert(0, '/Users/palaksharma/Phillycalendar/backend')

from database import EventDatabase
from scrapers.comprehensive_philly_scraper import ComprehensivePhillyScraper

db = EventDatabase()
scraper = ComprehensivePhillyScraper()

try:
    print("Generating comprehensive events...")
    events = scraper.scrape()
    print(f"Generated {len(events)} events")
    added = db.add_events_batch(events)
    print(f"Added {added} events to database")
    
    stats = db.get_stats()
    print(f"\nDatabase stats:")
    print(f"Total events: {stats['total_events']}")
    print(f"Upcoming events: {stats['upcoming_events']}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
