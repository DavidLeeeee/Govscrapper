from __future__ import annotations

import unittest
from datetime import date

from src.services.alarm_service import daily_alarm_skip_reason


class DailyAlarmPolicyTest(unittest.TestCase):
    def test_weekend_skips_notification(self) -> None:
        target_date = date(2026, 9, 5)
        notices = [{"posted_at": target_date.isoformat()}]

        self.assertEqual(daily_alarm_skip_reason(target_date, notices, []), "weekend")

    def test_public_holiday_skips_notification(self) -> None:
        target_date = date(2026, 1, 1)
        notices = [{"posted_at": target_date.isoformat()}]

        reason = daily_alarm_skip_reason(target_date, notices, [])

        self.assertIsNotNone(reason)
        self.assertTrue(str(reason).startswith("public_holiday:"))

    def test_no_today_notice_skips_notification(self) -> None:
        target_date = date(2026, 9, 1)
        notices = [{"posted_at": "2026-08-31"}]

        self.assertEqual(daily_alarm_skip_reason(target_date, notices, []), "no_new_notices_today")

    def test_today_regional_notice_allows_notification(self) -> None:
        target_date = date(2026, 9, 1)
        regional_notices = [{"posted_at": target_date.isoformat()}]

        self.assertIsNone(daily_alarm_skip_reason(target_date, [], regional_notices))


if __name__ == "__main__":
    unittest.main()
