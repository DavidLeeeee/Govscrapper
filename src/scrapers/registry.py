from src.services.storage_service import Notice


def scrape_placeholder() -> list[Notice]:
    return []


SCRAPERS = {
    "placeholder": scrape_placeholder,
}
