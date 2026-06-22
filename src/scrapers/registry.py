from src.scrapers._iris import IrisBtinSituScraper
from src.scrapers._kglobal import KglobalScraper
from src.scrapers._kisa import KisaBidScraper
from src.scrapers._nia import NiaBidScraper
from src.scrapers._nipa import NipaScraper
from src.scrapers._seoul import SeoulRndScraper
from src.scrapers.scrap_interface import Scraper


def build_scraper_instances(max_pages: int | None = None) -> list[Scraper]:
    if max_pages is None:
        return [
            IrisBtinSituScraper(),
            KglobalScraper(),
            KisaBidScraper(),
            NiaBidScraper(),
            NipaScraper(),
            SeoulRndScraper(),
        ]

    return [
        IrisBtinSituScraper(max_pages=max_pages),
        KglobalScraper(max_pages=max_pages),
        KisaBidScraper(max_pages=max_pages),
        NiaBidScraper(max_pages=max_pages),
        NipaScraper(max_pages=max_pages),
        SeoulRndScraper(max_pages=max_pages),
    ]


def build_scrapers(max_pages: int | None = None) -> dict[str, Scraper]:
    return {
        scraper.target.source_name: scraper.scrape
        for scraper in build_scraper_instances(max_pages=max_pages)
    }


SCRAPER_INSTANCES: list[Scraper] = build_scraper_instances()

SCRAPERS = build_scrapers()
