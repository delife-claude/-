---
name: skill-audit
description: 指定されたAgent Skillについて、固定Pythonスクリプトでskills.sh上の人気度（インストール数・GitHubスター数）とセキュリティ監査結果を取得し、日本語で報告する。確認後にインストール候補を提示し、ユーザーが許可したSkillだけをインストールする。Use when the user asks to audit, vet, or check the safety/security of an agent skill on skills.sh, or wants to verify skills before installing (e.g. "このSkillの監査結果を確認して", "インストール前に安全か調べて", "skill audit").
allowed-tools:
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/audit_skill.py *)
---

# Skill Audit

指定されたAgent Skillについて、skills.sh上の人気度とセキュリティ監査結果を確認し、
日本語で分かりやすく報告するSkill。

情報の取得は、毎回コードを書き起こすのではなく、
このSkillに同梱された固定Pythonスクリプトを1回実行することで行う。

監査結果を確認したあと、インストール候補を具体的に提示し、
ユーザーが許可したSkillだけをインストールする。

## 使用するスクリプト

```
${CLAUDE_SKILL_DIR}/scripts/audit_skill.py
```

- このSkillが監査を行うときは、必ずこの固定ファイルを実行する。
- ヒアドキュメントや `python3 -c` などでPythonコードをその場で生成しない。
- このスクリプトはAPI・認証・トークンを使用せず、標準ライブラリのみでskills.shの公開HTMLを取得する。
- ブラウザ操作（Claude in Chrome等）は使用しない。スクリプトで取得できなかった場合も、
  自動でブラウザ操作へ切り替えず、取得できなかった項目と理由をそのまま報告する。

## 対象Skillの特定

- skills.shのURLが渡された場合は、そのURLを使用する。
- Find Skillsが提示した候補一覧が渡された場合は、一覧に含まれるすべての候補のURLを集める。
- 各候補にskills.shのURLが含まれている場合は、そのURLを使用する。
- Skill名やGitHubリポジトリ名だけの場合は、skills.sh内で対応するページのURLを特定する。
- Skill名だけが渡され、別のSkillと思われる同名候補が複数見つかった場合は、
  勝手に選ばず、候補を一覧にしてユーザーに確認する。
- skills.sh上に対象Skillのページが見つからない場合は、その事実を報告する
  （スクリプトの `error` フィールドで判定する）。

## Find Skillsの直近候補をまとめて監査する

ユーザーが「さっきの候補を全部監査して」「今出した候補を監査して」
「この候補をまとめて安全確認して」などと指示した場合は、
候補名やURLを再入力・貼り直ししてもらう必要はない。
現在の会話内にある直近のFind Skillsの実行結果を読み取り、対象を特定する。

- 現在の会話をさかのぼり、直近のFind Skills結果（候補一覧）を探す。
- その結果から、`owner/repository@skill-name` 形式の候補をすべて抽出する。

  例：
  ```
  googleworkspace/cli@recipe-create-presentation
  getsentry/skills@presentation-creator
  ```

- 抽出した各候補を、次の形式でskills.shのURLへ変換する。

  ```
  googleworkspace/cli@recipe-create-presentation
  ↓
  https://skills.sh/googleworkspace/cli/recipe-create-presentation
  ```

- 変換したすべてのURLを、下記「スクリプトの実行方法」に従い、
  既存の固定Pythonスクリプトへ1回のコマンドでまとめて渡す。

  ```
  python3 ${CLAUDE_SKILL_DIR}/scripts/audit_skill.py "URL1" "URL2" "URL3"
  ```

- ユーザーへ候補名やURLの再提示・コピー・貼り直しを求めない。
- 候補の文字列（`owner/repository@skill-name`）を正確に確認できないものは、
  推測でURLを作らず監査対象に含めない。「URLを特定できなかった候補」として、
  他の監査結果とは分けて報告する。
- 現在の会話内に直近のFind Skills結果が見つからない場合だけ、
  Find Skillsの結果一覧、またはskills.shのURLをユーザーに求める。

## スクリプトの実行方法

対象が1件の場合:

```
python3 ${CLAUDE_SKILL_DIR}/scripts/audit_skill.py "https://www.skills.sh/vercel-labs/skills/find-skills"
```

対象が複数件の場合（Find Skillsの候補一覧など）は、
すべてのURLを1回のコマンドにまとめて渡す。個別に何度も実行しない。

```
python3 ${CLAUDE_SKILL_DIR}/scripts/audit_skill.py "URL1" "URL2" "URL3"
```

スクリプトは標準出力へ構造化されたJSONを返す。結果はファイルに保存されない。
このJSONを読み取り、日本語で要約・報告する（JSON自体は日本語へ要約されずそのまま出力される）。

## JSONの読み取り方

各URLの結果（`results[]`）には次が含まれる。

- `error`：ページ取得やページ構造の不一致などで問題があった場合の理由。`null`なら特に問題なし。
- `skill_name` / `distributor` / `repository_url` / `verified_org`
- `installs`（インストール数）/ `github_stars`（GitHubスター数）
- `security_audits[]`：各監査の `name`（監査元）、`verdict`（判定）、`detail_url`（詳細ページURL）
  - 判定が `Pass` または `Safe` の場合、`detail` は `null`（詳細ページを取得していない）
  - 判定がそれ以外の場合、`detail` に次が入る（取得できなかった項目は `null`）：
    `audited_by`、`audited_on`（監査実施日）、`risk_level`（リスクレベル）、
    `analyzed_at`、`issues_count`、`issues[]`（`code`＝警告コード、`title`＝警告タイトル）、
    `analysis[]`（警告理由・分析内容の本文）
  - 詳細ページの取得自体に失敗した場合は `detail_error` にその理由が入る

`null`や空配列になっている項目は、推測で埋めずに「確認できませんでした」として報告する。

## 確認する内容

各Skillについて、次を確認する。

- Skill名
- 配布元
- skills.shのURL
- インストール数
- GitHubスター数
- 掲載されているセキュリティ監査元
- 各監査の判定
- 監査実施日（表示されている場合）
- 警告、失敗、高リスク、未確認などの結果があるか

インストール数とGitHubスター数は「人気度の目安」、
セキュリティ監査結果は「安全性の判断材料」として、分けて表示する。

## 報告形式

各Skillについて、次の形式で簡潔に報告する。

```
■ Skill名

配布元：
インストール数：
GitHubスター数：

監査結果：
・監査元名：判定
・監査元名：判定

警告の有無：
警告がある場合の理由：
監査実施日：
確認したページ：
```

- 表示されていない項目（JSONで`null`）は、推測せず「確認できませんでした」と記載する。
- 監査結果が一切掲載されていない場合（`security_audits`が空配列）は「監査結果なし」と表示し、
  この情報だけでは安全とも危険とも判断できないことを説明する。
- skills.sh上にSkillページ自体がない場合（`error`にその旨が入る）と、
  Skillページはあるものの監査結果がない場合は、区別して報告する。

## 確認後の整理

確認したSkillを、次の4つに分けて表示する。
人気度（インストール数・GitHubスター数）と安全性（監査結果）は分けて示す。

### ■ インストール候補

警告がなく、明確な問題も報告されていないSkill
（すべての監査が `Pass`/`Safe` など）。

### ■ 注意付きインストール候補

警告（Warnなど）はあるものの、警告理由を確認した結果、
悪意ある動作や明確な情報流出などではなく、
そのSkillの機能の性質に由来する注意であると判断できるもの。

判定が`Warn`であることだけを理由に、自動的にここから除外したり、
「要確認」「高リスク」側へ倒したりしない。必ず`issues`や`analysis`の内容を読み、
何が原因の警告かを具体的に説明したうえで分類する。

### ■ 保留

次のいずれかに該当するSkill。

- 監査結果が掲載されていない
- 判定が不明
- スクリプトで一部またはすべての情報を取得できなかった（`error`または`detail_error`がある）
- 安全性を判断するための情報が不足している

取得できなかった内容と理由を、Skillごとに具体的に説明する。

### ■ 非推奨

High、Critical、Fail、悪意ある処理、認証情報の流出、無許可のデータ送信など、
明確な危険性が報告されているSkill。

この分類は絶対的な安全性を保証するものではなく、
skills.shに掲載されている情報をもとにした整理であることを明記する。

## 各Skillについて必ず表示する項目

分類の一覧に加えて、Skillごとに次を必ず表示する。

- 総評
- 判断理由（監査結果のどの部分を根拠にしたか）
- インストール候補としての分類（上記4分類のいずれか）
- インストールするかどうかの選択肢

## インストールの確認

監査結果の報告後、対象のSkill名を具体的に表示して確認する。

例:

```
監査結果上、インストール候補は次のSkillです。

1. Skill名
2. Skill名

どれをインストールしますか？

・番号を指定
・インストール候補をすべて
・今回はインストールしない
```

- 注意付きインストール候補、保留、非推奨に分類されたSkillは、インストール候補とは分けて表示する。
- ユーザーが注意付きインストール候補・保留・非推奨のSkillを選んだ場合は、
  該当する警告やリスクをもう一度具体的に表示し、
  それでもインストールするか確認する。
- ユーザーが明確に許可したSkillだけをインストールする。

## インストール先

ユーザーがインストールを許可したあと、保存先が指定されていない場合は、
次のどちらにするか確認する。

1. 現在開いているプロジェクトだけで使う（プロジェクト内の `.claude/skills/`）
2. すべてのプロジェクトで使う（`~/.claude/skills/`）

保存先と実行内容を表示し、ユーザーの許可を受けてからインストールする。

ユーザーが対象Skillと保存先を明確に指定した場合だけ、
指定されたSkillをインストールする。

インストール後は、次を報告する。

- インストールしたSkill名
- 配布元
- 保存場所
- 正常に認識されたか
- インストールできなかった場合は、その理由
