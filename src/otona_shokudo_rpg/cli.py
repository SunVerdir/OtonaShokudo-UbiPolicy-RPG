"""コマンドライン版。標準ライブラリのみで動きます。"""
from __future__ import annotations

import argparse
from pathlib import Path

from .engine import Game, bot_choose
from .report import build_report, to_markdown
from .rules import RESOURCES, load_ruleset, validate_ruleset

DISCLAIMER = """\
╔══════════════════════════════════════════════════════════════╗
  大人食堂（マルチモーダルUBI基盤）政策ゲーム   ─ ゲーム案 ─
  ・舞台は架空の「大人食堂ワールド」。数値や人物はすべて架空です。
  ・「有り難う！」は困りごとの対応数を示すゲーム内の仮想指標です。
  ・実際の感謝・満足度・同意・政策効果を測定するものではありません。
  ・自治体導入・実給付・政策効果を示さず、NEXA等の公式見解でもありません。
  ・異論、担当パス、途中離脱は自由です。勝者やランキングはありません。
╚══════════════════════════════════════════════════════════════╝"""

TAG_LABELS = {
    "meal": "食事", "supply": "食材流通", "funding": "資金", "labor": "担い手",
    "infra": "電力・通信", "info": "情報", "voice": "参加・声", "culture": "居場所・文化",
}


class Quit(Exception):
    pass


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise Quit from None


def bar(game: Game, key: str) -> str:
    v = game.res[key]
    return f"{game.rs.resource_labels[key]:<6}{'■' * v}{'□' * (game.cap - v)} {v}"


def show_state(game: Game) -> None:
    print("\n── いまの大人食堂ワールド ──")
    for k in RESOURCES:
        print("  " + bar(game, k))
    th = "　".join(f"{r.label.split('（')[0]}:{game.thanks[r.id]}" for r in game.rs.roles)
    print(f"  「有り難う！」（ゲーム内の仮想指標） {th}")


def show_event(game: Game, ev, role, player: str) -> None:
    print(f"\n━━━ 第{game.round}/{game.total_rounds}ラウンド ━━━")
    print(f"🌍 イベントカード：{ev.title}")
    print(f"   {ev.text}")
    print("   影響：" + (" ".join(f"{game.rs.resource_labels[k]}{v:+d}" for k, v in ev.effects.items()) or "なし"))
    print("   現場の声（困りごと）：")
    for n in ev.needs:
        print(f"     ・[{game.rs.role(n.who).label}] {n.text}（{game.rs.tags[n.tag]}）")
    print(f"\n🎭 今回の役：{role.label}（担当：{player}）\n   視点の問い：{role.lens}")


def show_actions(game: Game, chosen: tuple = (), detail: bool = False) -> list:
    avail = game.available_actions(chosen)
    current_tags = {n.tag for n in game.current_event.needs} if game.current_event else set()
    print("\n選べる政策アクション（最大%dつ）:" % game.apa)
    print("  ×=資源不足　◇=今回の困りごとタグと重なる（おすすめ・解決保証ではありません）")
    for i, a in enumerate(game.rs.all_actions, 1):
        mod = game.rs.module(a.module_id)
        unavailable = "×" if a not in avail and a not in chosen else " "
        relevant = "◇" if current_tags.intersection(a.covers) else " "
        cost = " ".join(f"{game.rs.resource_labels[k]}-{v}" for k, v in a.cost.items()) or "コストなし"
        ai = " 🤖要味見" if a.automation else ""
        tags = "・".join(TAG_LABELS.get(t, game.rs.tags.get(t, t)) for t in a.covers) or "なし"
        print(f" {unavailable}{relevant}{i:>2}. [{mod.short}] {a.title}（{cost}）{ai}　→{tags}")
        if detail:
            print(f"        内容：{a.desc}")
    return game.rs.all_actions


def help_text() -> str:
    return ("番号をスペースで区切って入力（例: 1 4）。Enterだけで今回は見送り。\n"
            "  s:状態　d:カードの説明　m:構想の段階　o:異論\n"
            "  p:担当をパス（担当者名・理由はレポートに保存しない）\n"
            "  q:途中で抜ける　?:この説明")


def show_modules(game: Game) -> None:
    print("\n── 八つの政策モジュールの現在地（公開物の成熟度）──")
    for m in game.rs.modules:
        print(f"  {m.id}. {m.name}\n     {m.summary}\n     段階：{m.status}")


def choose_actions(game: Game) -> list | None:
    actions = show_actions(game)
    print("\n" + help_text())
    while True:
        s = ask("\n選ぶ番号 > ")
        low = s.lower()
        if low == "q":
            raise Quit
        if low == "p":
            print("  担当者名と理由の自由記述はレポートに残さず、このラウンドをパスします。")
            return None
        if low == "?":
            print(help_text()); continue
        if low == "s":
            show_state(game); continue
        if low == "m":
            show_modules(game); continue
        if low == "d":
            show_actions(game, detail=True); continue
        if low == "o":
            t = ask("異論・違和感（Enterで取り消し）> ")
            game.add_objection(t)
            print("  記録しました。異論は大切な政策の種です。" if t else "  取り消しました。")
            continue
        if not s:
            return []
        try:
            try:
                nums = [int(x) for x in s.replace(",", " ").split()]
            except ValueError:
                raise ValueError("番号（半角の数字）で入力してください。") from None
            if any(n < 1 or n > len(actions) for n in nums):
                raise ValueError(f"1〜{len(actions)}の番号を選んでください。")
            ids = [actions[n - 1].id for n in nums]
            if len(set(ids)) != len(ids) or len(ids) > game.apa:
                raise ValueError(f"同じものは選べず、最大{game.apa}つまでです。")
            acts = [game.rs.action(i) for i in ids]
            for k in range(len(acts)):
                if not game.affordable(acts[k], tuple(acts[:k])):
                    raise ValueError(f"「{acts[k].title}」は資源が足りません。")
            return ids
        except ValueError as e:
            print(f"  入力を確かめてください：{e}")


def do_taste(game: Game, ids: list) -> dict:
    taste = {}
    cost = " ".join(f"{game.rs.resource_labels[k]}-{v}" for k, v in game.rs.settings["taste_cost"].items())
    for i in ids:
        a = game.rs.action(i)
        if a.automation:
            ans = ask(f"🍴 『{a.title}』はAIの提案を含みます。人が味見（確認）しますか？（{cost}） [Y/n] > ").lower()
            taste[i] = ans in ("", "y", "yes", "はい")
            if not taste[i]:
                print("  味見を省きました。対応指標が減るのはゲーム内ルール上の調整です。")
    return taste


def show_result(game: Game, rec) -> None:
    print("\n── 結果（ゲーム内の仮想指標）──")
    for n in rec.met:
        print(f"  対応できた困りごと [{game.rs.role(n.who).label}] 「{n.text}」")
    for n in rec.unmet:
        print(f"  … 未解決 [{game.rs.role(n.who).label}] 「{n.text}」")
    for i, ok in rec.taste.items():
        if not ok:
            print(f"  ⚠ 味見を省いた：{game.rs.action(i).title}（ゲーム内の対応指標が1減ります）")


def finish(game: Game, save: str = None, interactive: bool = True) -> None:
    if interactive and game.records:
        print("\n━━━ 最後に、持ち帰る三つの記憶（一言ずつ。Enterで省略）━━━")
        try:
            for p in game.rs.memories:
                game.set_memory(p, ask(f"『{p}』（本名・個人情報は書かない）> "))
        except Quit:
            pass
    rep = build_report(game)
    md = to_markdown(rep)
    print("\n" + md)
    if save:
        Path(save).write_text(md, encoding="utf-8")
        print(f"レポートを保存しました：{save}")


def play(game: Game, interactive: bool = True, save: str = None) -> None:
    try:
        while not game.is_over:
            ev = game.begin_round()
            role = game.role_for_round(game.round)
            player = game.player_for_round(game.round)
            show_event(game, ev, role, player)
            show_state(game)
            if interactive:
                selection = choose_actions(game)
                passed = selection is None
                ids = [] if passed else selection
                taste = do_taste(game, ids)
                reason = ask("💬 選んだ理由を一言（任意。個人情報は書かない）> ") if ids else ""
            else:
                ids, taste = bot_choose(game)
                passed = False
                reason = "（デモ：困りごとに対応する行動を選択）"
            rec = game.resolve_round(ids, taste, reason, record_player=not passed)
            show_result(game, rec)
    except Quit:
        game.quit_early = True
        print("\n途中で抜けました。ここまでの振り返りをお見せします。おつかれさまでした！")
    finish(game, save=save, interactive=interactive)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="otona-shokudo-rpg", description="大人食堂（マルチモーダルUBI基盤）政策ゲーム")
    p.add_argument("--players", default="", help="ニックネームをカンマ区切りで（例: ゆい,そら,はる）")
    p.add_argument("--rounds", type=int, default=None, help="ラウンド数（標準6。--quickと併用時はこちらを優先）")
    p.add_argument("--quick", action="store_true", help="短縮版の3ラウンドで遊ぶ")
    p.add_argument("--seed", type=int, default=None, help="乱数シード（同じイベント順を再現。省略時もレポートに表示）")
    p.add_argument("--rules", default=None, help="自作ルールのフォルダ（data/*.json と同じ形式）")
    p.add_argument("--check-rules", action="store_true", help="ルールの整合性を検査して終了")
    p.add_argument("--demo", action="store_true", help="Botが自動で1ゲーム遊ぶ（入力不要）")
    p.add_argument("--save-report", default=None, help="振り返りレポート(.md)の保存先")
    a = p.parse_args(argv)
    if a.rounds is not None and a.rounds < 1:
        p.error("--rounds は1以上を指定してください")

    rs = load_ruleset(a.rules)
    errs = validate_ruleset(rs)
    if a.check_rules:
        print("\n".join(errs) if errs else "ルールに問題は見つかりませんでした。")
        return 1 if errs else 0
    if errs:
        print("ルールに問題があります：\n" + "\n".join(errs))
        return 1

    rounds = a.rounds if a.rounds is not None else (3 if a.quick else None)
    print(DISCLAIMER)
    players = [x.strip() for x in a.players.split(",") if x.strip()] or None
    game = Game(rs, players=players, seed=a.seed, rounds=rounds)
    if game.total_rounds < rs.settings["rounds"]:
        print(f"\n【ショート周回】今回は{game.total_rounds}ラウンド。まずは短く試してみましょう。")
    if not a.demo:
        print("\n遊び方：現場の声を読む → 関係するカードを選ぶ（最大2枚）→ 振り返る")
        print("番号選び・理由記入はパスできます。ニックネームを使い、本名や個人情報は入力しないでください。")
        print("Enterで開始 > ", end="")
        try:
            ask("")
        except Quit:
            return 0
    play(game, interactive=not a.demo, save=a.save_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
