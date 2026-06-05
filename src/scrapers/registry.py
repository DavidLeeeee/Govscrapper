from src.scrapers._kisa import KisaBidScraper
from src.scrapers.scrap_interface import Scraper


SCRAPER_INSTANCES: list[Scraper] = [
    KisaBidScraper(),
]

SCRAPERS = {
    scraper.target.source_name: scraper.scrape
    for scraper in SCRAPER_INSTANCES
}
