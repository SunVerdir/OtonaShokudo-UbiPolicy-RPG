# ルールを書き換える（政策ゲームチェンジ）

このゲームのルールは、プログラミングなしで書き換えられます。`src/otona_shokudo_rpg/data/` のJSONを編集してください。

| ファイル | 中身 |
| --- | --- |
| `modules.json` | 八つの政策モジュールと、その行動カード（コスト・効果・応えられる困りごと） |
| `events.json` | イベントカード（影響と、現場の困りごと） |
| `roles.json` | 住民・生産者・運営者・行政・技術者と、その視点の問い |
| `rules.json` | ラウンド数・初期資源・回復量・検証課題カードなど |

## 手順

```bash
python -m pip install -e .
cp -r src/otona_shokudo_rpg/data my-rules      # コピーして編集
otona-shokudo-rpg --rules my-rules --check-rules   # 整合性を検査
otona-shokudo-rpg --rules my-rules                 # 自作ルールで遊ぶ
python -m unittest discover -s tests -v             # テスト
```

## 守ってほしいこと

- 実在の個人・子ども・団体の情報、APIキー、パスワードを入れない。
- `modules.json` の `status`（公開物の段階）を、実際より進んでいるように書かない。
- `modules.json` の `covers` と `events.json` の `needs[].tag` は対応づけを確認する。画面の `◇` はタグの重なりを示すだけで、推奨や解決保証ではない。
- 「有り難う！」や資源効果はゲーム内の仮想指標・仮定として扱い、実際の感謝、満足度、同意、政策効果の証拠と書かない。
- 異論を述べる権利と、途中離脱の自由を損なわない。
- プレイテストは任意参加とし、ニックネームを使う。理由や振り返りの入力・共有を強制しない。
- 変更は、GitHubリポジトリ作成後にIssueの「ルール提案」またはPull Requestで提案してください。
- テストとルール検査が通ることを確認してください。
