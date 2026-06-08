from src.scrapers._iris import IrisBtinSituScraper
from src.scrapers._kisa import KisaBidScraper
from src.scrapers._nia import NiaBidScraper
from src.scrapers._seoul import SeoulRndScraper
from src.scrapers.scrap_interface import Scraper


SCRAPER_INSTANCES: list[Scraper] = [
    IrisBtinSituScraper(),
    KisaBidScraper(),
    NiaBidScraper(),
    SeoulRndScraper(),
]

SCRAPERS = {
    scraper.target.source_name: scraper.scrape
    for scraper in SCRAPER_INSTANCES
}
