import unittest

from freshdesk_mcp.config import ConfigurationError, FreshdeskSettings


class FreshdeskSettingsTests(unittest.TestCase):
    def test_domain_without_scheme_defaults_to_https(self) -> None:
        settings = FreshdeskSettings(api_key="abc", domain="example.freshdesk.com")
        self.assertEqual(settings.base_url, "https://example.freshdesk.com")

    def test_domain_with_scheme_is_preserved(self) -> None:
        settings = FreshdeskSettings(api_key="abc", domain="https://example.freshdesk.com/")
        self.assertEqual(settings.base_url, "https://example.freshdesk.com")

    def test_from_env_requires_key_and_domain(self) -> None:
        with self.assertRaises(ConfigurationError) as ctx:
            FreshdeskSettings.from_env({})
        self.assertIn("FRESHDESK_API_KEY", str(ctx.exception))

    def test_from_env_parses_timeout(self) -> None:
        settings = FreshdeskSettings.from_env(
            {
                "FRESHDESK_API_KEY": "abc",
                "FRESHDESK_DOMAIN": "example.freshdesk.com",
                "FRESHDESK_TIMEOUT_SECONDS": "12.5",
            }
        )
        self.assertEqual(settings.timeout_seconds, 12.5)


if __name__ == "__main__":
    unittest.main()
