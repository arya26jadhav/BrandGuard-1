"""Planted-mistake AI evaluation script for BrandGuard.

Runs the labelled dataset against the BrandGuard backend check pipeline,
evaluates recall, false positives, and AI status, and writes data/eval_results.json.

Run from backend directory with:
    python -m tests.run_eval
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.ai.prompt import PROMPT_VERSION
from app.config import get_settings


CHANNEL_MAP = {
    "instagram": "Instagram",
    "website": "Website",
    "email": "Email",
    "ad": "Ad",
}

RULE_SYNONYMS: dict[str, list[str]] = {
    "g-001": ["g-001", "unsupported_claim", "absolute", "guarantee", "100%"],
    "g-002": ["g-002", "superlative", "best", "fastest", "#1"],
    "g-003": ["g-003", "terminology", "client", "user", "customer"],
    "g-004": ["g-004", "disclaimer", "results may vary"],
    "g-009": ["g-009", "confidential", "project aurora", "aurora"],
    "g-010": ["g-010", "price", "f-004", "naming"],
    "g-011": ["g-011", "g-010", "f-001", "product name", "naming", "green glow"],
    "g-012": ["g-012", "g-008", "medical", "cure", "treat", "heal"],
    "g-013": ["g-013", "competitor", "brand name", "cetaphil", "neutrogena"],
    "f-005": ["f-005", "g-001", "sunscreen", "spf", "100% protection"],
    "f-007": ["f-007", "g-001", "acne", "removes acne", "unsupported"],
    "f-009": ["f-009", "cruelty-free", "certificate", "expired"],
    "unsupported_claim": ["unsupported_claim", "g-001", "f-007", "claim"],
}


def find_dataset_path() -> tuple[Path, str]:
    """Find and return the path to the labelled posts dataset."""
    candidates = [
        Path("tests/quality/labelled_posts.json"),
        Path("../tests/quality/labelled_posts.json"),
        Path("backend/tests/quality/labelled_posts.json"),
    ]
    for path in candidates:
        if path.is_file():
            return path.resolve(), str(path)
    raise FileNotFoundError("Could not find labelled_posts.json in expected locations")


def spans_overlap(find_start: int | None, find_end: int | None, exp_start: int, exp_end: int,
                  find_text: str, exp_text: str) -> bool:
    """Return True if character offsets overlap or either text contains the other."""
    if find_start is not None and find_end is not None and exp_start >= 0 and exp_end > exp_start:
        if max(find_start, exp_start) < min(find_end, exp_end):
            return True

    # Fallback to string containment
    norm_find = find_text.lower().strip()
    norm_exp = exp_text.lower().strip()
    if norm_find and norm_exp:
        if norm_find in norm_exp or norm_exp in norm_find:
            return True
    return False


def is_issue_match(expected_rule: str, finding: dict[str, Any]) -> bool:
    """Determine whether an expected rule matches a returned finding.

    Matching Logic:
    1. Exact or substring match on source_id (e.g. 'G-001', 'F-007').
    2. Case-insensitive substring match of the rule key in finding title or reason.
    3. Keyword synonym expansion (e.g. rule 'G-002' matches 'superlative' in finding title).
    """
    rule_lower = expected_rule.lower().strip()
    source_id = str(finding.get("sourceId") or "").lower().strip()
    title = str(finding.get("title") or "").lower().strip()
    reason = str(finding.get("reason") or "").lower().strip()
    suggestion_kind = str(finding.get("suggestionKind") or "").lower().strip()
    finding_type = str(finding.get("type") or "").lower().strip()

    # Direct match against sourceId
    if rule_lower and source_id:
        if rule_lower == source_id or rule_lower in source_id or source_id in rule_lower:
            return True

    # Synonym/family matching
    synonyms = RULE_SYNONYMS.get(rule_lower, [rule_lower])
    for syn in synonyms:
        if syn in source_id or syn in title or syn in reason or syn in suggestion_kind or syn in finding_type:
            return True

    return False


def match_findings(expected_findings: list[dict[str, Any]], returned_findings: list[dict[str, Any]],
                   post_text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Match expected findings against returned findings.

    Returns:
        matched_pairs: list of tuples (expected, returned)
        unmatched_expected: list of expected findings not found
        extra_findings: list of returned findings not matching any expected finding
    """
    matched: list[dict[str, Any]] = []
    unmatched_expected: list[dict[str, Any]] = []
    used_finding_indices: set[int] = set()

    for exp in expected_findings:
        exp_span = exp["span"]
        exp_rule = exp["rule"]
        exp_start = post_text.find(exp_span)
        exp_end = exp_start + len(exp_span) if exp_start >= 0 else -1

        found_match = False
        for idx, finding in enumerate(returned_findings):
            if idx in used_finding_indices:
                continue

            find_start = finding.get("start")
            find_end = finding.get("end")
            find_text = finding.get("originalText") or ""

            if spans_overlap(find_start, find_end, exp_start, exp_end, find_text, exp_span):
                if is_issue_match(exp_rule, finding):
                    matched.append({"expected": exp, "finding": finding})
                    used_finding_indices.add(idx)
                    found_match = True
                    break

        if not found_match:
            unmatched_expected.append(exp)

    extra_findings = [f for idx, f in enumerate(returned_findings) if idx not in used_finding_indices]
    return matched, unmatched_expected, extra_findings


def main() -> int:
    dataset_file, dataset_display_path = find_dataset_path()
    print(f"=== BrandGuard AI Evaluation ===")
    print(f"Loaded dataset: {dataset_display_path}")

    with open(dataset_file, "r", encoding="utf-8") as f:
        posts = json.load(f)

    settings = get_settings()
    model_name = settings.brandguard_model
    prompt_version = PROMPT_VERSION
    api_base = "http://localhost:8000"

    print(f"Prompt Version: {prompt_version}")
    print(f"Model Name:     {model_name}")
    print(f"Total Posts:    {len(posts)}")
    print("--------------------------------------------------------------------------------")

    client = httpx.Client(base_url=api_base, timeout=45.0)

    # 1. Login as creator
    login_resp = client.post("/api/auth/demo-login", json={"userId": "user-creator"})
    if login_resp.status_code != 200:
        print(f"ERROR: Login failed ({login_resp.status_code}): {login_resp.text}")
        return 1

    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    per_post_results: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {"success": 0, "cached": 0, "fallback": 0, "failed": 0}

    total_expected = 0
    total_matched = 0
    clean_posts_count = 0
    false_positives_clean = 0
    total_extra_findings = 0
    rule_stats: dict[str, dict[str, int]] = {}

    for post in posts:
        post_id = post["id"]
        raw_channel = post.get("channel", "website")
        channel = CHANNEL_MAP.get(raw_channel.lower(), "Website")
        text = post["text"]
        expected_findings = post.get("expected_findings", [])
        is_clean = len(expected_findings) == 0
        if is_clean:
            clean_posts_count += 1

        total_expected += len(expected_findings)
        for exp in expected_findings:
            rule_family = exp["rule"]
            if rule_family not in rule_stats:
                rule_stats[rule_family] = {"expected": 0, "matched": 0}
            rule_stats[rule_family]["expected"] += 1

        # Create content
        create_payload = {
            "title": f"Eval {post_id}",
            "channel": channel,
            "team": "Marketing",
            "bodyText": text,
            "bodyHtml": f"<p>{text}</p>",
        }
        create_res = client.post("/api/content", json=create_payload, headers=headers)
        if create_res.status_code != 201:
            print(f"[{post_id}] Failed to create content ({create_res.status_code}): {create_res.text}")
            status_counts["failed"] += 1
            per_post_results.append({
                "id": post_id,
                "channel": channel,
                "text": text,
                "aiStatus": "failed",
                "error": create_res.text,
            })
            continue

        content_id = create_res.json()["id"]

        # Run check (retry up to 3 times if rate-limited)
        check_data = None
        for attempt in range(3):
            check_res = client.post(f"/api/content/{content_id}/check", headers=headers)
            if check_res.status_code == 200:
                check_data = check_res.json()
                break
            elif check_res.status_code == 429:
                print(f"[{post_id}] Rate limited, backing off 5s (attempt {attempt + 1})...")
                time.sleep(5)
            else:
                print(f"[{post_id}] Check failed with HTTP {check_res.status_code}: {check_res.text}")
                break

        if not check_data:
            status_counts["failed"] += 1
            per_post_results.append({
                "id": post_id,
                "channel": channel,
                "text": text,
                "aiStatus": "failed",
            })
            continue

        ai_status = check_data.get("aiStatus", "unknown")
        check_run_id = check_data.get("checkRunId", "")
        status_counts[ai_status] = status_counts.get(ai_status, 0) + 1

        returned_findings = check_data.get("findings", [])
        matched, unmatched_exp, extra = match_findings(expected_findings, returned_findings, text)

        matched_count = len(matched)
        total_matched += matched_count
        extra_count = len(extra)
        total_extra_findings += extra_count

        if is_clean and extra_count > 0:
            false_positives_clean += extra_count

        for m in matched:
            rule_family = m["expected"]["rule"]
            rule_stats[rule_family]["matched"] += 1

        post_record = {
            "id": post_id,
            "channel": channel,
            "text": text,
            "expectedCount": len(expected_findings),
            "matchedCount": matched_count,
            "unmatchedExpected": unmatched_exp,
            "extraFindings": extra,
            "aiStatus": ai_status,
            "checkRunId": check_run_id,
        }
        per_post_results.append(post_record)

        # Print per post summary
        status_symbol = "OK" if len(unmatched_exp) == 0 and (not is_clean or extra_count == 0) else "MISMATCH"
        print(
            f"[{post_id}] ({channel:9s}) Status: {ai_status:7s} | Expected: {len(expected_findings)} "
            f"| Matched: {matched_count} | Extra: {extra_count} -> {status_symbol}"
        )
        if unmatched_exp:
            for u in unmatched_exp:
                print(f"   [MISSED] Rule: {u['rule']} | Span: '{u['span']}'")
        if extra:
            for ex in extra:
                print(f"   [EXTRA]  Source: {ex.get('sourceId')} | Title: '{ex.get('title')}' | Quote: '{ex.get('originalText')}'")

    # Compute overall metrics
    recall = (total_matched / total_expected) if total_expected > 0 else 1.0
    recall_by_rule = {}
    for r, counts in sorted(rule_stats.items()):
        r_exp = counts["expected"]
        r_rec = (counts["matched"] / r_exp) if r_exp > 0 else 1.0
        recall_by_rule[r] = {
            "expected": r_exp,
            "matched": counts["matched"],
            "recall": round(r_rec, 3),
        }

    totals = {
        "totalPosts": len(posts),
        "cleanPosts": clean_posts_count,
        "totalExpected": total_expected,
        "totalMatched": total_matched,
        "overallRecall": round(recall, 3),
        "falsePositivesCleanPosts": false_positives_clean,
        "totalExtraFindings": total_extra_findings,
        "recallByRule": recall_by_rule,
    }

    print("\n============================== EVALUATION SUMMARY ==============================")
    print(f"Total Posts Evaluated:          {totals['totalPosts']} (Clean: {totals['cleanPosts']})")
    print(f"Expected Planted Issues:       {totals['totalExpected']}")
    print(f"Matched Issues (Found):        {totals['totalMatched']}")
    print(f"Overall Recall:                {totals['overallRecall']:.1%}")
    print(f"False Positives on Clean Posts:{totals['falsePositivesCleanPosts']}")
    print(f"Total Extra Findings:          {totals['totalExtraFindings']}")
    print("\nAI Status Distribution:")
    for st, count in status_counts.items():
        print(f"  {st:10s}: {count}")

    print("\nRecall by Rule Family:")
    for r, stats in recall_by_rule.items():
        print(f"  {r:15s}: {stats['matched']}/{stats['expected']} ({stats['recall']:.1%})")
    print("================================================================================")

    # Output to data/eval_results.json
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir = Path("../data")
    data_dir.mkdir(parents=True, exist_ok=True)
    results_file = data_dir / "eval_results.json"

    eval_data = {
        "runTimestamp": datetime.now(timezone.utc).isoformat(),
        "promptVersion": prompt_version,
        "modelName": model_name,
        "datasetPath": dataset_display_path,
        "totals": totals,
        "aiStatusCounts": status_counts,
        "posts": per_post_results,
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(eval_data, f, indent=2)

    print(f"\nSaved results to {results_file.resolve()}")

    # Exit code 2 if ANY post has aiStatus other than success or cached
    non_ai_count = status_counts.get("fallback", 0) + status_counts.get("failed", 0)
    if non_ai_count > 0:
        print(f"\nWARNING: {non_ai_count} post(s) had non-AI status (fallback or failed). Exiting with code 2.")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())

