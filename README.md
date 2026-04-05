# Permitrack Flask App

Permitrack is a Flask application for managing leave and on-duty requests across students, faculty, HODs, and administrators.

## Production readiness changes

- Production config now requires MySQL and shared object storage instead of local SQLite plus local disk
- CSRF protection is enabled for state-changing forms
- Logout is POST-only
- Login attempts are rate-limited per username and client IP
- Leave and OD review flows use version-tracked rows and transaction-safe updates
- Email notifications are queued in the database and processed by a separate worker command
- In-process scheduling was removed from the web app in favor of dedicated CLI jobs
- Health checks, Gunicorn config, Docker packaging, and cloud-ready env templates were added

## Local development

1. Create and activate a virtual environment.
2. Install dependencies:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Run migrations:

```powershell
.\venv\Scripts\python.exe -m flask --app wsgi db upgrade
```

4. Start the app:

```powershell
.\venv\Scripts\python.exe app.py
```

By default, local development still uses SQLite and local file storage.

## MySQL configuration

For production and AWS deployment, configure either `DATABASE_URL` or the `MYSQL_*` variables:

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`

The app automatically builds a `mysql+pymysql://...` SQLAlchemy URL when `MYSQL_DATABASE` is present.

## Shared storage

Production expects private object storage instead of local disk for shared deployments.

AWS S3:

- `STORAGE_BACKEND=s3`
- `STORAGE_BUCKET`
- `STORAGE_PREFIX`
- `STORAGE_PRESIGNED_URL_EXPIRY`
- `AWS_REGION`
- `AWS_S3_BUCKET`
- `AWS_S3_PREFIX`
- `AWS_PRESIGNED_URL_EXPIRY`

Oracle Cloud Infrastructure Object Storage via the S3-compatible API:

- `STORAGE_BACKEND=oci`
- `STORAGE_BUCKET`
- `STORAGE_PREFIX`
- `STORAGE_PRESIGNED_URL_EXPIRY`
- `OCI_OBJECT_STORAGE_REGION`
- `OCI_OBJECT_STORAGE_BUCKET`
- `OCI_OBJECT_STORAGE_PREFIX`
- `OCI_OBJECT_STORAGE_ENDPOINT`
- `OCI_S3_ACCESS_KEY`
- `OCI_S3_SECRET_KEY`
- `OCI_STORAGE_ADDRESSING_STYLE`

Development can keep using:

- `STORAGE_BACKEND=local`

## Email delivery

The web app now queues email notifications in the database. Run a worker command separately to send them:

```powershell
.\venv\Scripts\python.exe -m flask --app wsgi process-email-queue
```

Queue the daily reminder emails from a scheduler such as cron, EventBridge, or ECS Scheduled Tasks:

```powershell
.\venv\Scripts\python.exe -m flask --app wsgi queue-daily-summary
```

### SMTP Configuration

To enable email sending, create a `.env` file in the project root with the following variables:

- `MAIL_SERVER` (default: smtp.gmail.com)
- `MAIL_PORT` (default: 587)
- `MAIL_USE_TLS` (default: true)
- `MAIL_USE_SSL` (default: false)
- `MAIL_USERNAME` (required for sending emails)
- `MAIL_PASSWORD` (required for sending emails)
- `MAIL_DEFAULT_SENDER` (optional, defaults to MAIL_USERNAME)
- `MAIL_DELIVERY_MODE` (default: sync, options: queue/sync)

For Gmail, use an app password instead of your regular password. Create one at https://myaccount.google.com/apppasswords.

Example `.env` file:

```
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DELIVERY_MODE=sync
```

The app automatically loads environment variables from the `.env` file.

## Render Deployment

### Option 1: Using render.yaml (Recommended)

1. **Create `render.yaml`** in your project root (already included)
2. **Update the configuration** in `render.yaml`:
   - Replace `DATABASE_URL` with your actual database connection string
   - Replace `MAIL_USERNAME` and `MAIL_PASSWORD` with your email credentials
   - Update other settings as needed

3. **Deploy to Render**:
   - Connect your GitHub repository to Render
   - Render will automatically detect and use the `render.yaml` configuration

### Option 2: Manual Environment Variable Setup

If you prefer manual setup in Render dashboard:

1. **Go to your Render service dashboard**
2. **Navigate to Environment**
3. **Add the following environment variables**:

```
FLASK_ENV=production
APP_ENV=production
SECRET_KEY=your-strong-secret-key
LEAVE_SECRET=your-leave-secret
DATABASE_URL=mysql+pymysql://user:password@host:port/database
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DELIVERY_MODE=sync
STORAGE_BACKEND=local
INITDB_TOKEN=your-init-token
```

### Email Configuration for Render

**Important**: For emails to work on Render, you must configure:

- `MAIL_USERNAME`: Your Gmail address
- `MAIL_PASSWORD`: Your Gmail app password (not regular password)
- `MAIL_DELIVERY_MODE`: Set to `sync` for immediate sending

**Gmail Setup**:
1. Enable 2-factor authentication on your Gmail account
2. Generate an app password: https://myaccount.google.com/apppasswords
3. Use the app password as `MAIL_PASSWORD`

## Guarded sample data

Prefer the CLI command:

```powershell
$env:INIT_ADMIN_PASSWORD="change-this-admin-password"
.\venv\Scripts\python.exe -m flask --app wsgi init-sample-data
```

The legacy `/initdb` route still exists only when explicitly enabled with:

- `ENABLE_INITDB_ROUTE=true`
- optional `INITDB_TOKEN`

It now requires `POST`.

## Production deployment notes

- Set `APP_ENV=production`
- Set a strong `LEAVE_SECRET`
- Use MySQL on your managed database service
- Use private object storage for uploads
- Run Gunicorn behind an ALB or reverse proxy
- Enable `TRUST_PROXY=true`
- Run `process-email-queue` from a separate worker or scheduled task
- Run `queue-daily-summary` from a scheduler, not from the web process
- Apply database migrations before shifting traffic

## Container run

Build and start the app with Docker:

```powershell
docker compose up --build
```

For AWS, use `.env.production.example`. For Oracle Cloud, use `.env.oci.example`.
