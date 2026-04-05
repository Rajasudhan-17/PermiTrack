#!/usr/bin/env python3

from leave_app import create_app


app = create_app()


with app.app_context():
    from leave_app.services.emailing import send_email_now

    try:
        recipient = app.config.get("SMTP_TEST_RECIPIENT") or app.config.get("MAIL_DEFAULT_SENDER")
        if not app.config.get("MAIL_SERVER"):
            raise RuntimeError("MAIL_SERVER is not configured.")
        if not app.config.get("MAIL_USERNAME"):
            raise RuntimeError("MAIL_USERNAME is not configured.")
        if not app.config.get("MAIL_PASSWORD"):
            raise RuntimeError("MAIL_PASSWORD is not configured.")
        if not recipient:
            raise RuntimeError("No recipient configured. Set SMTP_TEST_RECIPIENT or MAIL_DEFAULT_SENDER.")

        send_email_now(
            subject="SMTP Test Email",
            recipients=[recipient],
            body=(
                "This email was sent using the configured SMTP server.\n\n"
                "If you receive this, SMTP is working correctly."
            ),
        )
        print("SMTP email request completed successfully.")
        print(f"Delivery mode: {app.config.get('MAIL_DELIVERY_MODE')}")
        print(f"SMTP server: {app.config.get('MAIL_SERVER')}")
    except Exception as exc:
        print(f"Failed to send email: {exc}")
