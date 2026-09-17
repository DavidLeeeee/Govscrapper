from __future__ import annotations

import hashlib
import ssl
import unittest

from src.scrapers._kisa import (
    BASE_URL,
    KISA_INTERMEDIATE_CA_PATH,
    _KisaTlsAdapter,
    _make_session,
)


class KisaTlsTest(unittest.TestCase):
    def test_official_intermediate_certificate_fingerprint(self) -> None:
        pem = KISA_INTERMEDIATE_CA_PATH.read_text(encoding="ascii")
        certificate_der = ssl.PEM_cert_to_DER_cert(pem)

        self.assertEqual(
            hashlib.sha256(certificate_der).hexdigest(),
            "c06e307f7cfc1d32fa72a4c033c87b90019af216f0775d64978a2eca6c8a230e",
        )

    def test_tls_adapter_is_scoped_to_kisa(self) -> None:
        session = _make_session()

        self.assertIsInstance(session.get_adapter(f"{BASE_URL}/403?page=1"), _KisaTlsAdapter)
        self.assertNotIsInstance(session.get_adapter("https://example.com"), _KisaTlsAdapter)


if __name__ == "__main__":
    unittest.main()
