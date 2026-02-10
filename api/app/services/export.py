"""
Export Service

Export scan data to various formats (CSV, JSON).
"""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models import Scan, Page, Issue, ImpactLevel


class ExportService:
    """Service for exporting scan data to various formats."""

    @staticmethod
    def issues_to_csv(issues: List[Issue], include_html: bool = False) -> str:
        """
        Export issues to CSV format.

        Args:
            issues: List of Issue objects
            include_html: Whether to include element HTML (can be large)

        Returns:
            CSV string
        """
        output = io.StringIO()

        fieldnames = [
            "id",
            "page_url",
            "rule_id",
            "impact",
            "wcag_criteria",
            "wcag_level",
            "bfsg_reference",
            "title_de",
            "description_de",
            "fix_suggestion_de",
            "element_selector",
            "help_url",
        ]

        if include_html:
            fieldnames.append("element_html")

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for issue in issues:
            row = {
                "id": str(issue.id),
                "page_url": issue.page.url if issue.page else "",
                "rule_id": issue.rule_id,
                "impact": issue.impact.value if issue.impact else "",
                "wcag_criteria": ",".join(issue.wcag_criteria or []),
                "wcag_level": issue.wcag_level.value if issue.wcag_level else "",
                "bfsg_reference": issue.bfsg_reference or "",
                "title_de": issue.title_de,
                "description_de": issue.description_de or "",
                "fix_suggestion_de": issue.fix_suggestion_de or "",
                "element_selector": issue.element_selector or "",
                "help_url": issue.help_url or "",
            }

            if include_html:
                row["element_html"] = issue.element_html or ""

            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def issues_to_json(issues: List[Issue], include_html: bool = True) -> str:
        """
        Export issues to JSON format.

        Args:
            issues: List of Issue objects
            include_html: Whether to include element HTML

        Returns:
            JSON string
        """
        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_issues": len(issues),
            "issues": []
        }

        for issue in issues:
            issue_data = {
                "id": str(issue.id),
                "page_url": issue.page.url if issue.page else None,
                "rule_id": issue.rule_id,
                "impact": issue.impact.value if issue.impact else None,
                "wcag": {
                    "criteria": issue.wcag_criteria,
                    "level": issue.wcag_level.value if issue.wcag_level else None,
                },
                "bfsg_reference": issue.bfsg_reference,
                "title_de": issue.title_de,
                "description_de": issue.description_de,
                "fix_suggestion_de": issue.fix_suggestion_de,
                "element": {
                    "selector": issue.element_selector,
                    "xpath": issue.element_xpath,
                },
                "help_url": issue.help_url,
                "screenshot_url": issue.screenshot_path,
            }

            if include_html:
                issue_data["element"]["html"] = issue.element_html

            data["issues"].append(issue_data)

        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def scan_summary_to_json(scan: Scan, pages: List[Page], issues: List[Issue]) -> str:
        """
        Export full scan summary to JSON.

        Args:
            scan: Scan object
            pages: List of scanned pages
            issues: List of issues found

        Returns:
            JSON string
        """
        # Count issues by impact
        issues_by_impact = {
            "critical": 0,
            "serious": 0,
            "moderate": 0,
            "minor": 0,
        }
        for issue in issues:
            if issue.impact:
                issues_by_impact[issue.impact.value] += 1

        # Count issues by WCAG criteria
        wcag_counts: Dict[str, int] = {}
        for issue in issues:
            for criteria in (issue.wcag_criteria or []):
                wcag_counts[criteria] = wcag_counts.get(criteria, 0) + 1

        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "scan": {
                "id": str(scan.id),
                "url": scan.url,
                "status": scan.status.value if scan.status else None,
                "score": scan.score,
                "created_at": scan.created_at.isoformat() if scan.created_at else None,
                "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
                "duration_seconds": scan.duration_seconds,
            },
            "summary": {
                "pages_scanned": len(pages),
                "total_issues": len(issues),
                "issues_by_impact": issues_by_impact,
                "issues_by_wcag": dict(sorted(wcag_counts.items())),
            },
            "pages": [
                {
                    "url": page.url,
                    "title": page.title,
                    "score": page.score,
                    "issues_count": page.issues_count,
                    "load_time_ms": page.load_time_ms,
                }
                for page in pages
            ],
        }

        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def pages_to_csv(pages: List[Page]) -> str:
        """
        Export pages to CSV format.

        Args:
            pages: List of Page objects

        Returns:
            CSV string
        """
        output = io.StringIO()

        fieldnames = [
            "id",
            "url",
            "title",
            "depth",
            "score",
            "issues_count",
            "passed_rules",
            "failed_rules",
            "load_time_ms",
            "scan_time_ms",
            "error",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for page in pages:
            writer.writerow({
                "id": str(page.id),
                "url": page.url,
                "title": page.title or "",
                "depth": page.depth,
                "score": page.score,
                "issues_count": page.issues_count,
                "passed_rules": page.passed_rules,
                "failed_rules": page.failed_rules,
                "load_time_ms": page.load_time_ms,
                "scan_time_ms": page.scan_time_ms,
                "error": page.error or "",
            })

        return output.getvalue()


# Global service instance
export_service = ExportService()


def get_export_service() -> ExportService:
    """Get the export service instance."""
    return export_service
