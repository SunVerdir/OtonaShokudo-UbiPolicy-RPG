import unittest
from otona_shokudo_rpg.engine import Game, bot_choose
from otona_shokudo_rpg.report import build_report, to_markdown
from otona_shokudo_rpg.rules import load_ruleset, validate_ruleset


class RulesTest(unittest.TestCase):
    def test_default_rules_are_valid(self):
        self.assertEqual(validate_ruleset(load_ruleset()), [])

    def test_eight_modules_present(self):
        rs = load_ruleset()
        self.assertEqual([m.id for m in rs.modules], list(range(1, 9)))
        for m in rs.modules:  # 公開物の「段階」表記は必須（実装済みと誤解させない）
            self.assertTrue(m.status, m.name)


class GameTest(unittest.TestCase):
    def setUp(self):
        self.rs = load_ruleset()

    def full_bot_game(self, seed):
        g = Game(self.rs, seed=seed)
        while not g.is_over:
            g.begin_round()
            ids, taste = bot_choose(g)
            g.resolve_round(ids, taste)
        return g

    def test_game_completes_and_resources_stay_in_range(self):
        for seed in range(30):
            g = self.full_bot_game(seed)
            self.assertEqual(len(g.records), g.total_rounds)
            self.assertTrue(all(0 <= v <= g.cap for v in g.res.values()))

    def test_first_event_is_great_depression(self):
        g = Game(self.rs, seed=3)
        self.assertEqual(g.begin_round().id, "depression")

    def test_seed_is_reproducible(self):
        a, b = Game(self.rs, seed=5), Game(self.rs, seed=5)
        self.assertEqual([e.id for e in a._queue], [e.id for e in b._queue])

    def test_cannot_overspend(self):
        g = Game(self.rs, seed=1)
        g.begin_round()
        g.res["people"] = 0
        with self.assertRaises(ValueError):
            g.resolve_round(["a3_market"])

    def test_max_actions_and_duplicates(self):
        g = Game(self.rs, seed=1)
        g.begin_round()
        with self.assertRaises(ValueError):
            g.resolve_round(["a1_table", "a1_table"])
        with self.assertRaises(ValueError):
            g.resolve_round(["a1_table", "a2_meal", "a3_market"])

    def test_taste_test_skipped_reduces_thanks(self):
        def play(taste):
            g = Game(self.rs, seed=1)
            g.begin_round()
            g.res.update(food=9, budget=9, people=9, infra=9)
            g.resolve_round(["a5_alloc"], {"a5_alloc": taste})
            return g
        checked, skipped = play(True), play(False)
        self.assertEqual(skipped.skipped_taste, 1)
        self.assertEqual(checked.skipped_taste, 0)
        self.assertEqual(build_report(checked)["total_thanks"] - build_report(skipped)["total_thanks"], 1 if build_report(checked)["raw_thanks"] > 0 else 0)

    def test_pass_round_is_allowed(self):
        g = Game(self.rs, seed=2)
        g.begin_round()
        rec = g.resolve_round([])
        self.assertEqual(rec.action_ids, [])
        self.assertEqual(len(rec.unmet), len(rec.event.needs))

    def test_no_loser_even_if_nothing_is_done(self):
        g = Game(self.rs, seed=4)
        while not g.is_over:
            g.begin_round(); g.resolve_round([])
        md = to_markdown(build_report(g))
        self.assertIn("次の検証課題", md)

    def test_objection_and_early_quit_report(self):
        g = Game(self.rs, seed=2, players=["ゆい", "そら"])
        g.begin_round(); g.resolve_round([])
        g.add_objection("このルールは、子どもに難しいと思う")
        g.quit_early = True
        rep = build_report(g)
        self.assertEqual(rep["played_rounds"], 1)
        self.assertEqual(len(rep["objections"]), 1)
        self.assertIn("途中離脱", to_markdown(rep))

    def test_players_rotate(self):
        g = Game(self.rs, players=["ゆい", "そら"], seed=1)
        self.assertEqual([g.player_for_round(i) for i in (1, 2, 3)], ["ゆい", "そら", "ゆい"])


if __name__ == "__main__":
    unittest.main()
