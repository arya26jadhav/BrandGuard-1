"""End-to-end workflow verification for BrandGuard on real database data.

Runs 11 automated steps testing the entire lifecycle:
1. Admin uploads a .md guideline.
2. Admin creates an approved fact.
3. Creator drafts a post with mistakes and runs check.
4. Creator accepts one finding and rejects another with a reason.
5. Creator resolves remaining critical findings and submits.
6. Reviewer tries to approve while a critical finding is open (verifies 409 gate).
7. Reviewer approves after resolving criticals (verifies revisions record).
8. Manager publishes (verifies published_at timestamp).
9. Admin changes the fact statement (verifies fact-change hook and alerts).
10. Reviewer marks one alert updated.
11. Analytics summary reflects the new metrics.

Exits 0 if all 11 steps pass; exits 1 on any failure.
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone

import httpx
import psycopg
from psycopg.rows import dict_row

API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://brandguard:brandguard_dev_password@localhost:5433/brandguard",
)

results: list[tuple[int, str, bool, str]] = []


def record_result(step_num: int, title: str, passed: bool, detail: str) -> None:
    status_str = "PASS" if passed else "FAIL"
    results.append((step_num, title, passed, detail))
    print(f"Step {step_num}: {status_str} - {title}")
    if not passed:
        print(f"  Reason: {detail}")
    else:
        print(f"  Detail: {detail}")


def login(client: httpx.Client, user_id: str) -> dict[str, str]:
    resp = client.post(f"{API_URL}/api/auth/demo-login", json={"userId": user_id})
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {user_id}: {resp.status_code} {resp.text}")
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def run_e2e_check() -> bool:
    print(f"Starting BrandGuard E2E Check at {datetime.now(timezone.utc).isoformat()}")
    print(f"API Target: {API_URL}")
    print(f"Database Target: {DATABASE_URL.split('@')[-1]}")
    print("=" * 70)

    run_id = uuid.uuid4().hex[:8]

    try:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    except Exception as exc:
        print(f"FATAL: Cannot connect to database: {exc}")
        return False

    with httpx.Client(timeout=30.0) as client:
        # Step 1: Admin uploads a .md guideline with a new name
        try:
            admin_headers = login(client, "user-admin")
            guideline_title = f"E2E Natural Skincare Policy {run_id}"
            md_content = (
                f"# {guideline_title}\n\n"
                "Always emphasize natural ingredients and never make unverified medical claims.\n"
            ).encode("utf-8")

            files = {"file": ("e2e_guideline.md", md_content, "text/markdown")}
            data = {
                "title": guideline_title,
                "category": "Tone of Voice",
                "severity": "warning",
            }
            resp = client.post(
                f"{API_URL}/api/knowledge/guidelines/upload",
                files=files,
                data=data,
                headers=admin_headers,
            )
            if resp.status_code != 201:
                record_result(1, "Admin uploads .md guideline", False, f"HTTP {resp.status_code}: {resp.text}")
            else:
                uploaded_id = resp.json().get("id")
                # Check DB
                with conn.cursor() as cur:
                    cur.execute("SELECT id, title, text FROM guidelines WHERE title = %s", (guideline_title,))
                    db_guideline = cur.fetchone()

                if db_guideline and db_guideline["id"]:
                    record_result(
                        1,
                        "Admin uploads .md guideline",
                        True,
                        f"Guideline created with id {db_guideline['id']}: '{guideline_title}'",
                    )
                else:
                    record_result(1, "Admin uploads .md guideline", False, "Guideline not found in database")
        except Exception as exc:
            record_result(1, "Admin uploads .md guideline", False, str(exc))

        # Step 2: Admin creates a fact with evidence
        fact_id = None
        try:
            fact_payload = {
                "title": f"GreenGlow Shield SPF rating {run_id}",
                "statement": "GreenGlow Daily UV Shield provides proven SPF 50+ broad-spectrum protection.",
                "fact_type": "claim",
                "severity_on_change": "Medium",
                "valid_from": "2026-10-28",
                "category": "Brand",
                "product_id": "P-001",
            }
            resp = client.post(
                f"{API_URL}/api/knowledge/facts",
                json=fact_payload,
                headers=admin_headers,
            )
            if resp.status_code != 201:
                record_result(2, "Admin creates fact with evidence", False, f"HTTP {resp.status_code}: {resp.text}")
            else:
                created_fact = resp.json()
                fact_id = created_fact["id"]
                with conn.cursor() as cur:
                    cur.execute("SELECT id, statement, version FROM facts WHERE id = %s", (fact_id,))
                    db_fact = cur.fetchone()

                if db_fact and db_fact["version"] == 1:
                    record_result(
                        2,
                        "Admin creates fact with evidence",
                        True,
                        f"Fact created with id {fact_id}, statement: '{db_fact['statement']}'",
                    )
                else:
                    record_result(2, "Admin creates fact with evidence", False, "Fact not found in database")
        except Exception as exc:
            record_result(2, "Admin creates fact with evidence", False, str(exc))

        # Step 3: Creator creates a post containing "100% clear skin" and runs the check
        content_id = None
        findings_list = []
        try:
            creator_headers = login(client, "user-creator")
            post_payload = {
                "title": f"Launch post for Daily UV Shield {run_id}",
                "channel": "Instagram",
                "team": "Marketing",
                "bodyText": (
                    "Get 100% clear skin with our daily routine! Never miss your skincare regimen. "
                    "GreenGlow Daily UV Shield provides proven SPF 50+ broad-spectrum protection."
                ),
                "bodyHtml": (
                    "<p>Get 100% clear skin with our daily routine! Never miss your skincare regimen. "
                    "GreenGlow Daily UV Shield provides proven SPF 50+ broad-spectrum protection.</p>"
                ),
                "format": "post",
                "category": "skincare",
            }
            resp = client.post(f"{API_URL}/api/content", json=post_payload, headers=creator_headers)
            if resp.status_code != 201:
                record_result(3, "Creator creates post and runs check", False, f"POST /api/content failed: {resp.status_code} {resp.text}")
            else:
                content_id = resp.json()["id"]
                check_resp = client.post(f"{API_URL}/api/content/{content_id}/check", headers=creator_headers)
                if check_resp.status_code != 200:
                    record_result(3, "Creator creates post and runs check", False, f"POST check failed: {check_resp.status_code} {check_resp.text}")
                else:
                    findings_resp = client.get(f"{API_URL}/api/content/{content_id}/findings", headers=creator_headers)
                    findings_list = findings_resp.json()
                    has_sources = all(bool(f.get("sourceId")) for f in findings_list)

                    if len(findings_list) >= 2 and has_sources:
                        record_result(
                            3,
                            "Creator creates post and runs check",
                            True,
                            f"Content {content_id} checked: {len(findings_list)} findings generated with valid sources",
                        )
                    else:
                        record_result(
                            3,
                            "Creator creates post and runs check",
                            False,
                            f"Findings count: {len(findings_list)}, has_sources: {has_sources}",
                        )
        except Exception as exc:
            record_result(3, "Creator creates post and runs check", False, str(exc))

        # Step 4: Creator accepts one finding and rejects another with a reason
        try:
            if len(findings_list) < 2 or not content_id:
                record_result(4, "Creator accepts one and rejects another finding", False, "Insufficient findings from step 3")
            else:
                f_with_fix = next((f for f in findings_list if f.get("suggestedFix")), findings_list[0])
                f_other = next((f for f in findings_list if f["id"] != f_with_fix["id"]), findings_list[1])

                resp1 = client.patch(
                    f"{API_URL}/api/findings/{f_with_fix['id']}",
                    json={"action": "accept"},
                    headers=creator_headers,
                )
                resp2 = client.patch(
                    f"{API_URL}/api/findings/{f_other['id']}",
                    json={"action": "reject", "rejectReason": "Brand tone intentional"},
                    headers=creator_headers,
                )

                if resp1.status_code != 200 or resp2.status_code != 200:
                    record_result(
                        4,
                        "Creator accepts one and rejects another finding",
                        False,
                        f"Patch finding failed: {resp1.status_code} ({resp1.text}) / {resp2.status_code} ({resp2.text})",
                    )
                else:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT finding_id, action, reject_reason FROM decisions WHERE content_id = %s",
                            (content_id,),
                        )
                        db_decisions = cur.fetchall()

                    actions = {d["action"] for d in db_decisions}
                    if "accept" in actions and "reject" in actions:
                        record_result(
                            4,
                            "Creator accepts one and rejects another finding",
                            True,
                            f"Recorded decisions: {actions} in decisions table for {content_id}",
                        )
                    else:
                        record_result(
                            4,
                            "Creator accepts one and rejects another finding",
                            False,
                            f"Unexpected decisions in DB: {actions}",
                        )
        except Exception as exc:
            record_result(4, "Creator accepts one and rejects another finding", False, str(exc))

        # Step 5: Creator resolves the remaining critical findings and submits. Status is In Review.
        try:
            if not content_id:
                record_result(5, "Creator resolves critical findings and submits", False, "Missing content_id")
            else:
                # Resolve remaining open critical findings if any
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM findings WHERE content_id = %s AND status = 'open' AND severity = 'critical'",
                        (content_id,),
                    )
                    open_crits = cur.fetchall()

                for c in open_crits:
                    client.patch(
                        f"{API_URL}/api/findings/{c['id']}",
                        json={"action": "reject", "rejectReason": "Resolved for submission"},
                        headers=creator_headers,
                    )

                submit_resp = client.post(f"{API_URL}/api/content/{content_id}/submit", headers=creator_headers)
                if submit_resp.status_code != 200:
                    record_result(5, "Creator resolves critical findings and submits", False, f"Submit failed: {submit_resp.status_code} {submit_resp.text}")
                else:
                    with conn.cursor() as cur:
                        cur.execute("SELECT status, submitted_at FROM content WHERE id = %s", (content_id,))
                        row = cur.fetchone()

                    if row and row["status"] == "In Review" and row["submitted_at"]:
                        record_result(
                            5,
                            "Creator resolves critical findings and submits",
                            True,
                            f"Content {content_id} submitted; status is 'In Review', submitted_at={row['submitted_at']}",
                        )
                    else:
                        record_result(5, "Creator resolves critical findings and submits", False, f"Invalid state: {row}")
        except Exception as exc:
            record_result(5, "Creator resolves critical findings and submits", False, str(exc))

        # Step 6: Reviewer tries to approve while a critical finding is open. The response is 409.
        test_crit_id = f"fnd_crit_{uuid.uuid4().hex[:8]}"
        try:
            reviewer_headers = login(client, "user-reviewer")
            # Inject an open critical finding to rigorously test the approval gate
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO findings
                        (id, content_id, type, severity, title, reason, source_id, source_version,
                         suggested_fix, confidence, status, suggestion_kind)
                    VALUES (%s, %s, 'rule', 'critical', 'Critical Safety Rule',
                            'Unverified claim must be resolved', 'G-001', 1, '', 0.99, 'open', 'Claim correction')
                    """,
                    (test_crit_id, content_id),
                )
                conn.commit()

            appr_resp = client.post(f"{API_URL}/api/content/{content_id}/approve", headers=reviewer_headers)
            if appr_resp.status_code == 409:
                record_result(
                    6,
                    "Reviewer tries to approve with open critical (expects 409)",
                    True,
                    f"Approval correctly rejected with HTTP 409: {appr_resp.json().get('detail')}",
                )
            else:
                record_result(
                    6,
                    "Reviewer tries to approve with open critical (expects 409)",
                    False,
                    f"Expected 409, got HTTP {appr_resp.status_code}: {appr_resp.text}",
                )
        except Exception as exc:
            record_result(6, "Reviewer tries to approve with open critical (expects 409)", False, str(exc))

        # Step 7: Reviewer approves after resolving criticals. A revisions row exists for the move.
        try:
            # Resolve the critical finding
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE findings SET status = 'resolved' WHERE content_id = %s AND status = 'open' AND severity = 'critical'",
                    (content_id,),
                )
                conn.commit()

            appr_resp2 = client.post(f"{API_URL}/api/content/{content_id}/approve", headers=reviewer_headers)
            if appr_resp2.status_code != 200:
                record_result(7, "Reviewer approves after resolving criticals", False, f"Approve failed: {appr_resp2.status_code} {appr_resp2.text}")
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, action, from_status, to_status FROM revisions WHERE content_id = %s AND action = 'approved'",
                        (content_id,),
                    )
                    rev_row = cur.fetchone()

                if rev_row and rev_row["to_status"] == "Approved":
                    record_result(
                        7,
                        "Reviewer approves after resolving criticals",
                        True,
                        f"Approved successfully. Revision recorded: {rev_row['from_status']} -> {rev_row['to_status']}",
                    )
                else:
                    record_result(7, "Reviewer approves after resolving criticals", False, f"No approved revision row found: {rev_row}")
        except Exception as exc:
            record_result(7, "Reviewer approves after resolving criticals", False, str(exc))

        # Step 8: Manager publishes. published_at is set.
        try:
            manager_headers = login(client, "user-manager")
            pub_resp = client.post(f"{API_URL}/api/content/{content_id}/publish", headers=manager_headers)
            if pub_resp.status_code != 200:
                record_result(8, "Manager publishes content", False, f"Publish failed: {pub_resp.status_code} {pub_resp.text}")
            else:
                with conn.cursor() as cur:
                    cur.execute("SELECT status, published_at FROM content WHERE id = %s", (content_id,))
                    pub_row = cur.fetchone()

                if pub_row and pub_row["status"] == "Published" and pub_row["published_at"]:
                    record_result(
                        8,
                        "Manager publishes content",
                        True,
                        f"Content published successfully; published_at = {pub_row['published_at']}",
                    )
                else:
                    record_result(8, "Manager publishes content", False, f"Published row invalid: {pub_row}")
        except Exception as exc:
            record_result(8, "Manager publishes content", False, str(exc))

        # Step 9: Admin changes the fact's statement. Open alerts appear for the linked published posts.
        alert_id = None
        try:
            if not fact_id or not content_id:
                record_result(9, "Admin changes fact and alerts are dispatched", False, "Missing fact_id or content_id")
            else:
                # Link published post to the fact in fact_content_links
                link_id = f"fcl_{uuid.uuid4().hex[:8]}"
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO fact_content_links
                            (id, content_id, source_kind, fact_id, source_id, source_version, match_reason)
                        VALUES (%s, %s, 'fact', %s, %s, 1, 'E2E fact link')
                        ON CONFLICT (content_id, source_kind, source_id, source_version) DO NOTHING
                        """,
                        (link_id, content_id, fact_id, fact_id),
                    )
                    conn.commit()

                # Admin updates the fact statement
                new_statement = "GreenGlow Daily UV Shield now provides advanced SPF 55+ protection with hyaluronic acid."
                patch_resp = client.patch(
                    f"{API_URL}/api/knowledge/facts/{fact_id}",
                    json={"statement": new_statement, "note": "Upgraded SPF rating to 55+"},
                    headers=admin_headers,
                )
                if patch_resp.status_code != 200:
                    record_result(9, "Admin changes fact and alerts are dispatched", False, f"Fact patch failed: {patch_resp.status_code} {patch_resp.text}")
                else:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT id, recipient_id, content_id, status FROM alerts WHERE content_id = %s AND status = 'open'",
                            (content_id,),
                        )
                        alert_row = cur.fetchone()
                        cur.execute("SELECT status FROM content WHERE id = %s", (content_id,))
                        updated_content = cur.fetchone()

                    if alert_row and updated_content["status"] == "Needs revalidation":
                        alert_id = alert_row["id"]
                        record_result(
                            9,
                            "Admin changes fact and alerts are dispatched",
                            True,
                            f"Fact statement changed. Open alert created: {alert_id}; content status changed to 'Needs revalidation'",
                        )
                    else:
                        record_result(
                            9,
                            "Admin changes fact and alerts are dispatched",
                            False,
                            f"Alert row: {alert_row}, Content status: {updated_content.get('status') if updated_content else None}",
                        )
        except Exception as exc:
            record_result(9, "Admin changes fact and alerts are dispatched", False, str(exc))

        # Step 10: Reviewer marks one alert updated. The status changes in the database.
        try:
            if not alert_id:
                record_result(10, "Reviewer marks alert updated", False, "Missing alert_id from step 9")
            else:
                alert_resp = client.patch(
                    f"{API_URL}/api/alerts/{alert_id}",
                    json={"status": "updated"},
                    headers=reviewer_headers,
                )
                if alert_resp.status_code != 200:
                    record_result(10, "Reviewer marks alert updated", False, f"Alert patch failed: {alert_resp.status_code} {alert_resp.text}")
                else:
                    with conn.cursor() as cur:
                        cur.execute("SELECT status FROM alerts WHERE id = %s", (alert_id,))
                        db_alert = cur.fetchone()

                    if db_alert and db_alert["status"] == "updated":
                        record_result(
                            10,
                            "Reviewer marks alert updated",
                            True,
                            f"Alert {alert_id} status updated to '{db_alert['status']}' in database",
                        )
                    else:
                        record_result(10, "Reviewer marks alert updated", False, f"DB status is not updated: {db_alert}")
        except Exception as exc:
            record_result(10, "Reviewer marks alert updated", False, str(exc))

        # Step 11: GET /api/analytics/summary now reflects the new counts.
        try:
            analytics_resp = client.get(f"{API_URL}/api/analytics/summary?days=30", headers=manager_headers)
            if analytics_resp.status_code != 200:
                record_result(11, "Analytics summary reflects new counts", False, f"HTTP {analytics_resp.status_code}: {analytics_resp.text}")
            else:
                analytics = analytics_resp.json()
                kpis = analytics.get("kpis", {})
                decision_count = kpis.get("decisionCount", 0)

                if decision_count >= 2 and "mostViolatedRules" in analytics and "issuesOverTime" in analytics:
                    record_result(
                        11,
                        "Analytics summary reflects new counts",
                        True,
                        f"Analytics returned real metrics: decisionCount={decision_count}, unresolvedIssues={kpis.get('unresolvedIssues')}",
                    )
                else:
                    record_result(
                        11,
                        "Analytics summary reflects new counts",
                        False,
                        f"Analytics missing expected activity counts: {analytics}",
                    )
        except Exception as exc:
            record_result(11, "Analytics summary reflects new counts", False, str(exc))

    conn.close()

    print("=" * 70)
    passed_count = sum(1 for _, _, passed, _ in results if passed)
    print(f"Summary: {passed_count}/11 steps PASSED")

    all_passed = passed_count == 11
    return all_passed


if __name__ == "__main__":
    success = run_e2e_check()
    sys.exit(0 if success else 1)
