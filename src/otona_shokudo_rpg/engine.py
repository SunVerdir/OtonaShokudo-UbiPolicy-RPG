"""ゲームの進行ロジック（入出力を持たない純粋なロジック）。

設計方針（第七巻の記述に対応）:
- サイコロで政策を決めない。政策は人が選び、選んだ「理由」を残す。
- 想定外はイベントカードで起きる（順番だけ乱数。シードで再現可能）。
- 「有り難う！」は困りごとタグへの対応数を表す仮想指標で、実際の感謝や政策効果ではない。
- AIの提案を含む行動は、人の「味見（確認）」を省くとゲーム内の対応指標が減る。
- 異論の記録と途中離脱は、いつでもできる。
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from .rules import RESOURCES, Action, Event, Ruleset


@dataclass
class RoundRecord:
    number: int
    event: Event
    role_id: str
    player: str
    action_ids: list
    reason: str
    taste: dict          # action_id -> 味見したか
    thanks_gained: dict  # role_id -> 増えた有り難う
    unmet: list          # 応えられなかった Need
    met: list            # 応えられた Need


class Game:
    def __init__(self, ruleset: Ruleset, players: Optional[list] = None,
                 seed: Optional[int] = None, rounds: Optional[int] = None):
        self.rs = ruleset
        self.seed = seed if seed is not None else random.SystemRandom().getrandbits(32)
        self.rng = random.Random(self.seed)
        self.players = players or ["あなた"]
        s = ruleset.settings
        self.cap = s["resource_cap"]
        self.apa = s["actions_per_round"]
        self.res = {k: min(self.cap, s["start"].get(k, 0)) for k in RESOURCES}
        self.total_rounds = min(rounds or s["rounds"], len(ruleset.events))
        self.round = 0
        self.thanks = {r.id: 0 for r in ruleset.roles}
        self.records: list = []
        self.objections: list = []
        self.memories: dict = {}
        self.used_modules: Counter = Counter()
        self.skipped_taste = 0
        self.current_event: Optional[Event] = None
        self.quit_early = False
        self._queue = self._build_queue()

    # ---- 準備 -------------------------------------------------------------
    def _build_queue(self) -> list:
        firsts = [e for e in self.rs.events if e.first]
        rest = [e for e in self.rs.events if not e.first]
        self.rng.shuffle(rest)
        return (firsts + rest)[: self.total_rounds]

    # ---- 状態 -------------------------------------------------------------
    def _apply(self, delta: dict) -> None:
        for k, v in delta.items():
            if k in self.res:
                self.res[k] = max(0, min(self.cap, self.res[k] + v))

    @property
    def is_over(self) -> bool:
        return len(self.records) >= self.total_rounds

    def role_for_round(self, n: int):
        return self.rs.roles[(n - 1) % len(self.rs.roles)]

    def player_for_round(self, n: int) -> str:
        return self.players[(n - 1) % len(self.players)]

    # ---- ラウンド進行 -----------------------------------------------------
    def begin_round(self) -> Event:
        if self.is_over:
            raise RuntimeError("ゲームは終了しています。")
        self.round = len(self.records) + 1
        self.current_event = self._queue[self.round - 1]
        self._apply(self.current_event.effects)
        return self.current_event

    def affordable(self, action: Action, already: tuple = ()) -> bool:
        total = Counter(action.cost)
        for a in already:
            total.update(a.cost)
        return all(self.res[k] >= v for k, v in total.items())

    def available_actions(self, chosen: tuple = ()) -> list:
        chosen_ids = {a.id for a in chosen}
        return [a for a in self.rs.all_actions
                if a.id not in chosen_ids and self.affordable(a, tuple(chosen))]

    def resolve_round(self, action_ids: list, taste: Optional[dict] = None, reason: str = "",
                      record_player: bool = True) -> RoundRecord:
        if self.current_event is None or len(self.records) >= self.round:
            raise RuntimeError("begin_round() を先に呼んでください。")
        ids = list(action_ids)
        if len(ids) != len(set(ids)):
            raise ValueError("同じ行動は一度しか選べません。")
        if len(ids) > self.apa:
            raise ValueError(f"1ラウンドで選べる行動は{self.apa}つまでです。")
        try:
            acts = [self.rs.action(i) for i in ids]
        except KeyError as e:
            raise ValueError(f"未知の行動です: {e}") from None
        total = Counter()
        for a in acts:
            total.update(a.cost)
        for k, v in total.items():
            if self.res[k] < v:
                raise ValueError(f"{self.rs.resource_labels[k]}が足りません。")

        for a in acts:                       # 支払い
            self._apply({k: -v for k, v in a.cost.items()})
        taste_in = taste or {}
        taste_done = {}
        taste_cost = self.rs.settings["taste_cost"]
        for a in acts:                       # 味見
            if not a.automation:
                continue
            can_pay = all(self.res[k] >= v for k, v in taste_cost.items())
            if taste_in.get(a.id) and can_pay:
                self._apply({k: -v for k, v in taste_cost.items()})
                taste_done[a.id] = True
            else:
                taste_done[a.id] = False
                self.skipped_taste += 1
        for a in acts:                       # 効果
            self._apply(a.effect)
            self.used_modules[a.module_id] += 1

        covered = {t for a in acts for t in a.covers}
        met, unmet = [], []
        gained = {r.id: 0 for r in self.rs.roles}
        for n in self.current_event.needs:
            if n.tag in covered:
                met.append(n)
                gained[n.who] += 1
                self.thanks[n.who] += 1
            else:
                unmet.append(n)

        rec = RoundRecord(
            number=self.round, event=self.current_event, role_id=self.role_for_round(self.round).id,
            player=self.player_for_round(self.round) if record_player else "",
            action_ids=ids, reason=reason.strip(),
            taste=taste_done, thanks_gained=gained, unmet=unmet, met=met,
        )
        self.records.append(rec)
        self._apply(self.rs.settings["regen"])   # 次のラウンドへ向けて、少し回復
        return rec

    # ---- 異論・振り返り ---------------------------------------------------
    def add_objection(self, text: str) -> None:
        if text.strip():
            self.objections.append({"round": max(self.round, 1), "role": self.role_for_round(max(self.round, 1)).label,
                                    "text": text.strip()})

    def set_memory(self, prompt: str, text: str) -> None:
        if text.strip():
            self.memories[prompt] = text.strip()


def bot_choose(game: Game):
    """デモ用の簡単なBot。困りごとへ多く応えられる行動を、安い順に選ぶ。"""
    ev = game.current_event
    chosen: list = []
    covered: set = set()
    for _ in range(game.apa):
        best, best_key = None, None
        for a in game.available_actions(tuple(chosen)):
            gain = sum(1 for n in ev.needs if n.tag in a.covers and n.tag not in covered)
            if gain == 0:
                continue
            key = (gain, -sum(a.cost.values()))
            if best_key is None or key > best_key:
                best, best_key = a, key
        if best is None:
            break
        chosen.append(best)
        covered.update(best.covers)
    return [a.id for a in chosen], {a.id: True for a in chosen if a.automation}
