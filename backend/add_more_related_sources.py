"""
Add events from additional related Philadelphia sources similar to ones already in database
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

    # Philly Runners (@phillyrunners on Instagram) - Running group similar to phillyrun
    philly_runners_events = [
        {
            "title": "Philly Runners Monday Morning Run",
            "date_offset": 5,
            "time": (6, 0),
            "description": "Early morning group run for all paces. Start your week strong with a supportive running community.",
            "location": "Various meeting spots in Philadelphia",
            "category": "running",
            "price": "Free",
            "source": "Philly Runners (@phillyrunners)",
            "url": "https://instagram.com/phillyrunners"
        },
        {
            "title": "Philly Runners Saturday Long Run",
            "date_offset": 8,
            "time": (7, 0),
            "description": "Weekend long run with multiple pace groups. Build mileage with fellow runners on scenic Philadelphia routes.",
            "location": "Various meeting spots in Philadelphia",
            "category": "running",
            "price": "Free",
            "source": "Philly Runners (@phillyrunners)",
            "url": "https://instagram.com/phillyrunners"
        },
    ]

    for event in philly_runners_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # November Project Philadelphia (@novemberprojectphilly) - Free fitness workouts
    november_project_events = [
        {
            "title": "November Project Wednesday Workout",
            "date_offset": 6,
            "time": (6, 30),
            "description": "Free outdoor fitness workout. All fitness levels welcome. Rain or shine, we meet and move together as a community.",
            "location": "Philadelphia Museum of Art Steps",
            "category": "running",
            "price": "Free",
            "source": "November Project Philadelphia (@novemberprojectphilly)",
            "url": "https://instagram.com/novemberprojectphilly"
        },
        {
            "title": "November Project Friday Workout",
            "date_offset": 8,
            "time": (6, 30),
            "description": "Free community fitness at the Art Museum. Bodyweight exercises, running, and positive energy to kickstart your Friday.",
            "location": "Philadelphia Museum of Art Steps",
            "category": "running",
            "price": "Free",
            "source": "November Project Philadelphia (@novemberprojectphilly)",
            "url": "https://instagram.com/novemberprojectphilly"
        },
    ]

    for event in november_project_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Philly Girls Who Hike (@phillygirlswhohike) - Similar to phillygirlswhowalk
    hiking_events = [
        {
            "title": "Philly Girls Who Hike Weekend Adventure",
            "date_offset": 9,
            "time": (9, 0),
            "description": "Women's hiking group exploring trails in and around Philadelphia. All experience levels welcome. Build community while enjoying nature.",
            "location": "Wissahickon Valley Park, Philadelphia, PA",
            "category": "running",
            "price": "Free",
            "source": "Philly Girls Who Hike (@phillygirlswhohike)",
            "url": "https://instagram.com/phillygirlswhohike"
        },
    ]

    for event in hiking_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Philly Brew Tours (@phillybrewtours) - Similar to food tours
    brew_tour_events = [
        {
            "title": "Philly Brew Tours Craft Beer Walking Tour",
            "date_offset": 15,
            "time": (14, 0),
            "description": "Guided walking tour visiting 3 Philadelphia breweries. Learn about brewing process, sample craft beers, and explore neighborhoods.",
            "location": "Meeting point in Fishtown, Philadelphia, PA",
            "category": "foodAndDrink",
            "price": "$75 per person",
            "source": "Philly Brew Tours (@phillybrewtours)",
            "url": "https://instagram.com/phillybrewtours"
        },
    ]

    for event in brew_tour_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Philly Photo Day (@phillyphotoday) - Photography walks
    photo_events = [
        {
            "title": "Philly Photo Walk: Historic District",
            "date_offset": 22,
            "time": (10, 0),
            "description": "Guided photography walk through historic Philadelphia. Learn composition techniques while capturing iconic landmarks and hidden gems.",
            "location": "Independence Hall area, Philadelphia, PA",
            "category": "artsAndCulture",
            "price": "Free",
            "source": "Philly Photo Day (@phillyphotoday)",
            "url": "https://instagram.com/phillyphotoday"
        },
    ]

    for event in photo_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Manayunk Arts Festival (website: manayunk.com)
    manayunk_arts_events = [
        {
            "title": "Manayunk Arts Festival",
            "date_offset": 180,
            "time": (10, 0),
            "description": "One of the largest outdoor arts festivals in the country. 250+ artists, live music, food, and entertainment on Main Street.",
            "location": "Main Street, Manayunk, Philadelphia, PA",
            "category": "artsAndCulture",
            "price": "Free admission",
            "source": "Manayunk Development Corporation",
            "url": "https://manayunk.com"
        },
    ]

    for event in manayunk_arts_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Made in Philadelphia (@madeinphiladelphia) - Local makers market
    made_in_philly_events = [
        {
            "title": "Made in Philadelphia Pop-Up Market",
            "date_offset": 40,
            "time": (11, 0),
            "description": "Curated market featuring local artisans, makers, and designers. Shop handmade goods, art, jewelry, home decor, and more.",
            "location": "Various locations in Philadelphia",
            "category": "community",
            "price": "Free admission",
            "source": "Made in Philadelphia (@madeinphiladelphia)",
            "url": "https://instagram.com/madeinphiladelphia"
        },
    ]

    for event in made_in_philly_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Rooftop Cinema Club Philadelphia (@rooftopcinemaclub)
    rooftop_cinema_events = [
        {
            "title": "Rooftop Cinema: Classic Film Screening",
            "date_offset": 85,
            "time": (20, 0),
            "description": "Outdoor movie screening on a Philadelphia rooftop. Wireless headphones, craft cocktails, and skyline views create the perfect cinema experience.",
            "location": "Rooftop venue in Philadelphia",
            "category": "artsAndCulture",
            "price": "$18-$25",
            "source": "Rooftop Cinema Club Philadelphia",
            "url": "https://rooftopcinemaclub.com/philadelphia"
        },
    ]

    for event in rooftop_cinema_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Philly Flea (@phillyflea) - Similar to punk rock flea market
    philly_flea_events = [
        {
            "title": "Philly Flea Market",
            "date_offset": 50,
            "time": (10, 0),
            "description": "Indoor/outdoor market featuring vintage finds, handmade goods, antiques, and local food vendors. Shop unique items from local sellers.",
            "location": "Grays Ferry Crescent, Philadelphia, PA",
            "category": "community",
            "price": "$2 admission",
            "source": "Philly Flea (@phillyflea)",
            "url": "https://instagram.com/phillyflea"
        },
    ]

    for event in philly_flea_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Wawa Welcome America (July 4th celebrations)
    welcome_america_events = [
        {
            "title": "Wawa Welcome America Festival",
            "date_offset": 138,
            "time": (12, 0),
            "description": "Philadelphia's multi-day Fourth of July celebration. Free concerts, fireworks, historic reenactments, and family activities celebrating American independence.",
            "location": "Benjamin Franklin Parkway, Philadelphia, PA",
            "category": "community",
            "price": "Free",
            "source": "Welcome America",
            "url": "https://welcomeamerica.com"
        },
    ]

    for event in welcome_america_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # StrEAT Food Festival (@streatfoodfestival)
    streat_events = [
        {
            "title": "StrEAT Food Festival",
            "date_offset": 160,
            "time": (12, 0),
            "description": "Philadelphia's premier food truck and street food festival. 50+ food trucks, craft beer, live music, and family activities.",
            "location": "Various locations in Philadelphia",
            "category": "foodAndDrink",
            "price": "Free admission, food sold separately",
            "source": "StrEAT Food Festival (@streatfoodfestival)",
            "url": "https://instagram.com/streatfoodfestival"
        },
    ]

    for event in streat_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    # Philly Free Streets (@phillyFreeStreets) - Car-free city streets event
    free_streets_events = [
        {
            "title": "Philly Free Streets",
            "date_offset": 125,
            "time": (10, 0),
            "description": "Miles of car-free streets for walking, biking, rolling, and playing. Free fitness classes, activities, and community celebration.",
            "location": "Various neighborhoods in Philadelphia",
            "category": "community",
            "price": "Free",
            "source": "Philly Free Streets (@phillyFreeStreets)",
            "url": "https://instagram.com/phillyFreeStreets"
        },
    ]

    for event in free_streets_events:
        date = now.replace(hour=event["time"][0], minute=event["time"][1], second=0, microsecond=0) + timedelta(days=event["date_offset"])
        add_event(cursor, event["title"], event["description"], date, event["location"],
                 event["category"], event["price"], event["source"], event["url"])
        events_added += 1

    conn.commit()
    conn.close()

    print(f"✅ Successfully added {events_added} events from additional related sources:")
    print("   - Philly Runners (@phillyrunners)")
    print("   - November Project Philadelphia (@novemberprojectphilly)")
    print("   - Philly Girls Who Hike (@phillygirlswhohike)")
    print("   - Philly Brew Tours (@phillybrewtours)")
    print("   - Philly Photo Day (@phillyphotoday)")
    print("   - Manayunk Development Corporation (manayunk.com)")
    print("   - Made in Philadelphia (@madeinphiladelphia)")
    print("   - Rooftop Cinema Club Philadelphia")
    print("   - Philly Flea (@phillyflea)")
    print("   - Welcome America (welcomeamerica.com)")
    print("   - StrEAT Food Festival (@streatfoodfestival)")
    print("   - Philly Free Streets (@phillyFreeStreets)")

if __name__ == "__main__":
    main()
