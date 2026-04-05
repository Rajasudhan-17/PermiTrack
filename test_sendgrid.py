#!/usr/bin/env python3

from leave_app import create_app


app = create_app()


with app.app_context():
    from leave_app.services.emailing import send_email_now

    try:
        if not app.config.get("SENDGRID_API_KEY"):
            raise RuntimeError("SENDGRID_API_KEY is not configured.")
        recipient = app.config.get("SENDGRID_TEST_RECIPIENT") or app.config.get("MAIL_DEFAULT_SENDER")
        if not app.config.get("MAIL_DEFAULT_SENDER"):
            raise RuntimeError("MAIL_DEFAULT_SENDER is not configured.")
        if not recipient:
            raise RuntimeError("No recipient configured. Set SENDGRID_TEST_RECIPIENT or MAIL_DEFAULT_SENDER.")

        send_email_now(
            subject="SendGrid Test Email",
            recipients=[recipient],
            body=(
                "This email was sent using the SendGrid API.\n\n"
                "If you receive this, SendGrid is properly configured."
            ),
        )
        print("SendGrid email request completed successfully.")
        print(f"Delivery mode: {app.config.get('MAIL_DELIVERY_MODE')}")
        print(f"Data residency: {app.config.get('SENDGRID_DATA_RESIDENCY', 'global')}")
    except Exception as exc:
        print(f"Failed to send email: {exc}")
