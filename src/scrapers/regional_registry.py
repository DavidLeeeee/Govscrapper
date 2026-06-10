from src.scrapers._bizinfo_region import BizInfoRegionScraper
from src.scrapers.scrap_interface import Scraper


REGIONAL_SCRAPER_INSTANCES: list[Scraper] = [
    BizInfoRegionScraper(),
]

REGIONAL_SCRAPERS = {
    scraper.source_name: scraper.scrape  # type: ignore[attr-defined]
    for scraper in REGIONAL_SCRAPER_INSTANCES
}

REGIONAL_SOURCE_NAMES = {
    scraper.source_name: scraper.display_name  # type: ignore[attr-defined]
    for scraper in REGIONAL_SCRAPER_INSTANCES
}
