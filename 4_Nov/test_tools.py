"""Free local checks. Does not use the OpenAI API or modify real tickets.json."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tools


class ToolTests(unittest.TestCase):
    def test_vpn_search(self):
        results = tools.search_knowledge_base("My VPN disconnects at home")
        self.assertTrue(results["results"])
        self.assertEqual(results["results"][0]["id"], "KB001")

    def test_teams_search(self):
        results = tools.search_knowledge_base("Teams slow and CPU hot on Mac")
        self.assertEqual(results["results"][0]["id"], "KB003")

    def test_ticket_is_rejected_without_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "tickets.json"
            p.write_text("[]", encoding="utf-8")
            with patch.object(tools, "TICKETS_PATH", p):
                result = tools.create_support_ticket(
                    "VPN issue", "Network", "Medium", confirm=lambda _: "n"
                )
            self.assertFalse(result["created"])
            self.assertEqual(json.loads(p.read_text()), [])

    def test_ticket_is_saved_with_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "tickets.json"
            p.write_text("[]", encoding="utf-8")
            with patch.object(tools, "TICKETS_PATH", p):
                result = tools.create_support_ticket(
                    "VPN issue", "Network", "Medium", confirm=lambda _: "y"
                )
            self.assertTrue(result["created"])
            self.assertEqual(result["ticket"]["id"], "IT-0001")
            self.assertEqual(len(json.loads(p.read_text())), 1)


if __name__ == "__main__":
    unittest.main()
