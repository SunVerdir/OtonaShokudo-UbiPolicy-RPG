"""ルールデータ（JSON）の読み込みと検証。

ルールは `data/*.json` にあり、プログラミングなしで書き換えられます。
`--rules DIR` で、自作のルールセットを読み込めます（無いファイルは標準ルールで補います）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Optional

RESOURCES = ("food", "budget", "people", "infra")
_FILES = ("roles.json", "rules.json", "events.json", "modules.json")


@dataclass(frozen=True)
class Action:
    id: str
    module_id: int
    title: str
    desc: str
    cost: dict
    effect: dict
    covers: tuple
    automation: bool


@dataclass(frozen=True)
class Module:
    id: int
    key: str
    name: str
    short: str
    group: str
    summary: str
    status: str
    question: str
    actions: tuple


@dataclass(frozen=True)
class Need:
    tag: str
    who: str
    text: str


@dataclass(frozen=True)
class Event:
    id: str
    title: str
    text: str
    effects: dict
    needs: tuple
    first: bool = False


@dataclass(frozen=True)
class Role:
    id: str
    label: str
    lens: str


@dataclass(frozen=True)
class Ruleset:
    roles: tuple
    modules: tuple
    events: tuple
    settings: dict
    resource_labels: dict
    tags: dict
    verification: dict
    memories: tuple

    def action(self, action_id: str) -> Action:
        for m in self.modules:
            for a in m.actions:
                if a.id == action_id:
                    return a
        raise KeyError(action_id)

    def module(self, module_id: int) -> Module:
        return next(m for m in self.modules if m.id == module_id)

    def role(self, role_id: str) -> Role:
        return next(r for r in self.roles if r.id == role_id)

    @property
    def all_actions(self) -> list:
        return [a for m in self.modules for a in m.actions]


def _read(name: str, rules_dir: Optional[Path]):
    if rules_dir is not None and (rules_dir / name).exists():
        return json.loads((rules_dir / name).read_text(encoding="utf-8"))
    return json.loads((resources.files("otona_shokudo_rpg") / "data" / name).read_text(encoding="utf-8"))


def load_ruleset(rules_dir: Optional[str] = None) -> Ruleset:
    d = Path(rules_dir) if rules_dir else None
    raw = {n: _read(n, d) for n in _FILES}
    rules = raw["rules.json"]
    roles = tuple(Role(**r) for r in raw["roles.json"])
    modules = []
    for m in raw["modules.json"]:
        acts = tuple(
            Action(
                id=a["id"], module_id=m["id"], title=a["title"], desc=a.get("desc", ""),
                cost=dict(a.get("cost", {})), effect=dict(a.get("effect", {})),
                covers=tuple(a.get("covers", ())), automation=bool(a.get("automation", False)),
            )
            for a in m["actions"]
        )
        modules.append(Module(
            id=m["id"], key=m["key"], name=m["name"], short=m.get("short", m["name"]),
            group=m.get("group", ""), summary=m.get("summary", ""), status=m.get("status", ""),
            question=m.get("question", ""), actions=acts,
        ))
    events = tuple(
        Event(
            id=e["id"], title=e["title"], text=e.get("text", ""), effects=dict(e.get("effects", {})),
            needs=tuple(Need(**n) for n in e["needs"]), first=bool(e.get("first", False)),
        )
        for e in raw["events.json"]
    )
    return Ruleset(
        roles=roles, modules=tuple(modules), events=events, settings=rules["settings"],
        resource_labels=rules["resource_labels"], tags=rules["tags"],
        verification=rules["verification"], memories=tuple(rules.get("memories", ())),
    )


def validate_ruleset(rs: Ruleset) -> list:
    """ルールの整合性を調べ、問題点のリスト（空なら問題なし）を返す。"""
    errs = []
    role_ids = {r.id for r in rs.roles}
    ids = [a.id for a in rs.all_actions]
    if len(ids) != len(set(ids)):
        errs.append("行動(action)のidが重複しています。")
    if len({m.id for m in rs.modules}) != len(rs.modules):
        errs.append("モジュールのidが重複しています。")
    covered = set()
    for a in rs.all_actions:
        for k in list(a.cost) + list(a.effect):
            if k not in RESOURCES:
                errs.append(f"{a.id}: 未知の資源 '{k}'")
        if any(v < 0 for v in a.cost.values()):
            errs.append(f"{a.id}: cost は0以上にしてください。")
        for t in a.covers:
            if t not in rs.tags:
                errs.append(f"{a.id}: 未知のタグ '{t}'")
        covered.update(a.covers)
    if len(rs.events) < rs.settings["rounds"]:
        errs.append("イベント数がラウンド数より少ないです。")
    for e in rs.events:
        for k in e.effects:
            if k not in RESOURCES:
                errs.append(f"{e.id}: 未知の資源 '{k}'")
        for n in e.needs:
            if n.who not in role_ids:
                errs.append(f"{e.id}: 未知の役 '{n.who}'")
            if n.tag not in rs.tags:
                errs.append(f"{e.id}: 未知のタグ '{n.tag}'")
            elif n.tag not in covered:
                errs.append(f"{e.id}: タグ '{n.tag}' に応えられる行動がありません（詰みます）。")
    v = rs.verification
    for t, c in v["tag_to_card"].items():
        if c not in v["cards"]:
            errs.append(f"検証課題カード '{c}' が定義されていません。")
    for key in ("taste_skipped", "role_overlooked"):
        if v[key] not in v["cards"]:
            errs.append(f"検証課題カード '{v[key]}' が定義されていません。")
    return errs
