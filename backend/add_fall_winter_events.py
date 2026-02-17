"""
Add more fall and winter events to ensure good coverage through the year
"""

import sqlite3
from datetime import datetime, timedelta

def add_event(cursor, title, description, start_date, location, category, price, source, source_url):
    """Add an event to the database"""
    cursor.execute('''
        INSERT INTO events (title, description, start_date, location, category, price, source, source_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, description, start_date.isoformat(), location, category, price, source, source_url))

def main():
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()

    # Base date for calculating event dates
    base_date = datetime(2026, 9, 1)
    events_added = 0

    # September Events
    september_events = [
        {
            "title": "Philadelphia Folk Festival",
            "date_offset": 5,
            "time": (10, 0),
            "description": "Annual three-day celebration of folk music and culture. Camping, workshops, crafts, and performances by renowned folk artists from around the world.",
            "location": "Old Pool Farm, Upper Salford Township, PA",
            "category": "music",
            "price": "$50-$200",
            "source": "Philadelphia Folksong Society",
            "url": "https://pfs.org"
        },
        {
            "title": "Philly Free Streets - Fall Edition",
            "date_offset": 12,
            "time": (10, 0),
            "description": "Car-free streets celebration through Philadelphia neighborhoods. Biking, walking, fitness activities, and community fun.",
            "location": "Various neighborhoods, Philadelphia, PA",
            "category": "community",
            "price": "Free",
            "source": "Philly Free Streets (@phillyFreeStreets)",
            "url": "https://instagram.com/phillyFreeStreets"
        },
        {
            "title": "Fall Run Fest 5K",
            "date_offset": 20,
            "time": (8, 0),
            "description": "Autumn running festival with 5K, 10K, and half marathon options. Scenic fall foliage routes through Philadelphia parks.",
            "location": "Fairmount Park, Philadelphia, PA",
            "category": "running",
            "price": "$40-$60",
            "source": "Philadelphia Runner",
            "url": "https://philadelphiarunner.com"
        },
    ]

    for event in september_events:
        date = base_date.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # October Events
    october_base = datetime(2026, 10, 1)
    october_events = [
        {
            "title": "Philadelphia Open Studio Tours",
            "date_offset": 3,
            "time": (12, 0),
            "description": "Free self-guided tours of artist studios across Philadelphia. Meet artists, see works in progress, and explore creative spaces.",
            "location": "Various locations, Philadelphia, PA",
            "category": "artsAndCulture",
            "price": "Free",
            "source": "Mural Arts Philadelphia (@muralarts)",
            "url": "https://instagram.com/muralarts"
        },
        {
            "title": "Philly Beer Week - Fall Edition",
            "date_offset": 15,
            "time": (17, 0),
            "description": "Week-long celebration of Philadelphia's craft beer scene with special releases, brewery events, and beer dinners.",
            "location": "Breweries across Philadelphia",
            "category": "foodAndDrink",
            "price": "Varies by event",
            "source": "Philly Beer Week (@phillyBeerWeek)",
            "url": "https://instagram.com/phillyBeerWeek"
        },
        {
            "title": "Philadelphia Marathon",
            "date_offset": 25,
            "time": (7, 0),
            "description": "Philadelphia's premier marathon event. Full marathon, half marathon, 8K, and kids fun run. Scenic course through historic Philadelphia.",
            "location": "Starting at Benjamin Franklin Parkway, Philadelphia, PA",
            "category": "running",
            "price": "$100-$150",
            "source": "Philadelphia Runner",
            "url": "https://philadelphiamarathon.com"
        },
    ]

    for event in october_events:
        date = october_base.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # November Events
    november_base = datetime(2026, 11, 1)
    november_events = [
        {
            "title": "Philadelphia Museum of Art Fall Exhibition",
            "date_offset": 7,
            "time": (10, 0),
            "description": "New contemporary art exhibition opening. Featured artists from Philadelphia and beyond.",
            "location": "Philadelphia Museum of Art, 2600 Benjamin Franklin Pkwy",
            "category": "artsAndCulture",
            "price": "$25",
            "source": "Franklin Institute (@franklininstitute)",
            "url": "https://instagram.com/franklininstitute"
        },
        {
            "title": "Thanksgiving Day Parade",
            "date_offset": 26,
            "time": (9, 0),
            "description": "Philadelphia's annual Thanksgiving Day Parade featuring floats, marching bands, and performances. One of the oldest parades in the country.",
            "location": "Benjamin Franklin Parkway, Philadelphia, PA",
            "category": "community",
            "price": "Free",
            "source": "City of Philadelphia (@philly)",
            "url": "https://instagram.com/philly"
        },
        {
            "title": "Small Business Saturday Markets",
            "date_offset": 28,
            "time": (10, 0),
            "description": "Shop local at pop-up markets featuring Philadelphia small businesses, makers, and artisans. Support your community!",
            "location": "Various neighborhoods, Philadelphia, PA",
            "category": "community",
            "price": "Free admission",
            "source": "Made in Philadelphia (@madeinphiladelphia)",
            "url": "https://instagram.com/madeinphiladelphia"
        },
    ]

    for event in november_events:
        date = november_base.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # December Events
    december_base = datetime(2026, 12, 1)
    december_events = [
        {
            "title": "Christmas Village in Philadelphia",
            "date_offset": 1,
            "time": (12, 0),
            "description": "Holiday market in LOVE Park featuring European-style vendors, food, drinks, and festive atmosphere. Open through Christmas.",
            "location": "LOVE Park, 1599 JFK Blvd, Philadelphia, PA",
            "category": "community",
            "price": "Free admission",
            "source": "LOVE Park Philly (@loveparkphilly)",
            "url": "https://instagram.com/loveparkphilly"
        },
        {
            "title": "New Year's Eve Fireworks & Celebration",
            "date_offset": 31,
            "time": (20, 0),
            "description": "Ring in the new year with fireworks over the Delaware River, live music, and celebrations across the city.",
            "location": "Penn's Landing, Philadelphia, PA",
            "category": "community",
            "price": "Free",
            "source": "Delaware River Waterfront (@delriverfront)",
            "url": "https://instagram.com/delriverfront"
        },
        {
            "title": "The Nutcracker Ballet",
            "date_offset": 15,
            "time": (19, 0),
            "description": "Pennsylvania Ballet's annual performance of The Nutcracker. Holiday tradition featuring world-class dancers and Tchaikovsky's beloved score.",
            "location": "Academy of Music, Philadelphia, PA",
            "category": "artsAndCulture",
            "price": "$35-$150",
            "source": "Visit Philadelphia (@visitphilly)",
            "url": "https://instagram.com/visitphilly"
        },
    ]

    for event in december_events:
        date = december_base.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # January 2027 Events
    january_base = datetime(2027, 1, 1)
    january_events = [
        {
            "title": "New Year's Day Mummers Parade",
            "date_offset": 1,
            "time": (9, 0),
            "description": "Philadelphia's legendary Mummers Parade! String bands, fancy brigades, and elaborate costumes celebrate New Year's Day.",
            "location": "Broad Street, Philadelphia, PA",
            "category": "community",
            "price": "Free",
            "source": "City of Philadelphia (@philly)",
            "url": "https://instagram.com/philly"
        },
        {
            "title": "Winter Restaurant Week",
            "date_offset": 17,
            "time": (17, 0),
            "description": "Special prix-fixe menus at over 100 Philadelphia restaurants. Explore the city's diverse culinary scene at great prices.",
            "location": "Restaurants across Philadelphia",
            "category": "foodAndDrink",
            "price": "$20-$60",
            "source": "Visit Philadelphia",
            "url": "https://visitphilly.com"
        },
    ]

    for event in january_events:
        date = january_base.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    conn.commit()
    conn.close()

    print(f"✅ Successfully added {events_added} fall and winter events:")
    print("   - September: 3 events")
    print("   - October: 3 events")
    print("   - November: 3 events")
    print("   - December: 3 events")
    print("   - January 2027: 2 events")
    print()
    print("These major events will now be visible when filtering by month!")

if __name__ == "__main__":
    main()
