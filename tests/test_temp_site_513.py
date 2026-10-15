"""Offline HTML/owner boundary checks for the existing HTTPS PHP site."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import temp_site_513 as site
import temp_db_513_bridge as bridge
import unittest


def html(checks):
    return "<table>" + "".join("<tr><td>" + name + "</td><td>PASS</td><td>" + evidence + "</td></tr>"
                             for name, evidence in checks) + "</table>"


class SiteTests(unittest.TestCase):
    def test_extract_csrf(self):
        page = site.PageParser()
        page.feed('<input type="hidden" name="csrf" value="' + "a"*64 + '">')
        self.assertEqual(page.csrf, "a"*64)

    def test_require_database_and_account(self):
        h = html([("Connection", "connected"), ("Database identity", bridge.DATABASE+" / MariaDB 10.11"),
                  ("Authenticated account", bridge.USERNAME+"@%")])
        self.assertEqual(site.verify_page(h, "status")["verified_checks"], 3)
        with self.assertRaises(bridge.ProbeBlocked):
            site.verify_page(h.replace(bridge.DATABASE, "wrong_database"), "status")
        self.assertFalse(site.verify_page(h.replace(bridge.USERNAME, "wrong_user"), "status")["account_verified"])

    def test_full_test_requires_all_checks_and_cleanup(self):
        items = [(x, ("Test table and all its records removed." if x == "Cleanup" else
                      bridge.DATABASE + " / MariaDB" if x == "Database identity" else
                      bridge.USERNAME + "@%" if x == "Authenticated account" else "PASS"))
                 for x in site.EXPECTED_CHECKS]
        self.assertTrue(site.verify_page(html(items), "full-test")["cleanup_verified"])
        with self.assertRaises(bridge.ProbeBlocked):
            site.verify_page(html(items[:-1]), "full-test")

    def test_only_owner_could_trigger_full_test(self):
        payload = {"action":"opened","repository":{"full_name":bridge.REPO},
                   "issue":{"number":9,"user":{"login":bridge.OWNER},
                            "title":"TEMPTEST-513: full-test",
                            "body":"TEMPTEST_513_V1\noperation=full-test\ndatabase="+bridge.DATABASE}}
        self.assertEqual(site.issue_command(payload), (9, "full-test"))
        payload["issue"]["user"]["login"] = "other"
        with self.assertRaises(bridge.ProbeBlocked):
            site.issue_command(payload)


if __name__ == "__main__":
    unittest.main()
