import csv
import json
import tempfile
import unittest
from pathlib import Path

from playstyle_tool import apply_to_all, load_roster, save_roster


class PlaystyleDataTests(unittest.TestCase):
    def test_adds_styles_to_every_player_without_duplicates(self):
        players = [
            {"name": "One", "playstyles": ["Finesse Shot"]},
            {"name": "Two", "playstyles": "Rapid"},
        ]

        changed = apply_to_all(players, ["Finesse Shot", "Power Shot"], ["Trivela"], "add")

        self.assertEqual(changed, 2)
        self.assertEqual(players[0]["playstyles"], ["Finesse Shot", "Power Shot"])
        self.assertEqual(players[1]["playstyles"], ["Rapid", "Finesse Shot", "Power Shot"])
        self.assertEqual(players[0]["playstyles_plus"], ["Trivela"])
        self.assertEqual(players[1]["playstyles_plus"], ["Trivela"])

    def test_replace_mode_replaces_both_style_fields(self):
        players = [{"playstyles": ["Rapid"], "playstyles_plus": ["Block"]}]

        apply_to_all(players, ["Power Shot"], [], "replace")

        self.assertEqual(players[0]["playstyles"], ["Power Shot"])
        self.assertEqual(players[0]["playstyles_plus"], [])

    def test_invalid_later_player_does_not_partially_update_roster(self):
        players = [
            {"name": "One", "playstyles": ["Rapid"]},
            {"name": "Two", "playstyles": {"unexpected": "value"}},
        ]

        with self.assertRaises(ValueError):
            apply_to_all(players, ["Jockey"], [], "add")

        self.assertEqual(players[0]["playstyles"], ["Rapid"])
        self.assertNotIn("playstyles_plus", players[0])

    def test_json_object_roster_preserves_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.json"
            output = Path(folder) / "output.json"
            source.write_text(json.dumps({"version": 1, "players": [{"id": 7}]}), encoding="utf-8")

            roster = load_roster(source)
            apply_to_all(roster.players, ["Jockey"], [], "add")
            save_roster(roster, output)

            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["version"], 1)
            self.assertEqual(result["players"][0]["playstyles"], ["Jockey"])

    def test_csv_round_trip_keeps_existing_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.csv"
            output = Path(folder) / "output.csv"
            source.write_text("id,name,club\n7,Player,Club\n", encoding="utf-8")

            roster = load_roster(source)
            apply_to_all(roster.players, ["Quick Step"], ["Rapid"], "add")
            save_roster(roster, output)

            with output.open(encoding="utf-8-sig", newline="") as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row["club"], "Club")
            self.assertEqual(row["playstyles"], "Quick Step")
            self.assertEqual(row["playstyles_plus"], "Rapid")


if __name__ == "__main__":
    unittest.main()