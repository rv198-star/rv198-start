import json
import subprocess
import sys
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class BacklogTests(unittest.TestCase):
    def test_repo_has_canonical_backlog_board(self) -> None:
        board_path = ROOT / "backlog" / "board.yaml"

        self.assertTrue(board_path.exists(), board_path)
        board = yaml.safe_load(board_path.read_text(encoding="utf-8"))

        self.assertEqual(board["schema_version"], "kiu.backlog/v0.1")
        self.assertIn("tickets", board)
        self.assertGreaterEqual(len(board["tickets"]), 5)
        self.assertTrue(
            any(ticket["target_version"] == "v0.6.0" for ticket in board["tickets"]),
            board["tickets"],
        )

    def test_show_backlog_cli_emits_summary_for_v06(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "show_backlog.py"),
                "--version",
                "v0.6.0",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)

        self.assertEqual(payload["version"], "v0.6.0")
        self.assertIn("summary", payload)
        self.assertGreaterEqual(payload["summary"]["ticket_count"], 1)
        self.assertIn("done", payload["summary"]["status_counts"])
        self.assertTrue(
            any(ticket["id"] == "KIU-620" for ticket in payload["tickets"]),
            payload["tickets"],
        )


if __name__ == "__main__":
    unittest.main()
