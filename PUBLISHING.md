# GitHub 公開手順

このプロジェクトは公開リポジトリを想定したローカル一式です。ZIPを展開しただけでは、GitHub上のリポジトリ作成や公開は行われません。

## 公開前チェック

1. `VISION.md` が本人の意図・表現に合っているか確認します。第七巻は公開済み記事ではなく、原稿・構想資料として扱っています。
2. `LICENSE-MIT` はPython実装・テスト・プロジェクト設定、`LICENSE-CC-BY-4.0.txt` は文書・ルールJSON・画像に適用します。ファイル群でライセンスが異なるため、`pyproject.toml` にMIT単独のパッケージ全体ライセンスを設定していません。`ATTRIBUTION.md` の素材一覧・寸法・ハッシュ・由来に関する限定表現も確認します。
3. 本名・連絡先・健康情報・家庭状況・APIキーなどが含まれていないか、`git status` とファイル内容を確認します。保存したゲームレポートは共有前に自由記述を確認してください。
4. 若い世代の参加者に遊んでもらう場合は、任意参加、発言パス、異論、途中離脱が守られるかを確認し、結果を政策効果の実証として扱わないでください。
5. READMEの動画案内が動画説明欄の章立てに限定され、未確認の映像場面を描写していないことを確認します。公開前にREADMEの章立てと動画説明欄が一致するかも手動で照合してください。

## 手動で初回公開する場合

GitHubにログインし、`SunVerdir` アカウントで `OtonaShokudo-UbiPolicy-RPG` という **Public** リポジトリを空の状態で作成します。README、License、`.gitignore` はGitHub側で追加せず、ZIPの内容を使います。作成後、READMEの「アドレス候補」の案内を実際のリポジトリリンクに更新してから、プロジェクトフォルダーで次を実行します。

```bash
git init
git add .
git status --short
git diff --cached --stat
# 内容・権利・個人情報を確認してからコミット
git commit -m "Initial policy game prototype"
git branch -M main
git remote add origin https://github.com/SunVerdir/OtonaShokudo-UbiPolicy-RPG.git
git push -u origin main
```

`git status --short` に意図しないファイルがあれば、コミット前に外してください。認証を求められた場合はGitHub公式の認証方法を使い、パスワードやトークンをコードやファイルに書き込まないでください。

## 公開後

- GitHub ActionsでPython 3.10〜3.13のテスト・ルール検査・デモが成功することを確認します。
- READMEのローカル画像が表示され、YouTubeリンクが正しいことを確認します。
- Issueを受け付ける前に、個人情報・子ども・差別的表現を扱う運用方針を決めます。
- 参加者によるテストでは、名前はニックネームのみとし、感想やレポートを本人の同意なく公開しません。

この手順は公開作業の案内です。リポジトリの作成やpushが完了したことを意味しません。
