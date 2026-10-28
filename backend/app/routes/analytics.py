"""Analytics summary endpoint for BrandGuard.

Aggregates KPIs, rule violations, rejected suggestions, issue trends,
and review times across content and workflow history.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from app.db import get_conn
from app.security import require_role

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

ANALYTICS_ROLES = ("manager", "admin")


@router.get("/summary")
def get_analytics_summary(
    days: int = Query(default=30, ge=1),
    conn: Connection = Depends(get_conn),
    _user: dict = Depends(require_role(*ANALYTICS_ROLES)),
) -> dict[str, Any]:
    """Return aggregated analytics summary for the given time window in days.

    Manager and admin only.
    """
    days_str = str(days)

    # 1. Review time KPIs and reviewTimeByTeam
    # Threshold: >= 5 approved items across >= 2 teams
    review_rows = conn.execute(
        """
        SELECT team,
               EXTRACT(EPOCH FROM (approved_at - submitted_at)) / 60.0 AS duration_minutes
        FROM content
        WHERE approved_at IS NOT NULL
          AND submitted_at IS NOT NULL
          AND approved_at >= NOW() - (%s || ' days')::INTERVAL
        """,
        (days_str,),
    ).fetchall()

    items_count = len(review_rows)
    distinct_teams = {r["team"] for r in review_rows}

    if items_count >= 5 and len(distinct_teams) >= 2:
        avg_review_minutes: float | None = round(
            sum(float(r["duration_minutes"]) for r in review_rows) / items_count, 1
        )
        team_groups: dict[str, list[float]] = defaultdict(list)
        for r in review_rows:
            team_groups[r["team"]].append(float(r["duration_minutes"]))
        review_time_by_team = [
            {"team": team, "avgMinutes": round(sum(durs) / len(durs), 1)}
            for team, durs in team_groups.items()
        ]
        review_time_by_team.sort(key=lambda x: x["avgMinutes"], reverse=True)
    else:
        avg_review_minutes = None
        review_time_by_team = []

    # 2. Unresolved issues (findings with status 'open')
    unresolved_row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM findings
        WHERE status = 'open'
        """
    ).fetchone()
    unresolved_issues = int(unresolved_row["count"]) if unresolved_row else 0

    # 3. Outdated published posts (distinct content_id in alerts with status 'open')
    outdated_row = conn.execute(
        """
        SELECT COUNT(DISTINCT content_id) AS count
        FROM alerts
        WHERE status = 'open'
        """
    ).fetchone()
    outdated_posts = int(outdated_row["count"]) if outdated_row else 0

    # 4. Decisions KPIs: suggestionsAcceptedPct & decisionCount
    # Threshold: null unless >= 10 decisions
    decision_rows = conn.execute(
        """
        SELECT action, COUNT(*) AS count
        FROM decisions
        WHERE created_at >= NOW() - (%s || ' days')::INTERVAL
        GROUP BY action
        """,
        (days_str,),
    ).fetchall()

    decision_count = sum(int(r["count"]) for r in decision_rows)
    accepted_count = sum(
        int(r["count"]) for r in decision_rows if r["action"] == "accept"
    )
    rejected_count = sum(
        int(r["count"]) for r in decision_rows if r["action"] == "reject"
    )

    if decision_count >= 10:
        suggestions_accepted_pct: float | None = round(
            100.0 * accepted_count / decision_count, 1
        )
    else:
        suggestions_accepted_pct = None

    # 5. Most rejected suggestions:
    # Threshold: [] unless >= 5 decisions with >= 1 rejection
    if decision_count >= 5 and rejected_count >= 1:
        rejected_rows = conn.execute(
            """
            SELECT f.suggestion_kind, COUNT(*) AS count
            FROM decisions d
            JOIN findings f ON f.id = d.finding_id
            WHERE d.action = 'reject'
              AND d.created_at >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY f.suggestion_kind
            ORDER BY count DESC, f.suggestion_kind
            """,
            (days_str,),
        ).fetchall()
        most_rejected_suggestions = [
            {
                "type": r["suggestion_kind"],
                "label": r["suggestion_kind"],
                "count": int(r["count"]),
            }
            for r in rejected_rows
        ]
    else:
        most_rejected_suggestions = []

    # 6. Most violated rules:
    # Threshold: [] unless >= 5 findings; top 5 by count of findings grouped by source_id
    findings_rows = conn.execute(
        """
        SELECT f.source_id,
               COUNT(*) AS count,
               COALESCE(
                   g.title,
                   MODE() WITHIN GROUP (ORDER BY f.title)
               ) AS label
        FROM findings f
        LEFT JOIN guidelines g ON g.id = f.source_id
        WHERE f.created_at >= NOW() - (%s || ' days')::INTERVAL
        GROUP BY f.source_id, g.title
        ORDER BY count DESC, f.source_id
        """,
        (days_str,),
    ).fetchall()

    total_findings = sum(int(r["count"]) for r in findings_rows)
    if total_findings >= 5:
        most_violated_rules = [
            {
                "ruleId": r["source_id"],
                "label": r["label"] or r["source_id"],
                "count": int(r["count"]),
            }
            for r in findings_rows[:5]
        ]
    else:
        most_violated_rules = []

    # 7. Issues over time:
    # findings joined to check_runs on check_run_id, grouped by day of started_at, within the window
    trend_rows = conn.execute(
        """
        SELECT TO_CHAR(cr.started_at AT TIME ZONE 'UTC', 'YYYY-MM-DD') AS date,
               COUNT(*) FILTER (WHERE f.severity = 'critical') AS critical,
               COUNT(*) FILTER (WHERE f.severity = 'warning') AS warning,
               COUNT(*) FILTER (WHERE f.severity = 'info') AS info
        FROM findings f
        JOIN check_runs cr ON cr.id = f.check_run_id
        WHERE cr.started_at >= NOW() - (%s || ' days')::INTERVAL
        GROUP BY date
        ORDER BY date ASC
        """,
        (days_str,),
    ).fetchall()

    issues_over_time = [
        {
            "date": r["date"],
            "critical": int(r["critical"]),
            "warning": int(r["warning"]),
            "info": int(r["info"]),
        }
        for r in trend_rows
    ]

    return {
        "kpis": {
            "avgReviewMinutes": avg_review_minutes,
            "avgReviewItems": items_count,
            "unresolvedIssues": unresolved_issues,
            "outdatedPublishedPosts": outdated_posts,
            "suggestionsAcceptedPct": suggestions_accepted_pct,
            "decisionCount": decision_count,
        },
        "mostViolatedRules": most_violated_rules,
        "mostRejectedSuggestions": most_rejected_suggestions,
        "issuesOverTime": issues_over_time,
        "reviewTimeByTeam": review_time_by_team,
    }
