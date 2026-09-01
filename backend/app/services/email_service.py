import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv


def send_password_reset_email(
    recipient_email: str,
    reset_link: str,
):
    """
    Sends a password reset email.
    """
    load_dotenv(override=True)

    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from_email = os.getenv("SMTP_FROM_EMAIL")

    if not all([smtp_server, smtp_username, smtp_password, smtp_from_email]):
        raise RuntimeError(
            "SMTP configuration is incomplete. "
            "Please verify the SMTP settings in the .env file."
        )

    message = EmailMessage()

    message["Subject"] = "EchoSphere Password Reset"
    message["From"] = smtp_from_email
    message["To"] = recipient_email

    message.set_content(
        f"""
Hello,

A request was received to reset your EchoSphere password.

Click the link below to reset your password:

{reset_link}

If you did not request this, you can safely ignore this email.

Regards,
EchoSphere Team
"""
    )

    assert smtp_server is not None
    assert smtp_username is not None
    assert smtp_password is not None

    with smtplib.SMTP(
        host=smtp_server,
        port=smtp_port,
    ) as smtp:
        smtp.starttls()

        smtp.login(
            user=smtp_username,
            password=smtp_password,
        )

        smtp.send_message(message)

