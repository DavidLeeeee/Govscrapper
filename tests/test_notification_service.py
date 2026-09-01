from __future__ import annotations

import unittest

from src.services.notification_service import build_daily_scraping_message


class DailyNotificationMessageTest(unittest.TestCase):
    def test_today_notices_are_above_yesterday_notices(self) -> None:
        message = build_daily_scraping_message(
            [
                {"title": "어제 공고", "posted_at": "2026-08-31"},
                {"title": "오늘 공고", "posted_at": "2026-09-01"},
            ],
            [],
            [],
            total_mark_count=0,
            start_date="2026-08-31",
            end_date="2026-09-01",
        )

        self.assertLess(message.index("[오늘] 오늘 공고"), message.index("[어제] 어제 공고"))

    def test_regional_summary_places_today_above_yesterday(self) -> None:
        message = build_daily_scraping_message(
            [],
            [
                {"region": "부산", "posted_at": "2026-08-31"},
                {"region": "서울", "posted_at": "2026-09-01"},
            ],
            [],
            total_mark_count=0,
            start_date="2026-08-31",
            end_date="2026-09-01",
        )

        self.assertLess(message.index("[오늘] 서울 1건"), message.index("[어제] 부산 1건"))


if __name__ == "__main__":
    unittest.main()
