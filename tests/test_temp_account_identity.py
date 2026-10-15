"""Offline regression tests for MariaDB's USER() vs CURRENT_USER() display forms.

No credentials, network or database access.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import temp_db_513_bridge as bridge
import temp_site_513 as site


def page_for(reported_account):
    values = [
        ("Connection", "Connected from this PHP hosting server."),
        ("Database identity", bridge.DATABASE + " / 11.8.0-MariaDB"),
        ("Authenticated account", reported_account),
    ]
    return "<table>" + "".join(
        "<tr><td>" + name + "</td><td>PASS</td><td>" + result + "</td></tr>"
        for name, result in values
    ) + "</table>"


class MariaDBIdentityTests(unittest.TestCase):
    def test_host_qualification_does_not_break_match(self):
        # Merely changing the @host portion cannot explain the live mismatch.
        for suffix in ("@%", "@localhost", "@127.0.0.1", "@php-host"):
            with self.subTest(suffix=suffix):
                outcome = site.verify_page(page_for(bridge.USERNAME + suffix), "status")
                self.assertTrue(outcome["account_verified"])
                self.assertIsNone(outcome["identity_warning"])

    def test_different_privilege_account_is_not_accepted(self):
        # CURRENT_USER() can legitimately refer to a different matched grant account.
        for reported in ("another_user@localhost", "@localhost", "proxy_account@%"):
            with self.subTest(account=reported):
                outcome = site.verify_page(page_for(reported), "status")
                self.assertFalse(outcome["account_verified"])
                self.assertEqual(outcome["identity_warning"], "SITE_ACCOUNT_DIFFERENT")

    def test_identity_check_requires_expected_database_even_for_read_only(self):
        with self.assertRaises(bridge.ProbeBlocked):
            site.verify_page(page_for(bridge.USERNAME + "@%").replace(
                bridge.DATABASE, "not_our_database"), "status")


if __name__ == "__main__":
    unittest.main()
