"""ゲームの振り返りレポート（「次の検証課題」を持ち帰る）。"""
from __future__ import annotations

from collections import Counter

from .engine import Game


def build_report(game: Game) -> dict:
    rs = game.rs
    raw_total = sum(game.thanks.values())
    total = max(0, raw_total - game.skipped_taste)
    overlooked = [r.label for r in rs.roles if game.thanks[r.id] == 0] if game.records else []

    triggers = Counter()
    unmet_list = []
    for rec in game.records:
        for n in rec.met + rec.unmet:
            triggers[rs.verification["tag_to_card"][n.tag]] += 1
        for n in rec.unmet:
            unmet_list.append({"round": rec.number, "event": rec.event.title,
                               "who": rs.role(n.who).label, "text": n.text})
    if game.skipped_taste:
        triggers[rs.verification["taste_skipped"]] += 3
    if overlooked or unmet_list:
        triggers[rs.verification["role_overlooked"]] += 1
    cards = [dict(id=c, **rs.verification["cards"][c]) for c, _ in triggers.most_common(4)]

    used = {rs.module(mid).short for mid in game.used_modules}
    unused = [m.short for m in rs.modules if m.short not in used]
    rounds = []
    for rec in game.records:
        rounds.append({
            "round": rec.number, "event": rec.event.title,
            "player": rec.player or "担当者名は非記録",
            "role": rs.role(rec.role_id).label,
            "actions": [rs.action(i).title for i in rec.action_ids] or ["今回は見送り"],
            "reason": rec.reason, "met": len(rec.met), "unmet": len(rec.unmet),
            "taste_skipped": [rs.action(i).title for i, ok in rec.taste.items() if not ok],
        })
    return {
        "total_thanks": total, "raw_thanks": raw_total, "skipped_taste": game.skipped_taste,
        "per_role": {r.label: game.thanks[r.id] for r in rs.roles},
        "overlooked_roles": overlooked, "unmet": unmet_list, "unused_modules": unused,
        "cards": cards, "objections": list(game.objections), "memories": dict(game.memories),
        "rounds": rounds, "played_rounds": len(game.records), "total_rounds": game.total_rounds,
        "quit_early": game.quit_early, "seed": game.seed,
    }


def to_markdown(rep: dict) -> str:
    L = ["# 大人食堂政策ゲーム 振り返りレポート", "",
         "> 本レポートは学びのためのゲームの記録です。実在の制度・自治体導入・実給付・政策効果を示すものではありません。", ""]
    if rep["quit_early"]:
        L += [f"途中離脱（{rep['played_rounds']}/{rep['total_rounds']}ラウンド）。いつでも抜けてよいルールです。", ""]
    L += [f"## 「有り難う！」（ゲーム内の仮想指標）：{rep['total_thanks']}", "",
          "> この値は、タグ対応の記録数から味見省略回数を差し引いた、ゲーム内ルール上の仮想指標です。実際の住民の感謝・満足度・同意・政策効果を測定したものではありません。", ""]
    if rep["skipped_taste"]:
        L += [f"- AIの提案の「味見」を省いた回数：{rep['skipped_taste']}（ゲーム内の対応指標が1減ります）"]
    L += [f"- {role}：困りごと対応の記録（味見省略の減算前）{n}" for role, n in rep["per_role"].items()]
    L += ["", "## 見落としていた声", ""]
    if rep["overlooked_roles"]:
        L += [f"- まだ対応できた困りごとの記録がない役：{'、'.join(rep['overlooked_roles'])}"]
    L += [f"- 第{u['round']}ラウンド「{u['event']}」／{u['who']}：{u['text']}" for u in rep["unmet"]] or ["- なし"]
    if rep["unused_modules"]:
        L += ["", f"まだ試していない構想：{'、'.join(rep['unused_modules'])}"]
    L += ["", "## 選んだ理由の振り返り", ""]
    for r in rep["rounds"]:
        L.append(f"- 第{r['round']}ラウンド「{r['event']}」（{r['player']}／{r['role']}）：{'＋'.join(r['actions'])}"
                 + (f"　理由：{r['reason']}" if r["reason"] else ""))
    L += ["", "## 持ち帰る、次の検証課題", ""]
    L += [f"- **{c['title']}**：{c['question']}" for c in rep["cards"]] or ["- （ラウンドを進めると表示されます）"]
    if rep["objections"]:
        L += ["", "## 出された異論", ""]
        L += [f"- 第{o['round']}ラウンド／{o['role']}：{o['text']}" for o in rep["objections"]]
    if rep["memories"]:
        L += ["", "## 持ち帰る、三つの記憶", ""]
        L += [f"- **{k}**：{v}" for k, v in rep["memories"].items()]

    seed = rep.get("seed")
    if seed is not None:
        L += ["", "## もう一度遊ぶ", "",
              "同じ標準イベント順で、違う選択を試すための再戦コマンドです。選んだ理由や異論はコマンドに含みません。", "",
              f"`otona-shokudo-rpg --seed {seed} --rounds {rep['total_rounds']}`", ""]
        if rep["overlooked_roles"]:
            L += [f"次は、まだ声が届いていない役（{'、'.join(rep['overlooked_roles'])}）の視点から、別のカードを試してみましょう。"]
        elif rep["unused_modules"]:
            L += [f"次は、まだ試していない構想（{'、'.join(rep['unused_modules'])}）を一つ選ぶと、何が変わるか試してみましょう。"]
        else:
            L += ["次は、優先順位を一つ変えてみると、どんな声が変わるか試してみましょう。"]
    return "\n".join(L) + "\n"
