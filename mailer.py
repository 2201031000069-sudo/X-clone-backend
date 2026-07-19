import os
import logging
from email.mime.text import MIMEText

logger = logging.getLogger("mailer")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@nextweet.app")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


async def send_reset_email(recipient_email: str, token: str) -> None:
    reset_link = f"{FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    subject = "Reset your Nextweet password"
    body = f"""
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
  <h2 style="font-size: 20px; font-weight: 700; margin-bottom: 8px;">Password Reset</h2>
  <p style="font-size: 15px; color: #555; line-height: 1.5;">
    We received a request to reset your Nextweet password.
    Click the button below to set a new one. This link expires in 1 hour.
  </p>
  <a href="{reset_link}"
     style="display: inline-block; margin: 16px 0; padding: 12px 28px; border-radius: 9999px;
            background-color: #1d9bf0; color: #fff; text-decoration: none; font-size: 15px; font-weight: 600;">
    Reset password
  </a>
  <p style="font-size: 13px; color: #999;">
    If you didn't request this, you can safely ignore this email.
  </p>
  <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
  <p style="font-size: 12px; color: #bbb;">
    Nextweet · {FRONTEND_URL}
  </p>
</body>
</html>
"""

    await _send_email(recipient_email, subject, body)


async def _send_email(to: str, subject: str, html: str) -> None:
    if not SMTP_HOST:
        logger.warning(
            "SMTP not configured. To send real emails, set SMTP_HOST, SMTP_PORT, "
            "SMTP_USER, SMTP_PASS, and EMAIL_FROM environment variables."
        )
        return

    msg = MIMEText(html, "html")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to

    try:
        import aiosmtplib

        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASS,
            start_tls=True,
        )
        logger.info("Email sent to %s — subject: %s", to, subject)
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
