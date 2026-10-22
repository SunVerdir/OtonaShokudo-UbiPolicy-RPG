import unittest
import re
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from otona_shokudo_rpg import __version__, cli
from otona_shokudo_rpg.engine import Game
from otona_shokudo_rpg.report import build_report, to_markdown
from otona_shokudo_rpg.rules import load_ruleset


class CliTest(unittest.TestCase):
    def setUp(self):
        self.rs = load_ruleset()

    def test_action_menu_marks_overlapping_tags_without_recommending(self):
        game = Game(self.rs, seed=7)
        game.begin_round()
        output = StringIO()
        with redirect_stdout(output):
            cli.show_actions(game)
        text = output.getvalue()
        self.assertIn("◇", text)
        self.assertIn("今回の困りごとタグと重なる", text)
        self.assertIn("おすすめ・解決保証ではありません", text)
        self.assertIn("食事", text)

    def test_pass_skips_reason_entry_and_records_no_objection(self):
        game = Game(self.rs, seed=7, rounds=1, players=["ニックネーム"])
        output = StringIO()
        with patch("otona_shokudo_rpg.cli.ask", side_effect=["p", "", "", ""]) as ask_mock:
            with redirect_stdout(output):
                cli.play(game, interactive=True)
        self.assertEqual(game.records[0].action_ids, [])
        self.assertEqual(game.records[0].reason, "")
        self.assertEqual(game.records[0].player, "")
        self.assertEqual(game.objections, [])
        self.assertEqual(ask_mock.call_count, 4)  # pass once; then the three optional closing memories
        self.assertIn("担当をパス", output.getvalue())
        report = to_markdown(build_report(game))
        self.assertIn("担当者名は非記録", report)
        self.assertNotIn("ニックネーム", report)

    def test_quick_mode_runs_three_rounds_and_prints_replay_recipe(self):
        output = StringIO()
        with redirect_stdout(output):
            result = cli.main(["--quick", "--demo", "--seed", "7"])
        text = output.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("第3/3ラウンド", text)
        self.assertIn("otona-shokudo-rpg --seed 7 --rounds 3", text)

    def test_report_labels_indicator_as_virtual_and_preserves_replay_seed(self):
        game = Game(self.rs, seed=29, rounds=3, players=["ニックネーム"])
        game.begin_round()
        game.resolve_round([], reason="")
        rep = build_report(game)
        md = to_markdown(rep)
        self.assertIn("ゲーム内の仮想指標", md)
        self.assertIn("実際の住民の感謝・満足度・同意・政策効果", md)
        self.assertIn("otona-shokudo-rpg --seed 29 --rounds 3", md)
        recipe = next(line for line in md.splitlines() if line.startswith("`otona-shokudo-rpg"))
        self.assertNotIn("ニックネーム", recipe)

    def test_package_version_matches_project_metadata(self):
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"))
        self.assertIsNotNone(match)
        self.assertEqual(__version__, match.group(1))


if __name__ == "__main__":
    unittest.main()
