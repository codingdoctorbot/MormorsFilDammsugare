import unittest
from mormorsfildammsugare.geo.locator import ContinentLocator


class TestGeoLocator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.locator = ContinentLocator.get_default()

    def test_stockholm_lookup(self):
        # Stockholm coordinates: 59.3293, 18.0686
        loc = self.locator.locate(59.3293, 18.0686)
        self.assertIsNotNone(loc)
        self.assertEqual(loc.continent, "Europe")
        self.assertEqual(loc.country_name, "Sweden")

    def test_paris_lookup(self):
        # Paris coordinates: 48.8566, 2.3522
        loc = self.locator.locate(48.8566, 2.3522)
        self.assertIsNotNone(loc)
        self.assertEqual(loc.continent, "Europe")
        self.assertEqual(loc.country_name, "France")


if __name__ == "__main__":
    unittest.main()
