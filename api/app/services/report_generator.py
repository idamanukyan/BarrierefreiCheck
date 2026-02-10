"""
Report Generator Service

Generates accessibility scan reports in PDF, HTML, JSON, and CSV formats.
"""

import json
import csv
import io
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

from ..config import settings


class ReportFormat(str, Enum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV = "csv"


class ReportGenerator:
    """Generates accessibility reports in various formats."""

    def __init__(self):
        # Set up Jinja2 template environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Add custom filters
        self.env.filters["format_date"] = self._format_date
        self.env.filters["format_number"] = self._format_number
        self.env.filters["format_duration"] = self._format_duration
        self.env.filters["format_percent"] = self._format_percent

        self.font_config = FontConfiguration()

    def generate(
        self,
        scan_data: dict,
        format: ReportFormat,
        language: str = "de",
        include_screenshots: bool = True,
        branding: Optional[dict] = None,
    ) -> bytes:
        """
        Generate a report in the specified format.

        Args:
            scan_data: Complete scan results including pages and issues
            format: Output format (pdf, html, json, csv)
            language: Report language (de or en)
            include_screenshots: Whether to include issue screenshots
            branding: Optional branding config (logo, company_name)

        Returns:
            Report content as bytes
        """
        if format == ReportFormat.PDF:
            return self._generate_pdf(scan_data, language, include_screenshots, branding)
        elif format == ReportFormat.HTML:
            return self._generate_html(scan_data, language, include_screenshots, branding)
        elif format == ReportFormat.JSON:
            return self._generate_json(scan_data)
        elif format == ReportFormat.CSV:
            return self._generate_csv(scan_data, language)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_pdf(
        self,
        scan_data: dict,
        language: str,
        include_screenshots: bool,
        branding: Optional[dict],
    ) -> bytes:
        """Generate PDF report using WeasyPrint."""
        # First generate HTML
        html_content = self._render_html_template(
            scan_data, language, include_screenshots, branding
        )

        # Convert to PDF
        html = HTML(string=html_content, base_url=str(Path(__file__).parent.parent / "templates"))
        css = CSS(string=self._get_pdf_styles(), font_config=self.font_config)

        return html.write_pdf(stylesheets=[css], font_config=self.font_config)

    def _generate_html(
        self,
        scan_data: dict,
        language: str,
        include_screenshots: bool,
        branding: Optional[dict],
    ) -> bytes:
        """Generate standalone HTML report."""
        html_content = self._render_html_template(
            scan_data, language, include_screenshots, branding, standalone=True
        )
        return html_content.encode("utf-8")

    def _generate_json(self, scan_data: dict) -> bytes:
        """Generate JSON report."""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "BarrierefreiCheck",
            "version": "1.0.0",
            "scan": scan_data,
        }
        return json.dumps(report, indent=2, ensure_ascii=False, default=str).encode("utf-8")

    def _generate_csv(self, scan_data: dict, language: str) -> bytes:
        """Generate CSV report of issues."""
        output = io.StringIO()

        # CSV headers based on language
        if language == "de":
            headers = [
                "Seiten-URL",
                "Regel-ID",
                "Titel",
                "Schweregrad",
                "WCAG-Stufe",
                "WCAG-Kriterien",
                "BFSG-Referenz",
                "Beschreibung",
                "Lösungsvorschlag",
                "Element-Selektor",
                "HTML-Code",
            ]
        else:
            headers = [
                "Page URL",
                "Rule ID",
                "Title",
                "Impact",
                "WCAG Level",
                "WCAG Criteria",
                "BFSG Reference",
                "Description",
                "How to Fix",
                "Element Selector",
                "HTML Code",
            ]

        writer = csv.writer(output)
        writer.writerow(headers)

        # Write issues
        for page in scan_data.get("pages", []):
            page_url = page.get("url", "")
            for issue in page.get("issues", []):
                writer.writerow([
                    page_url,
                    issue.get("rule_id", ""),
                    issue.get("title", ""),
                    issue.get("impact", ""),
                    issue.get("wcag_level", ""),
                    ", ".join(issue.get("wcag_criteria", [])),
                    issue.get("bfsg_reference", ""),
                    issue.get("description", ""),
                    issue.get("fix", ""),
                    issue.get("element", {}).get("selector", ""),
                    issue.get("element", {}).get("html", "")[:500],  # Truncate long HTML
                ])

        return output.getvalue().encode("utf-8")

    def _render_html_template(
        self,
        scan_data: dict,
        language: str,
        include_screenshots: bool,
        branding: Optional[dict],
        standalone: bool = False,
    ) -> str:
        """Render the HTML template with scan data."""
        template = self.env.get_template(f"report_{language}.html")

        # Get translations
        translations = self._get_translations(language)

        # Calculate summary statistics
        summary = self._calculate_summary(scan_data)

        return template.render(
            scan=scan_data,
            summary=summary,
            translations=translations,
            include_screenshots=include_screenshots,
            branding=branding or {},
            standalone=standalone,
            generated_at=datetime.now(timezone.utc),
        )

    def _get_translations(self, language: str) -> dict:
        """Get report translations."""
        translations = {
            "de": {
                "report_title": "Barrierefreiheits-Bericht",
                "generated_on": "Erstellt am",
                "executive_summary": "Zusammenfassung",
                "overall_score": "Gesamtbewertung",
                "pages_scanned": "Gescannte Seiten",
                "total_issues": "Gefundene Probleme",
                "scan_duration": "Scan-Dauer",
                "issues_by_impact": "Probleme nach Schweregrad",
                "issues_by_wcag": "Probleme nach WCAG-Stufe",
                "critical": "Kritisch",
                "serious": "Schwerwiegend",
                "moderate": "Mittel",
                "minor": "Gering",
                "detailed_findings": "Detaillierte Ergebnisse",
                "page": "Seite",
                "issue": "Problem",
                "impact": "Schweregrad",
                "wcag_level": "WCAG-Stufe",
                "wcag_criteria": "WCAG-Kriterium",
                "bfsg_reference": "BFSG-Referenz",
                "description": "Beschreibung",
                "recommendation": "Lösungsvorschlag",
                "affected_element": "Betroffenes Element",
                "bfsg_compliance": "BFSG-Compliance",
                "compliant": "Konform",
                "partially_compliant": "Teilweise konform",
                "non_compliant": "Nicht konform",
                "methodology": "Methodik",
                "methodology_text": "Dieser Bericht wurde mit automatisierten Tests basierend auf axe-core generiert. Die Tests prüfen die Einhaltung von WCAG 2.1 Level AA und den Anforderungen des Barrierefreiheitsstärkungsgesetzes (BFSG). Automatisierte Tests können etwa 30-40% der Barrierefreiheitsprobleme erkennen. Für eine vollständige Bewertung wird eine manuelle Prüfung empfohlen.",
                "disclaimer": "Haftungsausschluss",
                "disclaimer_text": "Dieser Bericht stellt keine rechtliche Beratung dar. Die Ergebnisse basieren auf automatisierten Tests und ersetzen keine vollständige Barrierefreiheitsprüfung durch Experten.",
                "footer_text": "Erstellt mit BarrierefreiCheck",
            },
            "en": {
                "report_title": "Accessibility Report",
                "generated_on": "Generated on",
                "executive_summary": "Executive Summary",
                "overall_score": "Overall Score",
                "pages_scanned": "Pages Scanned",
                "total_issues": "Total Issues",
                "scan_duration": "Scan Duration",
                "issues_by_impact": "Issues by Severity",
                "issues_by_wcag": "Issues by WCAG Level",
                "critical": "Critical",
                "serious": "Serious",
                "moderate": "Moderate",
                "minor": "Minor",
                "detailed_findings": "Detailed Findings",
                "page": "Page",
                "issue": "Issue",
                "impact": "Severity",
                "wcag_level": "WCAG Level",
                "wcag_criteria": "WCAG Criterion",
                "bfsg_reference": "BFSG Reference",
                "description": "Description",
                "recommendation": "Recommendation",
                "affected_element": "Affected Element",
                "bfsg_compliance": "BFSG Compliance",
                "compliant": "Compliant",
                "partially_compliant": "Partially Compliant",
                "non_compliant": "Non-Compliant",
                "methodology": "Methodology",
                "methodology_text": "This report was generated using automated testing based on axe-core. The tests check compliance with WCAG 2.1 Level AA and the requirements of the German Accessibility Strengthening Act (BFSG). Automated tests can detect approximately 30-40% of accessibility issues. A manual review is recommended for a complete assessment.",
                "disclaimer": "Disclaimer",
                "disclaimer_text": "This report does not constitute legal advice. The results are based on automated tests and do not replace a complete accessibility audit by experts.",
                "footer_text": "Generated with BarrierefreiCheck",
            },
        }
        return translations.get(language, translations["de"])

    def _calculate_summary(self, scan_data: dict) -> dict:
        """Calculate summary statistics from scan data."""
        pages = scan_data.get("pages", [])
        all_issues = []

        for page in pages:
            all_issues.extend(page.get("issues", []))

        issues_by_impact = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
        issues_by_wcag = {"A": 0, "AA": 0, "AAA": 0}

        for issue in all_issues:
            impact = issue.get("impact", "minor")
            if impact in issues_by_impact:
                issues_by_impact[impact] += 1

            wcag_level = issue.get("wcag_level", "AA")
            if wcag_level in issues_by_wcag:
                issues_by_wcag[wcag_level] += 1

        # Calculate BFSG compliance status
        critical_serious = issues_by_impact["critical"] + issues_by_impact["serious"]
        if critical_serious == 0 and issues_by_impact["moderate"] <= 5:
            bfsg_status = "compliant"
        elif critical_serious <= 3:
            bfsg_status = "partially_compliant"
        else:
            bfsg_status = "non_compliant"

        return {
            "total_pages": len(pages),
            "total_issues": len(all_issues),
            "issues_by_impact": issues_by_impact,
            "issues_by_wcag": issues_by_wcag,
            "bfsg_status": bfsg_status,
            "score": scan_data.get("score", 0),
            "duration": scan_data.get("duration", 0),
        }

    def _get_pdf_styles(self) -> str:
        """Get CSS styles for PDF generation."""
        return """
        @page {
            size: A4;
            margin: 2cm;
            @top-center {
                content: "Barrierefreiheits-Bericht";
                font-size: 10pt;
                color: #666;
            }
            @bottom-center {
                content: "Seite " counter(page) " von " counter(pages);
                font-size: 10pt;
                color: #666;
            }
        }

        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #333;
        }

        h1 {
            font-size: 24pt;
            color: #1a365d;
            margin-bottom: 20pt;
            border-bottom: 2px solid #3182ce;
            padding-bottom: 10pt;
        }

        h2 {
            font-size: 16pt;
            color: #2c5282;
            margin-top: 20pt;
            margin-bottom: 10pt;
        }

        h3 {
            font-size: 13pt;
            color: #2d3748;
            margin-top: 15pt;
            margin-bottom: 8pt;
        }

        .summary-box {
            background: #f7fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15pt;
            margin: 15pt 0;
        }

        .score-circle {
            width: 80pt;
            height: 80pt;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24pt;
            font-weight: bold;
            color: white;
        }

        .score-excellent { background: #38a169; }
        .score-good { background: #3182ce; }
        .score-fair { background: #d69e2e; }
        .score-poor { background: #e53e3e; }

        .impact-critical { color: #c53030; font-weight: bold; }
        .impact-serious { color: #dd6b20; font-weight: bold; }
        .impact-moderate { color: #805ad5; }
        .impact-minor { color: #718096; }

        .issue-card {
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 12pt;
            margin: 10pt 0;
            page-break-inside: avoid;
        }

        .issue-card.critical { border-left: 4px solid #c53030; }
        .issue-card.serious { border-left: 4px solid #dd6b20; }
        .issue-card.moderate { border-left: 4px solid #805ad5; }
        .issue-card.minor { border-left: 4px solid #718096; }

        .code-block {
            background: #2d3748;
            color: #e2e8f0;
            padding: 10pt;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 9pt;
            overflow-wrap: break-word;
            white-space: pre-wrap;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10pt 0;
        }

        th, td {
            border: 1px solid #e2e8f0;
            padding: 8pt;
            text-align: left;
        }

        th {
            background: #edf2f7;
            font-weight: bold;
        }

        .badge {
            display: inline-block;
            padding: 2pt 8pt;
            border-radius: 10pt;
            font-size: 9pt;
            font-weight: bold;
        }

        .badge-critical { background: #fed7d7; color: #c53030; }
        .badge-serious { background: #feebc8; color: #c05621; }
        .badge-moderate { background: #e9d8fd; color: #6b46c1; }
        .badge-minor { background: #e2e8f0; color: #4a5568; }

        .wcag-badge { background: #bee3f8; color: #2b6cb0; }

        .bfsg-compliant { color: #38a169; }
        .bfsg-partial { color: #d69e2e; }
        .bfsg-non-compliant { color: #e53e3e; }

        .footer {
            margin-top: 30pt;
            padding-top: 15pt;
            border-top: 1px solid #e2e8f0;
            font-size: 9pt;
            color: #718096;
        }

        .screenshot {
            max-width: 100%;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            margin: 10pt 0;
        }
        """

    # Template filters
    @staticmethod
    def _format_date(value: datetime, format: str = "%d.%m.%Y %H:%M") -> str:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value.strftime(format)

    @staticmethod
    def _format_number(value: int) -> str:
        return f"{value:,}".replace(",", ".")

    @staticmethod
    def _format_duration(ms: int) -> str:
        seconds = ms // 1000
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"

    @staticmethod
    def _format_percent(value: float) -> str:
        return f"{value:.1f}%"
