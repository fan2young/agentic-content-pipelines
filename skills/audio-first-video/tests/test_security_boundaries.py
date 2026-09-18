import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/synthesize_dashscope.py"


@unittest.skipUnless(importlib.util.find_spec("dashscope"), "dashscope dependency is not installed")
class ProviderHostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("synthesize_dashscope", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(cls.module)

    def test_official_host_is_accepted(self):
        self.assertEqual(
            self.module.normalize_api_host("https://dashscope.aliyuncs.com", False),
            "dashscope.aliyuncs.com",
        )

    def test_http_and_embedded_credentials_are_rejected(self):
        with self.assertRaises(ValueError):
            self.module.normalize_api_host("http://dashscope.aliyuncs.com", False)
        with self.assertRaises(ValueError):
            self.module.normalize_api_host("https://user:pass@dashscope.aliyuncs.com", False)

    def test_custom_host_requires_explicit_override(self):
        with self.assertRaises(ValueError):
            self.module.normalize_api_host("https://example.invalid", False)
        self.assertEqual(
            self.module.normalize_api_host("https://example.invalid", True),
            "example.invalid",
        )


if __name__ == "__main__":
    unittest.main()
