"""
Philadelphia Calendar Event Scrapers
"""

from .base_scraper import BaseScraper
from .eventbrite_scraper import EventbriteScraper
from .visit_philly_scraper import VisitPhillyScraper
from .do215_scraper import Do215Scraper
from .sample_data_scraper import SampleDataScraper
from .comprehensive_philly_scraper import ComprehensivePhillyScraper
from .milkboy_scraper import MilkBoyScraper
from .johnnybrendas_scraper import JohnnyBrendasScraper
from .fillmore_scraper import FillmoreScraper
from .reading_terminal_scraper import ReadingTerminalScraper
from .barnes_scraper import BarnesScraper
from .muralarts_scraper import MuralArtsScraper

# Active scrapers fetching real events from live websites
SCRAPERS = [
    EventbriteScraper,      # Eventbrite Philadelphia (6 categories, PA-only)
    Do215Scraper,           # Do215 Philadelphia events guide (30-day calendar)
    MilkBoyScraper,         # MilkBoy Philadelphia music venue (JSON-LD)
    JohnnyBrendasScraper,   # Johnny Brenda's Fishtown music venue (HTML)
    FillmoreScraper,        # The Fillmore Philadelphia music venue
    ReadingTerminalScraper, # Reading Terminal Market events (JSON-LD)
    BarnesScraper,          # Barnes Foundation exhibitions & events (HTML)
    # MuralArtsScraper is excluded — site is JS-rendered, returns 0 events without headless browser
]

__all__ = [
    'BaseScraper', 'EventbriteScraper', 'VisitPhillyScraper',
    'Do215Scraper', 'SampleDataScraper', 'ComprehensivePhillyScraper',
    'MilkBoyScraper', 'JohnnyBrendasScraper', 'FillmoreScraper',
    'ReadingTerminalScraper', 'BarnesScraper', 'MuralArtsScraper', 'SCRAPERS'
]
