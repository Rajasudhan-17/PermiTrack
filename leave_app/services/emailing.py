import json
from datetime import timedelta

from flask import current_app
from flask_mail import Message

from ..extensions import db, mail
from ..models import EmailQueue, EmailStatus, utcnow


def serialize_recipients(recipients):
    return json.dumps(sorted(set(recipients)))


def deserialize_recipients(raw_value):
    return json.loads(raw_value)


def queue_email(subject, recipients, body):
    if not recipients:
        return

    username = current_app.config.get("MAIL_USERNAME")
    if not username:
        current_app.logger.info("Skipping email '%s' because mail is not configured.", subject)
        return

    db.session.add(
        EmailQueue(
            subject=subject,
            recipients=serialize_recipients(recipients),
            body=body,
            status=EmailStatus.QUEUED.value,
            available_at=utcnow(),
        )
    )


def send_email_now(subject, recipients, body):
    if not recipients:
        return

    username = current_app.config.get("MAIL_USERNAME")
    if not username:
        current_app.logger.info("Skipping email '%s' because mail is not configured.", subject)
        return

    msg = Message(subject=subject, sender=username, recipients=recipients, body=body)
    mail.send(msg)


def send_email(subject, recipients, body):
    mode = current_app.config.get("MAIL_DELIVERY_MODE", "queue")
    if mode == "sync":
        send_email_now(subject, recipients, body)
        return

    queue_email(subject, recipients, body)


def queued_email_batch(limit=None):
    batch_limit = limit or current_app.config.get("EMAIL_BATCH_SIZE", 50)
    now = utcnow()
    return (
        EmailQueue.query.filter(
            EmailQueue.status.in_([EmailStatus.QUEUED.value, EmailStatus.FAILED.value]),
            EmailQueue.available_at <= now,
        )
        .order_by(EmailQueue.available_at.asc(), EmailQueue.created_at.asc())
        .limit(batch_limit)
        .all()
    )


def process_email_queue(limit=None):
    processed = 0
    max_retries = current_app.config.get("EMAIL_MAX_RETRIES", 5)

    for queued_email in queued_email_batch(limit=limit):
        recipients = deserialize_recipients(queued_email.recipients)
        queued_email.status = EmailStatus.SENDING.value
        queued_email.attempts += 1
        db.session.commit()

        try:
            send_email_now(queued_email.subject, recipients, queued_email.body)
        except Exception as exc:
            current_app.logger.warning("Failed to send queued email '%s': %s", queued_email.subject, exc)
            queued_email.last_error = str(exc)
            queued_email.status = EmailStatus.FAILED.value
            if queued_email.attempts >= max_retries:
                queued_email.available_at = utcnow() + timedelta(hours=24)
            else:
                queued_email.available_at = utcnow() + timedelta(minutes=queued_email.attempts * 5)
            db.session.commit()
            continue

        queued_email.status = EmailStatus.SENT.value
        queued_email.sent_at = utcnow()
        queued_email.last_error = None
        db.session.commit()
        processed += 1

    return processed
