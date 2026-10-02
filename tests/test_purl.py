import unittest

from license_check.models import Coordinate
from license_check.purl import PurlError, package_key, parse_purl


class ParsePurlTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(
            parse_purl("pkg:npm/lodash@4.17.21"),
            Coordinate("npm", "lodash", "4.17.21"),
        )

    def test_scoped_npm_name(self):
        self.assertEqual(
            parse_purl("pkg:npm/@babel/core@7.0.0"),
            Coordinate("npm", "@babel/core", "7.0.0"),
        )

    def test_qualifiers_and_subpath_stripped(self):
        self.assertEqual(
            parse_purl("pkg:pypi/requests@2.31.0?arch=any#sub"),
            Coordinate("pypi", "requests", "2.31.0"),
        )

    def test_no_version(self):
        self.assertEqual(
            parse_purl("pkg:npm/lodash"),
            Coordinate("npm", "lodash", None),
        )

    def test_package_key_drops_version(self):
        self.assertEqual(package_key("pkg:pypi/exemption@2.31.0"), "pkg:pypi/exemption")

    def test_rejects_non_purl(self):
        for bad in ["", "lodash@1.0.0", "pkg:", "pkg:npm", "pkg:/name@1"]:
            with self.assertRaises(PurlError):
                parse_purl(bad)


if __name__ == "__main__":
    unittest.main()
