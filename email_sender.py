"""
email_sender.py
──────────────────────
Sends the generated Excel report as an email attachment via Gmail SMTP.

Requires in config.py:

SENDER_EMAIL
SENDER_PASSWORD
"""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from config import SENDER_EMAIL, SENDER_PASSWORD


def send_excel_report(
    recipient_email: str,
    recipient_name: str,
    excel_path: str,
    sender_email: str = None,
    sender_password: str = None,
) -> tuple[bool, str]:
    """
    Sends generated Excel report via Gmail SMTP.
    """

    sender_email = sender_email or SENDER_EMAIL
    sender_password = sender_password or SENDER_PASSWORD

    if not sender_email:
        return False, (
            "SENDER_EMAIL not found in config.py"
        )

    if not sender_password:
        return False, (
            "SENDER_PASSWORD not found in config.py.\n"
            "Use a Gmail App Password."
        )

    if not os.path.exists(excel_path):
        return False, (
            f"Excel file not found:\n{excel_path}"
        )

    try:
        msg = MIMEMultipart()

        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = (
            "eCourts Legal Analytics Report — "
            f"{datetime.now().strftime('%d %B %Y')}"
        )

        body = f"""
Dear {recipient_name},

Please find attached your eCourts Legal Analytics Report.

This report contains:

• Case details for all entered CNR numbers
• Hearing history and next hearing dates
• Court and advocate information
• AI-generated summaries of latest court orders
• Case analytics and legal insights

Generated on:
{datetime.now().strftime('%d %B %Y at %H:%M')}

Regards,
eCourts Legal Analytics
"""

        msg.attach(
            MIMEText(body, "plain")
        )

        filename = os.path.basename(
            excel_path
        )

        with open(excel_path, "rb") as f:

            attachment = MIMEBase(
                "application",
                "octet-stream",
            )

            attachment.set_payload(
                f.read()
            )

        encoders.encode_base64(
            attachment
        )

        attachment.add_header(
            "Content-Disposition",
            f'attachment; filename="{filename}"',
        )

        msg.attach(
            attachment
        )

        with smtplib.SMTP(
            "smtp.gmail.com",
            587,
            timeout=30,
        ) as server:

            server.ehlo()
            server.starttls()
            server.ehlo()

            server.login(
                sender_email,
                sender_password,
            )

            server.send_message(
                msg
            )

        return (
            True,
            f"Report sent successfully to {recipient_email}"
        )

    except smtplib.SMTPAuthenticationError:

        return (
            False,
            "Gmail authentication failed.\n"
            "Use a Gmail App Password "
            "(not your account password)."
        )

    except smtplib.SMTPRecipientsRefused:

        return (
            False,
            f"Recipient rejected:\n{recipient_email}"
        )

    except smtplib.SMTPException as e:

        return (
            False,
            f"SMTP Error:\n{e}"
        )

    except TimeoutError:

        return (
            False,
            "Connection timed out."
        )

    except Exception as e:

        return (
            False,
            f"Unexpected error:\n{e}"
        )