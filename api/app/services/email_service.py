"""
Email Service

Handles sending transactional emails for notifications and reports.
"""

import smtplib
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List
import logging

from ..config import settings

logger = logging.getLogger(__name__)


def escape_html(text: str) -> str:
    """Escape HTML special characters to prevent XSS."""
    if text is None:
        return ""
    return html.escape(str(text))


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME

    async def send_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[tuple]] = None,
    ) -> bool:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Plain text body (optional)
            attachments: List of (filename, content, mime_type) tuples

        Returns:
            True if email was sent successfully
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to

            # Add text part
            if text_content:
                part1 = MIMEText(text_content, "plain", "utf-8")
                msg.attach(part1)

            # Add HTML part
            part2 = MIMEText(html_content, "html", "utf-8")
            msg.attach(part2)

            # Add attachments
            if attachments:
                for filename, content, mime_type in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={filename}",
                    )
                    msg.attach(part)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to, msg.as_string())

            logger.info(f"Email sent successfully to {to}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False

    async def send_scan_complete_notification(
        self,
        to: str,
        user_name: str,
        scan_url: str,
        scan_id: str,
        score: int,
        issues_count: int,
        language: str = "de",
    ) -> bool:
        """Send scan completion notification."""
        # Escape user-provided data to prevent XSS
        safe_user_name = escape_html(user_name)
        safe_scan_url = escape_html(scan_url)
        safe_scan_id = escape_html(scan_id)
        score_color = '#38a169' if score >= 70 else '#e53e3e'

        if language == "de":
            subject = f"Scan abgeschlossen: {safe_scan_url}"
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background: #f9fafb; }}
                    .score {{ font-size: 48px; font-weight: bold; color: {score_color}; }}
                    .button {{ display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Scan abgeschlossen</h1>
                    </div>
                    <div class="content">
                        <p>Hallo {safe_user_name},</p>
                        <p>Ihr Barrierefreiheits-Scan für <strong>{safe_scan_url}</strong> wurde abgeschlossen.</p>

                        <h2>Ergebnisse</h2>
                        <p class="score">{int(score)}%</p>
                        <p>Gefundene Probleme: <strong>{int(issues_count)}</strong></p>

                        <p>
                            <a href="{settings.FRONTEND_URL}/scans/{safe_scan_id}" class="button">
                                Ergebnisse ansehen
                            </a>
                        </p>

                        <p>Mit freundlichen Grüßen,<br>Ihr BarrierefreiCheck Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
        else:
            subject = f"Scan complete: {safe_scan_url}"
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background: #f9fafb; }}
                    .score {{ font-size: 48px; font-weight: bold; color: {score_color}; }}
                    .button {{ display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Scan Complete</h1>
                    </div>
                    <div class="content">
                        <p>Hello {safe_user_name},</p>
                        <p>Your accessibility scan for <strong>{safe_scan_url}</strong> has been completed.</p>

                        <h2>Results</h2>
                        <p class="score">{int(score)}%</p>
                        <p>Issues found: <strong>{int(issues_count)}</strong></p>

                        <p>
                            <a href="{settings.FRONTEND_URL}/scans/{safe_scan_id}" class="button">
                                View Results
                            </a>
                        </p>

                        <p>Best regards,<br>The BarrierefreiCheck Team</p>
                    </div>
                </div>
            </body>
            </html>
            """

        return await self.send_email(to, subject, html_content)

    async def send_report_ready_notification(
        self,
        to: str,
        user_name: str,
        scan_url: str,
        report_id: str,
        format: str,
        language: str = "de",
    ) -> bool:
        """Send report ready notification."""
        # Escape user-provided data to prevent XSS
        safe_user_name = escape_html(user_name)
        safe_scan_url = escape_html(scan_url)
        safe_report_id = escape_html(report_id)
        safe_format = escape_html(format).upper()

        if language == "de":
            subject = f"Ihr Bericht ist fertig: {safe_scan_url}"
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background: #f9fafb; }}
                    .button {{ display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Bericht bereit</h1>
                    </div>
                    <div class="content">
                        <p>Hallo {safe_user_name},</p>
                        <p>Ihr {safe_format}-Bericht für <strong>{safe_scan_url}</strong> wurde erstellt und steht zum Download bereit.</p>

                        <p>
                            <a href="{settings.FRONTEND_URL}/reports/{safe_report_id}/download" class="button">
                                Bericht herunterladen
                            </a>
                        </p>

                        <p>Der Bericht ist 7 Tage lang verfügbar.</p>

                        <p>Mit freundlichen Grüßen,<br>Ihr BarrierefreiCheck Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
        else:
            subject = f"Your report is ready: {safe_scan_url}"
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background: #f9fafb; }}
                    .button {{ display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Report Ready</h1>
                    </div>
                    <div class="content">
                        <p>Hello {safe_user_name},</p>
                        <p>Your {safe_format} report for <strong>{safe_scan_url}</strong> has been generated and is ready for download.</p>

                        <p>
                            <a href="{settings.FRONTEND_URL}/reports/{safe_report_id}/download" class="button">
                                Download Report
                            </a>
                        </p>

                        <p>The report will be available for 7 days.</p>

                        <p>Best regards,<br>The BarrierefreiCheck Team</p>
                    </div>
                </div>
            </body>
            </html>
            """

        return await self.send_email(to, subject, html_content)
