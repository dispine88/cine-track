"""Configuration tests that do not require an operating-system Keyring backend."""
import os
import unittest
from unittest.mock import patch

import config


class ConfigSecretTests(unittest.TestCase):
    def test_env_fallback_is_disabled_after_explicit_key_removal(self):
        with patch.object(config, "load_settings", return_value={"tmdb_api_key_disabled": True}), \
             patch.dict(os.environ, {"TMDB_API_KEY": "dev-key"}, clear=False), \
             patch.object(config, "get_secret", return_value=""):
            config.reload_secrets()
            self.assertEqual(config.TMDB_API_KEY, "")

    def test_env_fallback_remains_available_for_source_checkout(self):
        with patch.object(config, "load_settings", return_value={}), \
             patch.dict(os.environ, {"TMDB_API_KEY": "dev-key"}, clear=False), \
             patch.object(config, "get_secret", return_value=""):
            config.reload_secrets()
            self.assertEqual(config.TMDB_API_KEY, "dev-key")


if __name__ == "__main__":
    unittest.main()
