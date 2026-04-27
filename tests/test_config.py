import os
import tempfile
import unittest
from pathlib import Path

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

    def test_from_env_loads_dotenv_when_env_not_provided(self) -> None:
        old_cwd = os.getcwd()
        old_api_key = os.environ.get("FRESHDESK_API_KEY")
        old_domain = os.environ.get("FRESHDESK_DOMAIN")
        old_timeout = os.environ.get("FRESHDESK_TIMEOUT_SECONDS")

        try:
            os.environ.pop("FRESHDESK_API_KEY", None)
            os.environ.pop("FRESHDESK_DOMAIN", None)
            os.environ.pop("FRESHDESK_TIMEOUT_SECONDS", None)

            with tempfile.TemporaryDirectory() as temp_dir:
                Path(temp_dir, ".env").write_text(
                    "FRESHDESK_API_KEY=from-dotenv\n"
                    "FRESHDESK_DOMAIN=dotenv.freshdesk.com\n"
                    "FRESHDESK_TIMEOUT_SECONDS=45\n",
                    encoding="utf-8",
                )
                os.chdir(temp_dir)
                settings = FreshdeskSettings.from_env()

            self.assertEqual(settings.api_key, "from-dotenv")
            self.assertEqual(settings.domain, "dotenv.freshdesk.com")
            self.assertEqual(settings.timeout_seconds, 45.0)
        finally:
            os.chdir(old_cwd)
            self._restore_env("FRESHDESK_API_KEY", old_api_key)
            self._restore_env("FRESHDESK_DOMAIN", old_domain)
            self._restore_env("FRESHDESK_TIMEOUT_SECONDS", old_timeout)

    @staticmethod
    def _restore_env(key: str, value: str | None) -> None:
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
