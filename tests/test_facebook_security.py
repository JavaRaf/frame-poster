import unittest

from src.facebook import sanitize_for_logging


class FacebookSecurityTests(unittest.TestCase):
    def test_sanitize_for_logging_redacts_access_token(self) -> None:
        raw = "Client error '403 Forbidden' for url 'https://graph.facebook.com/v21.0/me/photos?access_token=SECRET_TOKEN&message=hi'"

        sanitized = sanitize_for_logging(raw)

        self.assertIn("access_token=[REDACTED]", sanitized)
        self.assertNotIn("SECRET_TOKEN", sanitized)


if __name__ == "__main__":
    unittest.main()
