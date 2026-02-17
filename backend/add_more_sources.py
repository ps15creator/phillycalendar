"""
Add events from Love Park Philly and other similar Philadelphia sources
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

    now = datetime.now()
    events_added = 0

    # Love Park Philly (@loveparkphilly) - Community events, yoga, fitness
    love_park_events = [
        {
            "title": "LOVE Park Yoga Sessions",
            "description": "Free outdoor yoga in the heart of Center City. All levels welcome. Bring your own mat and enjoy yoga with views of City Hall.",
            "date_offset": 3,
            "time": (9, 0),
            "location": "LOVE Park, 1599 JFK Blvd, Philadelphia, PA",
            "category": "community",
            "price": "Free",
            "source": "LOVE Park Philly (@loveparkphilly)",
            "url": "https://instagram.com/loveparkphilly"
        },
        {
            "title": "LOVE Park Winter Village",
            "date_offset": 280,
            "time": (16, 0),
            "description": "Holiday village featuring local vendors, seasonal treats, ice skating, and festive decorations. Family-friendly winter celebration in Center City.",
            "location": "LOVE Park, 1599 JFK Blvd, Philadelphia, PA",
            "category": "community",
            "price": "Free admission, activities vary",
            "source": "LOVE Park Philly (@loveparkphilly)",
            "url": "https://instagram.com/loveparkphilly"
        },
        {
            "title": "LOVE Park Fitness Bootcamp",
            "date_offset": 10,
            "time": (7, 0),
            "description": "Morning outdoor fitness bootcamp. High-intensity interval training in the park. All fitness levels encouraged to participate.",
            "location": "LOVE Park, 1599 JFK Blvd, Philadelphia, PA",
            "category": "running",
            "price": "Free",
            "source": "LOVE Park Philly (@loveparkphilly)",
            "url": "https://instagram.com/loveparkphilly"
        },
    ]

    for event in love_park_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Spruce Street Harbor Park (@sprucestharborpark) - Seasonal waterfront park
    spruce_events = [
        {
            "title": "Spruce Street Harbor Park Opening Day",
            "date_offset": 90,
            "time": (12, 0),
            "description": "Seasonal waterfront park opens for the season! Hammocks, boardwalk, food vendors, beer garden, games, and stunning Delaware River views.",
            "location": "Spruce Street Harbor Park, 301 S Christopher Columbus Blvd",
            "category": "community",
            "price": "Free admission",
            "source": "Spruce Street Harbor Park (@sprucestharborpark)",
            "url": "https://instagram.com/sprucestharborpark"
        },
        {
            "title": "Movie Nights at Spruce Street Harbor Park",
            "date_offset": 120,
            "time": (20, 0),
            "description": "Free outdoor movie screenings on the waterfront. Bring blankets and enjoy classic films with Delaware River views.",
            "location": "Spruce Street Harbor Park, 301 S Christopher Columbus Blvd",
            "category": "community",
            "price": "Free",
            "source": "Spruce Street Harbor Park (@sprucestharborpark)",
            "url": "https://instagram.com/sprucestharborpark"
        },
    ]

    for event in spruce_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Philly 5K Series (@philly5kseries) - Running events
    running_series_events = [
        {
            "title": "Philly 5K Spring Race",
            "date_offset": 60,
            "time": (8, 0),
            "description": "5K race through scenic Philadelphia routes. Chip-timed, post-race refreshments, and finisher medals for all participants.",
            "location": "Various locations in Philadelphia",
            "category": "running",
            "price": "$35-$45",
            "source": "Philly 5K Series (@philly5kseries)",
            "url": "https://instagram.com/philly5kseries"
        },
        {
            "title": "Philly 5K Summer Night Run",
            "date_offset": 150,
            "time": (19, 0),
            "description": "Evening 5K run with glow sticks and illuminated course. Fun summer running event with live DJ and after-party.",
            "location": "Various locations in Philadelphia",
            "category": "running",
            "price": "$35-$45",
            "source": "Philly 5K Series (@philly5kseries)",
            "url": "https://instagram.com/philly5kseries"
        },
    ]

    for event in running_series_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Schuylkill Banks (@schuylkillbanks) - River trail events
    schuylkill_events = [
        {
            "title": "Schuylkill Banks Boardwalk Walk",
            "date_offset": 7,
            "time": (10, 0),
            "description": "Guided walk along the scenic Schuylkill River boardwalk. Learn about the river's history and ecology while enjoying waterfront views.",
            "location": "Schuylkill Banks, 25th & Locust Streets",
            "category": "community",
            "price": "Free",
            "source": "Schuylkill Banks (@schuylkillbanks)",
            "url": "https://instagram.com/schuylkillbanks"
        },
        {
            "title": "Schuylkill Banks River Ride",
            "date_offset": 45,
            "time": (9, 0),
            "description": "Group bike ride along the Schuylkill River Trail. All skill levels welcome. Bring your own bike and helmet.",
            "location": "Schuylkill Banks, 25th & Locust Streets",
            "category": "running",
            "price": "Free",
            "source": "Schuylkill Banks (@schuylkillbanks)",
            "url": "https://instagram.com/schuylkillbanks"
        },
    ]

    for event in schuylkill_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Philly Beer Week (@phillyBeerWeek) - Beer and food events
    beer_week_events = [
        {
            "title": "Philly Beer Week Opening Tap",
            "date_offset": 180,
            "time": (17, 0),
            "description": "Annual 10-day celebration of beer culture kicks off! Over 1,000 events at 100+ venues across the region. Opening ceremony with special beer releases.",
            "location": "Various venues across Philadelphia",
            "category": "foodAndDrink",
            "price": "Varies by event",
            "source": "Philly Beer Week (@phillyBeerWeek)",
            "url": "https://instagram.com/phillyBeerWeek"
        },
    ]

    for event in beer_week_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Franklin Institute (@franklininstitute) - Science museum events
    franklin_events = [
        {
            "title": "Franklin Institute Science After Hours",
            "date_offset": 30,
            "time": (19, 0),
            "description": "Adults-only evening at the science museum. Explore exhibits, enjoy cocktails, live music, and hands-on science demonstrations.",
            "location": "The Franklin Institute, 222 N 20th St",
            "category": "artsAndCulture",
            "price": "$35-$45",
            "source": "Franklin Institute (@franklininstitute)",
            "url": "https://instagram.com/franklininstitute"
        },
        {
            "title": "Franklin Institute Planetarium Show",
            "date_offset": 14,
            "time": (15, 0),
            "description": "Immersive planetarium experience exploring the cosmos. State-of-the-art digital dome theater with stunning space visuals.",
            "location": "The Franklin Institute, 222 N 20th St",
            "category": "artsAndCulture",
            "price": "$20-$30",
            "source": "Franklin Institute (@franklininstitute)",
            "url": "https://instagram.com/franklininstitute"
        },
    ]

    for event in franklin_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Penn's Landing (@pennslandingcorp) - Waterfront events
    penns_landing_events = [
        {
            "title": "Penn's Landing Summer Concert Series",
            "date_offset": 100,
            "time": (18, 30),
            "description": "Free outdoor concerts on the Delaware River waterfront. Local and touring bands perform with stunning sunset views.",
            "location": "Penn's Landing, Columbus Boulevard",
            "category": "music",
            "price": "Free",
            "source": "Penn's Landing (@pennslandingcorp)",
            "url": "https://instagram.com/pennslandingcorp"
        },
    ]

    for event in penns_landing_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Fairmount Park Conservancy (@myphillypark) - Parks and outdoor events
    fairmount_events = [
        {
            "title": "Fairmount Park Trail Run",
            "date_offset": 35,
            "time": (8, 0),
            "description": "Guided trail run through historic Fairmount Park. Explore wooded trails and scenic overlooks. All paces welcome.",
            "location": "Fairmount Park, Philadelphia, PA",
            "category": "running",
            "price": "Free",
            "source": "Fairmount Park Conservancy (@myphillypark)",
            "url": "https://instagram.com/myphillypark"
        },
        {
            "title": "Fairmount Park Outdoor Yoga",
            "date_offset": 20,
            "time": (10, 0),
            "description": "Free yoga sessions in the park. Connect with nature while practicing mindfulness and movement. Bring your own mat.",
            "location": "Fairmount Park, Philadelphia, PA",
            "category": "community",
            "price": "Free",
            "source": "Fairmount Park Conservancy (@myphillypark)",
            "url": "https://instagram.com/myphillypark"
        },
    ]

    for event in fairmount_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # The Oval (@theovalphl) - Summer park on Ben Franklin Parkway
    oval_events = [
        {
            "title": "The Oval Summer Opening",
            "date_offset": 95,
            "time": (15, 0),
            "description": "Free summer park on the Parkway opens! Urban beach, hammocks, games, food trucks, live music, and outdoor movies all summer long.",
            "location": "Eakins Oval, Benjamin Franklin Parkway",
            "category": "community",
            "price": "Free",
            "source": "The Oval (@theovalphl)",
            "url": "https://instagram.com/theovalphl"
        },
        {
            "title": "The Oval Movie Night",
            "date_offset": 110,
            "time": (20, 0),
            "description": "Free outdoor movie screening on the Parkway. Bring blankets and enjoy a film under the stars with the Philadelphia skyline as backdrop.",
            "location": "Eakins Oval, Benjamin Franklin Parkway",
            "category": "community",
            "price": "Free",
            "source": "The Oval (@theovalphl)",
            "url": "https://instagram.com/theovalphl"
        },
    ]

    for event in oval_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Philly Night Market (@phillynightmarket) - Asian night market
    night_market_events = [
        {
            "title": "Philly Night Market",
            "date_offset": 140,
            "time": (18, 0),
            "description": "Asian-inspired night market featuring 50+ vendors with food, drinks, arts, crafts, and live performances. Celebrate AAPI culture and community.",
            "location": "Chinatown, Philadelphia, PA",
            "category": "foodAndDrink",
            "price": "Free admission",
            "source": "Philly Night Market (@phillynightmarket)",
            "url": "https://instagram.com/phillynightmarket"
        },
    ]

    for event in night_market_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Philly Bike Ride (@phillybikeride) - Annual bike event
    bike_ride_events = [
        {
            "title": "Philly Bike Ride",
            "date_offset": 200,
            "time": (7, 30),
            "description": "Car-free bike ride through Philadelphia streets. 15 or 30-mile routes showcasing the city's neighborhoods and landmarks. All ages and abilities welcome.",
            "location": "Starting at Eakins Oval, Philadelphia, PA",
            "category": "running",
            "price": "$35-$50",
            "source": "Philly Bike Ride (@phillybikeride)",
            "url": "https://instagram.com/phillybikeride"
        },
    ]

    for event in bike_ride_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Citizens Bank Park (@phillies) - Baseball and stadium events
    phillies_events = [
        {
            "title": "Phillies Opening Day",
            "date_offset": 70,
            "time": (13, 5),
            "description": "Philadelphia Phillies Opening Day! Start of baseball season at Citizens Bank Park. Celebrate America's pastime with festive pre-game ceremonies.",
            "location": "Citizens Bank Park, 1 Citizens Bank Way",
            "category": "community",
            "price": "$20-$150",
            "source": "Philadelphia Phillies (@phillies)",
            "url": "https://instagram.com/phillies"
        },
        {
            "title": "Phillies Fireworks Night",
            "date_offset": 170,
            "time": (19, 5),
            "description": "Phillies game with post-game fireworks show. Enjoy baseball followed by spectacular fireworks display over the stadium.",
            "location": "Citizens Bank Park, 1 Citizens Bank Way",
            "category": "community",
            "price": "$20-$100",
            "source": "Philadelphia Phillies (@phillies)",
            "url": "https://instagram.com/phillies"
        },
    ]

    for event in phillies_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    conn.commit()
    conn.close()

    print(f"✅ Successfully added {events_added} events from new sources:")
    print("   - LOVE Park Philly (@loveparkphilly)")
    print("   - Spruce Street Harbor Park (@sprucestharborpark)")
    print("   - Philly 5K Series (@philly5kseries)")
    print("   - Schuylkill Banks (@schuylkillbanks)")
    print("   - Philly Beer Week (@phillyBeerWeek)")
    print("   - Franklin Institute (@franklininstitute)")
    print("   - Penn's Landing (@pennslandingcorp)")
    print("   - Fairmount Park Conservancy (@myphillypark)")
    print("   - The Oval (@theovalphl)")
    print("   - Philly Night Market (@phillynightmarket)")
    print("   - Philly Bike Ride (@phillybikeride)")
    print("   - Philadelphia Phillies (@phillies)")

if __name__ == "__main__":
    main()
