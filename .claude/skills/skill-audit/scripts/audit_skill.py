#!/usr/bin/env python3
"""
skills.sh の公開Skill詳細ページから、人気度とセキュリティ監査結果を取得するスクリプト。

- 標準ライブラリのみを使用する（urllib.request, re, json, html, sys, datetime, urllib.parse）。
- APIキー・認証・トークンは使用しない。専用APIも使用しない。
- ブラウザ操作（Claude in Chrome 等）は使用しない。単純なHTTP GETのみ。
- 複数のskills.sh URLを一度の実行でまとめて処理する。
- 1件のURLで失敗しても、残りのURLの処理は継続する。
- 取得できなかった項目は推測で補わず null のままにする。
- 結果はファイルへ保存せず、構造化されたJSONとして標準出力へ出力するのみ。

使用例:
    python3 audit_skill.py "https://www.skills.sh/vercel-labs/skills/find-skills"
    python3 audit_skill.py "URL1" "URL2" "URL3"
"""

import sys
import re
import json
import html as html_module
import urllib.request
import urllib.error
from urllib.parse import urlparse
from datetime import datetime, timezone

USER_AGENT = "Mozilla/5.0 (compatible; skill-audit-script/1.0)"
TIMEOUT_SECONDS = 15
PASS_VERDICTS = {"pass", "safe"}


def fetch(url):
    """URLを取得し (status, html) を返す。失敗した場合は例外を送出する。"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        status = resp.status
        body = resp.read().decode("utf-8", errors="replace")
    return status, body


def clean_text(value):
    """タグ除去済みテキストのHTMLエンティティを解除し前後空白を除く。"""
    if value is None:
        return None
    return html_module.unescape(value).strip()


def strip_tags(value):
    return clean_text(re.sub(r"<[^>]+>", "", value))


def normalize_input_url(raw_url):
    """スキーム省略時は https:// を補い、(origin, skill_path) を返す。"""
    parsed = urlparse(raw_url)
    if not parsed.scheme:
        parsed = urlparse("https://" + raw_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    skill_path = parsed.path.rstrip("/")
    return origin, skill_path


def extract_skill_name(html_text):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.S)
    return strip_tags(m.group(1)) if m else None


def extract_repository(html_text):
    """「Repository」ラベル近傍からGitHubリポジトリURLとVerified表示有無を取得する。"""
    pos = html_text.find("Repository</span>")
    if pos == -1:
        return None, None, None

    window = html_text[pos:pos + 1500]
    verified_org = "Verified organization on GitHub" in window

    m = re.search(r'href="(https://github\.com/[^"]+)"', window)
    repository_url = m.group(1) if m else None
    distributor = repository_url.split("github.com/")[-1] if repository_url else None
    return repository_url, distributor, verified_org


def extract_installs(html_text):
    m = re.search(r'Installs</span></div><div[^>]*>([^<]+)</div>', html_text)
    return clean_text(m.group(1)) if m else None


def extract_github_stars(html_text):
    m = re.search(r'GitHub Stars</span></div>.*?<span>([^<]+)</span>', html_text, re.S)
    return clean_text(m.group(1)) if m else None


def extract_security_audits(html_text, skill_path, origin):
    """Skill詳細ページ内の監査一覧（名称・判定・詳細URL）を取得する。"""
    if not skill_path:
        return []

    pattern = re.compile(
        r'href="(?P<href>' + re.escape(skill_path) + r'/security/[^"]+)"[^>]*>'
        r'.{0,400}?truncate">(?P<name>[^<]+)</span>'
        r'<span[^>]*>(?P<verdict>[^<]+)</span>',
        re.S,
    )

    audits = []
    seen_hrefs = set()
    for m in pattern.finditer(html_text):
        href = m.group("href")
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        audits.append({
            "name": clean_text(m.group("name")),
            "verdict": clean_text(m.group("verdict")),
            "detail_url": origin + href,
        })
    return audits


def extract_audit_detail(html_text):
    """個別監査の詳細ページから、警告理由に関する情報を取得する。取得できない項目はnull。"""
    detail = {
        "audited_by": None,
        "audited_on": None,
        "risk_level": None,
        "analyzed_at": None,
        "issues_count": None,
        "issues": [],
        "analysis": [],
    }

    m = re.search(
        r'Audited by.*?<span[^>]*>([^<]+)</span>\s*on.*?>([^<]+)</p>',
        html_text, re.S,
    )
    if m:
        detail["audited_by"] = clean_text(m.group(1))
        detail["audited_on"] = clean_text(m.group(2))

    m = re.search(r'Risk Level:\s*(?:<!--\s*-->)?([A-Za-z]+)', html_text)
    if m:
        detail["risk_level"] = clean_text(m.group(1))

    m = re.search(r'Analyzed</dt><dd[^>]*>([^<]+)</dd>', html_text)
    if m:
        detail["analyzed_at"] = clean_text(m.group(1))

    m = re.search(r'Issues</dt><dd[^>]*>([^<]+)</dd>', html_text)
    if m:
        detail["issues_count"] = clean_text(m.group(1))

    codes = re.findall(r'>\s*([A-Z]\d{3}):\s*([^<.]+\.)', html_text)
    detail["issues"] = [
        {"code": clean_text(code), "title": clean_text(title)}
        for code, title in codes
    ]

    fa_pos = html_text.find("Full Analysis</div>")
    if fa_pos != -1:
        fa_end = html_text.find("</section>", fa_pos)
        fa_block = html_text[fa_pos:fa_end if fa_end != -1 else fa_pos + 4000]
        items = re.findall(r"<li>(.*?)</li>", fa_block, re.S)
        if not items:
            items = re.findall(r"<p>(.*?)</p>", fa_block, re.S)
        detail["analysis"] = [strip_tags(item) for item in items if strip_tags(item)]

    return detail


def audit_one_url(raw_url):
    result = {
        "input_url": raw_url,
        "resolved_origin": None,
        "skill_path": None,
        "fetch_status": None,
        "error": None,
        "skill_name": None,
        "distributor": None,
        "repository_url": None,
        "verified_org": None,
        "installs": None,
        "github_stars": None,
        "security_audits": [],
    }

    try:
        origin, skill_path = normalize_input_url(raw_url)
        result["resolved_origin"] = origin
        result["skill_path"] = skill_path
    except Exception as exc:
        result["error"] = f"URLの解析に失敗しました: {exc}"
        return result

    try:
        status, html_text = fetch(origin + skill_path)
        result["fetch_status"] = status
    except urllib.error.HTTPError as exc:
        result["error"] = f"HTTPエラー: {exc.code} {exc.reason}"
        return result
    except urllib.error.URLError as exc:
        result["error"] = f"接続エラー: {exc.reason}"
        return result
    except Exception as exc:
        result["error"] = f"取得中に想定外のエラー: {exc}"
        return result

    if status != 200:
        result["error"] = f"ページ取得に失敗しました（ステータス: {status}）"
        return result

    result["skill_name"] = extract_skill_name(html_text)
    repository_url, distributor, verified_org = extract_repository(html_text)
    result["repository_url"] = repository_url
    result["distributor"] = distributor
    result["verified_org"] = verified_org
    result["installs"] = extract_installs(html_text)
    result["github_stars"] = extract_github_stars(html_text)

    audits = extract_security_audits(html_text, skill_path, origin)

    if result["skill_name"] is None and repository_url is None and not audits:
        result["error"] = (
            "ページは200で応答しましたが、Skill名・配布元・監査情報のいずれも見つかりませんでした。"
            "対象ページが存在しないか、想定と異なる構造の可能性があります。"
        )
        return result

    for audit in audits:
        verdict = (audit.get("verdict") or "").strip().lower()
        if verdict in PASS_VERDICTS:
            audit["detail"] = None
            audit["detail_error"] = None
            continue

        try:
            d_status, d_html = fetch(audit["detail_url"])
            if d_status != 200:
                audit["detail"] = None
                audit["detail_error"] = f"詳細ページ取得に失敗しました（ステータス: {d_status}）"
                continue
            audit["detail"] = extract_audit_detail(d_html)
            audit["detail_error"] = None
        except urllib.error.HTTPError as exc:
            audit["detail"] = None
            audit["detail_error"] = f"HTTPエラー: {exc.code} {exc.reason}"
        except urllib.error.URLError as exc:
            audit["detail"] = None
            audit["detail_error"] = f"接続エラー: {exc.reason}"
        except Exception as exc:
            audit["detail"] = None
            audit["detail_error"] = f"詳細ページ取得中に想定外のエラー: {exc}"

    result["security_audits"] = audits
    return result


def main():
    urls = sys.argv[1:]
    if not urls:
        print(json.dumps({
            "error": "引数にskills.shのSkill詳細ページURLを1件以上指定してください。",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    output = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "requested_urls": urls,
        "results": [audit_one_url(url) for url in urls],
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
