import json
from datetime import timedelta
from urllib import error as urllib_error
from urllib import request as urllib_request

from flask import current_app
from flask_mail import Message

from ..extensions import db, mail
from ..models import EmailQueue, EmailStatus, utcnow


def serialize_recipients(recipients):
    return json.dumps(sorted(set(recipients)))


def deserialize_recipients(raw_value):
    return json.loads(raw_value)


def mail_is_configured():
    backend = current_app.config.get("MAIL_BACKEND", "smtp")
    sender = current_app.config.get("MAIL_DEFAULT_SENDER")

    if backend == "brevo_api":
        return bool(current_app.config.get("BREVO_API_KEY") and sender)

    return bool(current_app.config.get("MAIL_USERNAME") and sender)


def queue_email(subject, recipients, body):
    if not recipients:
        return

    if not mail_is_configured():
        current_app.logger.info("Skipping email '%s' because mail is not configured.", subject)
        return

    queued_email = EmailQueue(
        subject=subject,
        recipients=serialize_recipients(recipients),
        body=body,
        status=EmailStatus.QUEUED.value,
        available_at=utcnow(),
    )
    db.session.add(queued_email)
    db.session.commit()
    return queued_email


def send_email_now(subject, recipients, body):
    if not recipients:
        return

    if not mail_is_configured():
        current_app.logger.info("Skipping email '%s' because mail is not configured.", subject)
        return

    if current_app.config.get("MAIL_BACKEND", "smtp") == "brevo_api":
        send_email_via_brevo_api(subject, recipients, body)
        return

    username = current_app.config.get("MAIL_USERNAME")
    sender = current_app.config.get("MAIL_DEFAULT_SENDER") or username

    msg = Message(subject=subject, sender=sender, recipients=recipients, body=body)
    mail.send(msg)


def send_email_via_brevo_api(subject, recipients, body):
    sender_email = current_app.config["MAIL_DEFAULT_SENDER"]
    sender_name = current_app.config.get("BREVO_SENDER_NAME") or sender_email
    payload = {
        "sender": {"email": sender_email, "name": sender_name},
        "to": [{"email": recipient} for recipient in recipients],
        "subject": subject,
        "textContent": body,
    }
    request_body = json.dumps(payload).encode("utf-8")
    request = urllib_request.Request(
        current_app.config["BREVO_API_URL"],
        data=request_body,
        headers={
            "accept": "application/json",
            "api-key": current_app.config["BREVO_API_KEY"],
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=15) as response:
            status_code = getattr(response, "status", response.getcode())
            if status_code >= 400:
                raise RuntimeError(f"Brevo API returned HTTP {status_code}.")
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Brevo API returned HTTP {exc.code}: {error_body}") from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(f"Brevo API request failed: {exc.reason}") from exc


def send_email(subject, recipients, body):
    mode = current_app.config.get("MAIL_DELIVERY_MODE", "queue")
    if mode == "sync":
        try:
            send_email_now(subject, recipients, body)
            return
        except Exception as exc:
            current_app.logger.warning(
                "Synchronous email send failed for '%s', falling back to queue: %s",
                subject,
                exc,
            )
            queue_email(subject, recipients, body)
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
