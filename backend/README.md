# Philadelphia Calendar Backend

Automated web scraping backend for Philadelphia events.

## Quick Start

### 1. Install Python

Make sure you have Python 3.8+ installed:

```bash
python3 --version
```

### 2. Install Dependencies

```bash
cd backend
pip3 install -r requirements.txt
```

### 3. Run the Server

```bash
python3 app.py
```

The server will start at `http://localhost:5000` and automatically scrape events on startup.

## API Endpoints

Once running, you can test the API:

### Get All Events
```bash
curl http://localhost:5000/events
```

### Get Upcoming Events
```bash
curl http://localhost:5000/events/upcoming
```

### Trigger Manual Scraping
```bash
curl -X POST http://localhost:5000/scrape
```

### Get Statistics
```bash
curl http://localhost:5000/stats
```

## How It Works

1. **Scrapers** (`scrapers/`) - Extract events from Philadelphia websites
   - `eventbrite_scraper.py` - Scrapes Eventbrite Philadelphia
   - `visit_philly_scraper.py` - Scrapes Visit Philadelphia

2. **Database** (`database.py`) - SQLite database for storing events
   - Automatically deduplicates events
   - Stores event details and metadata

3. **API** (`app.py`) - Flask REST API
   - Serves events to iOS app
   - Provides search and filtering
   - Triggers scraping on demand

4. **Scheduler** (`scheduler.py`) - Automatic scraping
   - Runs scrapers every 12 hours
   - Cleans up old events
   - Background processing

## Using with iOS App

### For Local Development (Same Computer)

1. Start the backend:
   ```bash
   python3 app.py
   ```

2. In Xcode, update `APIService.swift`:
   ```swift
   private let baseURL = "http://localhost:5000"
   ```

3. Run the iOS app in simulator
4. Events will sync from your local backend

### For Real iPhone (Network Access)

1. Find your computer's IP address:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

2. Update `APIService.swift`:
   ```swift
   private let baseURL = "http://YOUR_IP:5000"
   ```

3. Make sure your iPhone and computer are on the same WiFi network

## Deployment Options

### Option 1: Railway (Easiest - Free Tier)

1. Create account at https://railway.app
2. Install Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

3. Deploy:
   ```bash
   cd backend
   railway login
   railway init
   railway up
   ```

4. Get your deployment URL and update iOS app

### Option 2: Render (Free Tier)

1. Create account at https://render.com
2. Create new "Web Service"
3. Connect your GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `python app.py`

### Option 3: Heroku (Paid but Easy)

1. Create account at https://heroku.com
2. Install Heroku CLI
3. Deploy:
   ```bash
   cd backend
   heroku create philly-calendar-api
   git push heroku main
   ```

### Option 4: Keep Running Locally

Just leave `python3 app.py` running on your computer. Works great for personal use!

## Adding More Scrapers

To add a new event source:

1. Create new scraper in `scrapers/`:

```python
# scrapers/my_source_scraper.py
from .base_scraper import BaseScraper

class MySourceScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            source_name="My Source",
            source_url="https://example.com/events"
        )

    def scrape(self):
        events = []
        soup = self.fetch_page(self.source_url)

        # Your scraping logic here
        for event_elem in soup.find_all('div', class_='event'):
            title = event_elem.find('h2').get_text()
            # ... extract other fields

            event = self.create_event(
                title=title,
                description=description,
                start_date=start_date,
                location=location,
                category='community'
            )
            events.append(event)

        return events
```

2. Add to `scrapers/__init__.py`:

```python
from .my_source_scraper import MySourceScraper

SCRAPERS = [
    EventbriteScraper,
    VisitPhillyScraper,
    MySourceScraper,  # Add here
]
```

3. Restart the server

## Troubleshooting

### "Connection refused" error in iOS app
- Make sure backend is running (`python3 app.py`)
- Check the IP address in `APIService.swift`
- Verify firewall isn't blocking port 5000

### No events scraped
- Some websites may have changed their HTML structure
- Check the logs for errors
- Try accessing the websites directly in a browser
- Some sites may block scrapers

### "Module not found" errors
- Run `pip3 install -r requirements.txt` again
- Make sure you're in the `backend` directory

### Events not updating
- Manually trigger scraping: `curl -X POST http://localhost:5000/scrape`
- Check scheduler is running
- Verify websites are accessible

## Files Overview

```
backend/
├── app.py                  # Flask API server (START HERE)
├── database.py             # SQLite database operations
├── scheduler.py            # Automatic scraping scheduler
├── requirements.txt        # Python dependencies
├── events.db              # SQLite database (created automatically)
│
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py    # Base class for scrapers
│   ├── eventbrite_scraper.py
│   └── visit_philly_scraper.py
│
└── README.md              # This file
```

## Development Tips

### Test a Single Scraper

```python
from scrapers import EventbriteScraper

scraper = EventbriteScraper()
events = scraper.scrape()
print(f"Found {len(events)} events")
for event in events[:3]:
    print(event['title'])
```

### View Database

```bash
sqlite3 events.db
sqlite> SELECT COUNT(*) FROM events;
sqlite> SELECT title, start_date FROM events LIMIT 5;
sqlite> .quit
```

### Monitor Logs

The server prints logs as it runs:
```
INFO:__main__:Starting Philadelphia Events Calendar API...
INFO:__main__:Running initial scrape...
INFO:scrapers.eventbrite_scraper:Scraping Eventbrite Philadelphia...
INFO:scrapers.eventbrite_scraper:Found 20 event cards
INFO:scrapers.eventbrite_scraper:Scraped: Philadelphia Marathon Weekend
...
```

## Next Steps

1. ✅ Get backend running locally
2. ✅ Test API endpoints with curl
3. ✅ Connect iOS app to backend
4. ⏳ Add more scrapers for Philadelphia sources
5. ⏳ Deploy to free hosting
6. ⏳ Set up automatic scraping schedule

## Support

- Backend issues: Check logs in terminal
- Scraping issues: Websites may have changed structure
- iOS connection: Verify IP address and network

## License

For personal use. Be respectful of website terms of service when scraping.
