"""
Fix event URLs to point to specific event pages where available
"""

import sqlite3

def main():
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()

    # Get all events with URLs
    cursor.execute("SELECT id, title, source_url FROM events WHERE source_url IS NOT NULL")
    events = cursor.fetchall()

    updates_made = 0

    # URL mappings for events that should have specific pages
    url_fixes = {
        # Major annual events with dedicated pages
        "Philadelphia Marathon": "https://philadelphiamarathon.com",
        "Broad Street Run": "https://broadstreetrun.com",
        "Hot Chocolate 15K": "https://hotchocolate15k.com/philadelphia",
        "Philadelphia Distance Run": "https://philadelphiadistancerun.com",
        "Philly Run Fest": "https://phillyrunfest.com",
        "Gift of Life": "https://donors1.org",

        # Recurring events - these are fine with homepage URLs
        # "Wednesday Night Group Run": Keep philadelphiarunner.com
        # "First Friday": Keep oldcitydistrict.org
        # "Live Music at": Keep venue homepages

        # Festival and large events
        "Manayunk Arts Festival": "https://manayunk.com/arts-festival",
        "Welcome America": "https://welcomeamerica.com",
        "Christmas Village": "https://philachristmas.com",
        "Mummers Parade": "https://mummers.com",
        "Restaurant Week": "https://visitphilly.com/restaurant-week",
        "StrEAT Food Festival": "https://streatfoodfestival.com",
        "Nutcracker Ballet": "https://paballet.org/performances/the-nutcracker",
        "Thanksgiving Day Parade": "https://6abc.com/dunkin-donuts-thanksgiving-day-parade",
        "Philly Food Festival": "https://delawareriverwaterfront.com/events",
        "Folk Festival": "https://pfs.org",
        "Beer Week": "https://phillybeerweek.org",

        # Specific venue pages
        "Reading Terminal Market": "https://readingterminalmarket.org",
        "Yards Brewing": "https://yardsbrewing.com",
        "Philadelphia Museum of Art": "https://philamuseum.org",
        "Franklin Institute": "https://fi.edu",
        "Rooftop Cinema": "https://rooftopcinemaclub.com/philadelphia",
        "Walnut Street Theatre": "https://walnutstreettheatre.org",
        "Kimmel Cultural Campus": "https://kimmelculturalcampus.org",
        "Penn's Landing": "https://delawareriverwaterfront.com",
    }

    for event_id, title, current_url in events:
        new_url = None

        # Check if title matches any fix pattern
        for keyword, correct_url in url_fixes.items():
            if keyword.lower() in title.lower():
                # Only update if current URL is different
                if current_url != correct_url:
                    new_url = correct_url
                    break

        if new_url:
            cursor.execute("UPDATE events SET source_url = ? WHERE id = ?", (new_url, event_id))
            updates_made += 1
            print(f"Updated: {title[:50]} -> {new_url}")

    conn.commit()
    conn.close()

    print(f"\n✅ Updated {updates_made} event URLs")
    print("\nNote: Recurring events (weekly runs, music shows, etc.) correctly point to")
    print("venue/organization homepages since specific event pages don't exist.")
    print("\nInstagram handles are kept as-is since they're the primary source for many events.")

if __name__ == "__main__":
    main()
