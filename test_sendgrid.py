#!/usr/bin/env python3

from leave_app import create_app

app = create_app()

with app.app_context():
    from leave_app.services.emailing import send_email

    try:
        send_email(
            subject="SendGrid Test Email",
            recipients=["your-test-email@gmail.com"],
            body="This email was sent using SendGrid SMTP.\n\nIf you receive this, SendGrid is properly configured!"
        )
        print("✅ Email queued successfully with SendGrid!")
        print("Check your email inbox in a few seconds.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")