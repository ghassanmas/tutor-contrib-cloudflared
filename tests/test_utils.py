import unittest

from tutorcloudflared import utils

class UtilsTests(unittest.TestCase):
    def test_get_root_domain(self):
        self.assertEqual(utils.get_first_level_domain("one.two.example.com"),"example.com")
