"""差异对比 & 过滤器测试"""
import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from deploy_tool.core.sync.filters import ExcludeFilter


class TestExcludeFilter(unittest.TestCase):

    def test_dir_exclusion(self):
        f = ExcludeFilter([".git/", "node_modules/"])
        self.assertTrue(f.is_excluded(".git/config"))
        self.assertTrue(f.is_excluded("node_modules/foo/bar.js"))
        self.assertTrue(f.is_excluded("src/node_modules/react/index.js"))
        self.assertFalse(f.is_excluded("src/app.js"))

    def test_file_pattern(self):
        f = ExcludeFilter(["*.log", "*.pyc"])
        self.assertTrue(f.is_excluded("error.log"))
        self.assertTrue(f.is_excluded("app.pyc"))
        self.assertFalse(f.is_excluded("app.js"))

    def test_wildcard_pattern(self):
        f = ExcludeFilter([".env*", "*.swp"])
        self.assertTrue(f.is_excluded(".env"))
        self.assertTrue(f.is_excluded(".env.local"))
        self.assertTrue(f.is_excluded(".env.production"))
        self.assertFalse(f.is_excluded("environment.conf"))

    def test_empty_pattern(self):
        f = ExcludeFilter([])
        self.assertFalse(f.is_excluded("anything.txt"))


if __name__ == "__main__":
    unittest.main()
