---
name: skill-auto
description: 「プレゼン資料に使えるSkillを紹介して」「PDFに使えるSkillを探して」のような普通の日本語の依頼だけで、Find Skillsで利用可能なSkillとskills.shの外部候補をまとめて提案し、その候補をSkill Auditへそのまま引き継いで一括監査し、ユーザーが選んだSkillだけをインストールするSkill。Use when the user casually asks for a skill that would help with some goal in Japanese (e.g. "〇〇に役立つSkillを教えて") without explicitly requesting search, audit, or install as separate steps.
allowed-tools:
  - Bash(npx skills find *)
  - Bash(python3 ${CLAUDE_SKILL_DIR}/../skill-audit/scripts/audit_skill.py *)
---

# Skill Auto

Skill Autoは、既存の [Find Skills](../find-skills/SKILL.md) と
[Skill Audit](../skill-audit/SKILL.md) を順番につなぐSkill。

このSkill自身は検索ロジックや監査ロジックを持たない。
実行時に必ず次の2つのSKILL.mdを読み、その内容に従う。

```
${CLAUDE_SKILL_DIR}/../find-skills/SKILL.md
${CLAUDE_SKILL_DIR}/../skill-audit/SKILL.md
```

## 使うタイミング

次のような、目的だけを伝える簡単な日本語の依頼で使用する。

- 「プレゼン資料に使えるSkillを紹介して」
- 「PDFに使えるSkillを探して」
- 「〇〇に役立つSkillを教えて」

「監査して」「安全確認して」「インストールして」まで、
ユーザーが個別に指定する必要はない。目的が分かる時点で、
下記の流れをまとめて続けて実行する。

## 実行の流れ

1. **候補を探す**
   Find SkillsのSKILL.mdの手順に従い、目的に合う候補を探す。

2. **既存の利用可能なSkillも候補に残す**
   現在すでに利用可能なSkill（インストール済み、または元々使えるSkill）の中に
   目的に合うものがあれば、それも候補として残す。

3. **外部候補も必ず検索する**
   既存の候補だけで終了しない。Find Skillsの手順に従い、
   `npx skills find` などでskills.shの外部候補も検索する。

4. **検索結果をそのままSkill Auditへ引き継ぐ**
   ユーザーにコピー・貼り直しを求めない。Find Skillsで得た候補一覧
   （`owner/repository@skill-name` 形式などを含む）を、
   そのままSkill Auditの「Find Skillsの直近候補をまとめて監査する」手順に渡す。

5. **監査以降はSkill Auditの手順に任せる**
   候補のURL化、一括監査（固定Pythonスクリプトの実行）、
   人気度とセキュリティ監査結果の日本語での報告、4分類
   （インストール候補／注意付きインストール候補／保留／非推奨）、
   総評、インストール確認画面の表示は、すべてSkill AuditのSKILL.mdの手順どおりに行う。

6. **ユーザーが選んだSkillだけをインストールする**
   Skill Auditの確認画面でユーザーが明確に選んだSkillだけをインストールする。
   自動でインストールしない。

## すでに利用可能なSkillの扱い

すでに利用可能なSkillにskills.shのページが確認できない場合は、
推測でURLを作らない。そのSkillは「すでに利用可能なSkill」として、
skills.shの外部候補とは別に表示する。

## 注意事項

- 自動でインストールしない。必ずSkill Auditの確認画面でユーザーに選んでもらう。
- インストールコマンドの実行はSkill Auditの手順に従い、
  ユーザーが対象Skillと保存先を明確に指定した場合だけ行う。
- 検索や監査の内容そのものは、このSkillでは決めない。常にFind SkillsとSkill Auditの
  SKILL.mdの記述を優先する。
