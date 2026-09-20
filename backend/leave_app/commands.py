import click

from .extensions import db
from .services.emailing import process_email_queue
from .services.scheduler import queue_daily_summary_emails
from .services.seed import ensure_seed_data


def register_commands(app):
    @app.cli.command("process-email-queue")
    @click.option("--limit", default=None, type=int, help="Maximum queued emails to process in one run.")
    def process_email_queue_command(limit):
        """Send queued email notifications."""
        processed = process_email_queue(limit=limit)
        click.echo(f"Processed {processed} queued email(s).")

    @app.cli.command("queue-daily-summary")
    def queue_daily_summary_command():
        """Queue daily pending summary emails."""
        queue_daily_summary_emails()
        db.session.commit()
        click.echo("Queued daily summary emails.")

    @app.cli.command("init-sample-data")
    def init_sample_data_command():
        """Create guarded sample users and reference data."""
        message, status_code = ensure_seed_data()
        if status_code >= 400:
            raise click.ClickException(message)
        click.echo(message)
