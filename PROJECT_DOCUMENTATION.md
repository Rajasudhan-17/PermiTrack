# Flask Leave & On-Duty Management System - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Database Models](#database-models)
5. [User Roles & Permissions](#user-roles--permissions)
6. [Features & Workflows](#features--workflows)
7. [API Routes & Endpoints](#api-routes--endpoints)
8. [Leave Management System](#leave-management-system)
9. [On-Duty (OD) Management System](#on-duty-od-management-system)
10. [Administration Features](#administration-features)
11. [Security Features](#security-features)
12. [File Upload System](#file-upload-system)
13. [Email System](#email-system)
14. [Database Configuration](#database-configuration)
15. [Installation & Setup](#installation--setup)
16. [User Workflows](#user-workflows)

---

## Project Overview

The **Flask Leave & On-Duty Management System** is a comprehensive institutional application designed for managing employee and student leave requests and on-duty (OD) requests in academic institutions. It streamlines the approval workflow from students/faculty to faculty advisors (HOD) with role-based access control.

### Key Purpose
- **Leave Management**: Handle leave requests with emergency fast-track approval
- **On-Duty Management**: Manage official duty requests requiring proof
- **Multi-level Approval**: Two-tier approval system (Faculty → HOD)
- **Admin Panel**: Complete institutional management (users, departments, classes)
- **Report Generation**: CSV and PDF reports for leave and OD history
- **Secure Authentication**: Rate-limited login with session management

### Target Users
- **Students**: Apply for leaves and OD requests
- **Faculty**: Review student leave/OD requests and approve/reject
- **HOD (Head of Department)**: Final approval of faculty-approved requests
- **Admin**: System administration and user/class management

---

## Architecture

### Application Structure
```
leave_flask_app/
├── app.py                          # Entry point
├── config.py                       # Configuration management
├── requirements.txt                # Dependencies
├── instance/                       # Instance-specific files (DB, uploads)
│   ├── app.db                     # SQLite database (development)
│   └── local_config.py            # Local configuration overrides
├── leave_app/
│   ├── __init__.py                # App factory and initialization
│   ├── auth.py                    # Authentication helpers
│   ├── commands.py                # CLI commands
│   ├── extensions.py              # Flask extensions (DB, Login, Mail, Migrate)
│   ├── models.py                  # Database models
│   ├── security.py                # Security configurations
│   ├── blueprints/
│   │   ├── auth.py                # Authentication routes
│   │   ├── leaves.py              # Leave management routes
│   │   ├── ods.py                 # On-Duty routes
│   │   ├── admin.py               # Admin routes
│   │   └── main.py                # Homepage and dashboard
│   ├── services/
│   │   ├── auth_security.py       # Login rate limiting
│   │   ├── emailing.py            # Email queue management
│   │   ├── reports.py             # Report generation (CSV/PDF)
│   │   ├── scheduler.py           # Background job scheduler
│   │   ├── seed.py                # Database seeding
│   │   ├── uploads.py             # File upload handling
│   │   ├── workflows.py           # Business logic workflows
│   │   └── admin.py               # Admin utilities (deprecated)
│   └── uploads/
│       ├── leave_proofs/          # Leave proof documents
│       └── od_proofs/             # OD proof documents
├── migrations/                    # Alembic database migrations
├── templates/                     # Jinja2 HTML templates
│   ├── layout.html                # Master template
│   ├── dashboard.html             # User dashboard
│   ├── apply.html                 # Leave application form
│   ├── apply_od.html              # OD application form
│   ├── my_leaves.html             # User's leave requests
│   ├── my_ods.html                # User's OD requests
│   ├── pending.html               # Faculty/HOD pending reviews
│   ├── review.html                # Leave review form
│   ├── review_od.html             # OD review form
│   ├── admin_*.html               # Admin templates
│   └── ...
└── static/                        # CSS, JavaScript files
    ├── style.css
    └── admin_create_user.js
```

### Architectural Pattern
- **MVC Architecture**: Models (SQLAlchemy ORM), Views (Jinja2 Templates), Controllers (Blueprints)
- **Factory Pattern**: App factory (`create_app()`) for testing and multiple configurations
- **Blueprint Separation**: Modular route organization
- **Service Layer**: Business logic separated from views

---

## Technology Stack

### Backend Framework
- **Flask 3.1.2**: Core web framework
- **Flask-SQLAlchemy 3.1.1**: ORM for database operations
- **Flask-Login 0.6.3**: User session management
- **Flask-Mail 0.10.0**: Email sending
- **Flask-Migrate 4.1.0**: Database migrations

### Database
- **SQLAlchemy 2.0.44**: ORM
- **Alembic 1.17.0**: Database migration tool
- **SQLite** (Development): Default database
- **MySQL** (Production): Supported via PyMySQL

### Security & Authentication
- **Werkzeug 3.1.3**: Password hashing utilities
- **python-dotenv 1.0.1**: Environment configuration

### Additional Libraries
- **PyMySQL 1.1.2**: MySQL driver
- **APScheduler** (inferred): Background task scheduling
- **WeasyPrint** (inferred): PDF generation
- **reportlab** (inferred): Report generation

---

## Database Models

### 1. **Role** (Enum)
Defines user types in the system:
```python
- STUDENT: "student"      # Can apply for leave/OD
- FACULTY: "faculty"      # Can review student requests
- HOD: "hod"             # Head of Department - final approval
- ADMIN: "admin"         # System administration
```

### 2. **RequestStatus** (Enum)
Tracks approval workflow:
```python
- PENDING: "PENDING"                    # Initial state
- FACULTY_APPROVED: "FACULTY_APPROVED"  # Faculty approved, awaiting HOD
- APPROVED: "APPROVED"                  # Final approval
- REJECTED: "REJECTED"                  # Rejected by faculty or HOD
```

### 3. **Department** Model
Represents academic departments:
```
Columns:
- id (Integer, PK)
- name (String[100], UNIQUE, NOT NULL)
- hod_id (Integer, FK → User.id, nullable)

Relationships:
- hod: User relationship (one-to-one)
- classes: List of ClassGroup objects (one-to-many)

Constraints:
- Department name must not be blank
```

### 4. **ClassGroup** Model
Represents academic classes/sections:
```
Columns:
- id (Integer, PK)
- year (Integer, NOT NULL) - Academic year (1, 2, 3, 4)
- section (String[10], NOT NULL) - Section identifier (A, B, C)
- department_id (Integer, FK → Department.id, NOT NULL)
- faculty_id (Integer, FK → User.id, nullable)

Relationships:
- department: Department object (many-to-one)
- faculty: Assigned faculty member (one-to-one)
- students: List of Student users (one-to-many)

Constraints:
- Unique: (department_id, year, section)
- year >= 1
- section must not be blank
- Indexed on faculty_id
```

### 5. **User** Model
Core user entity:
```
Columns:
- id (Integer, PK)
- username (String[80], UNIQUE, NOT NULL)
- email (String[120], UNIQUE, NOT NULL)
- password_hash (String[255], NOT NULL)
- full_name (String[150], nullable)
- role (String[20], DEFAULT='student') - One of Role enum values
- leave_balance (Integer, DEFAULT=20, >= 0) - Days of leave available
- faculty_id (Integer, FK → User.id, nullable) - Assigned faculty advisor
- department_id (Integer, FK → Department.id, nullable)
- class_group_id (Integer, FK → ClassGroup.id, nullable)
- version_id (Integer, DEFAULT=1) - Optimistic locking column

Relationships:
- faculty: Reference to assigned faculty advisor (remote_side self-join)
- students: List of students under this faculty member
- department: Department assignment
- class_group: Class assignment
- requested_leaves: Leaves submitted by this user (one-to-many)
- approved_leaves: Leaves approved by this user (one-to-many)

Constraints:
- role must be in valid Role values
- leave_balance >= 0
- Optimistic locking enabled via version_id
- Indexes on: role, (department_id, role), class_group_id, faculty_id

Methods:
- set_password(password): Hash and store password
- check_password(password): Verify password match
- is_authenticated: From UserMixin (Flask-Login)
```

### 6. **Leave** Model
Student/Faculty leave requests:
```
Columns:
- id (Integer, PK)
- requested_by (Integer, FK → User.id, NOT NULL)
- approved_by (Integer, FK → User.id, nullable)
- start_date (Date, NOT NULL)
- end_date (Date, NOT NULL)
- reason (Text, NOT NULL)
- is_emergency (Boolean, DEFAULT=False)
- proof_filename (String[300], nullable)
- proof_mimetype (String[120], nullable)
- proof_uploaded_on (DateTime, nullable)
- status (String[30], DEFAULT='PENDING')
- applied_on (DateTime, DEFAULT=utcnow)
- review_comment (Text, nullable)
- reviewed_on (DateTime, nullable)
- version_id (Integer, DEFAULT=1) - Optimistic locking

Relationships:
- requester: User who submitted the request (many-to-one)
- approver: User who approved (many-to-one)

Constraints:
- end_date >= start_date
- status must be valid RequestStatus
- Optimistic locking enabled
- Indexes on: (requested_by, status), (status, applied_on), (start_date, end_date), approved_by

Properties:
- applicant: Alias for requester
- requires_followup_proof: True if emergency leave without proof uploaded
```

### 7. **OD** (On-Duty) Model
On-duty request for students:
```
Columns:
- id (Integer, PK)
- requested_by (Integer, FK → User.id, NOT NULL)
- approved_by (Integer, FK → User.id, nullable)
- event_date (Date, NOT NULL) - Date of the on-duty event
- reason (Text, NOT NULL)
- proof_filename (String[300], nullable)
- proof_mimetype (String[120], nullable)
- status (String[20], DEFAULT='PENDING')
- faculty_id (Integer, FK → User.id, nullable) - Assigned reviewer
- applied_on (DateTime, DEFAULT=utcnow)
- review_comment (Text, nullable)
- reviewed_on (DateTime, nullable)
- version_id (Integer, DEFAULT=1) - Optimistic locking

Relationships:
- requester: User who submitted (many-to-one)
- approver: User who approved (many-to-one)
- faculty: Assigned faculty reviewer (many-to-one)

Constraints:
- status must be valid RequestStatus
- Optimistic locking enabled
- Indexes on: (requested_by, status), (faculty_id, status), (status, applied_on), event_date
```

### 8. **EmailQueue** Model
Asynchronous email queue:
```
Columns:
- id (Integer, PK)
- subject (String[255], NOT NULL)
- recipients (Text, NOT NULL) - Comma-separated emails
- body (Text, NOT NULL)
- status (String[20], DEFAULT='QUEUED') - One of EmailStatus enum
- attempts (Integer, DEFAULT=0) - Number of send attempts
- last_error (Text, nullable)
- available_at (DateTime, DEFAULT=utcnow)
- created_at (DateTime, DEFAULT=utcnow)
- sent_at (DateTime, nullable)

Constraints:
- status must be valid EmailStatus
- Indexes on: (status, available_at), created_at

Status Flow:
QUEUED → SENDING → SENT (success) or FAILED
```

### 9. **LoginAttempt** Model
Rate limiting for login security:
```
Columns:
- key (String[255], PK) - Unique identifier (username:ip_address)
- username (String[80], NOT NULL)
- ip_address (String[64], NOT NULL)
- attempt_count (Integer, DEFAULT=0)
- window_started_at (DateTime, DEFAULT=utcnow)
- last_attempt_at (DateTime, DEFAULT=utcnow)
- locked_until (DateTime, nullable) - Lockout expiry time

Constraints:
- Indexes on: locked_until, last_attempt_at

Purpose:
- Track failed login attempts
- Implement exponential backoff lockout
```

---

## User Roles & Permissions

### Role Hierarchy
```
ADMIN (System Administrator)
  ├── Full system access
  ├── Create departments, classes, and users
  ├── Modify leave balances
  ├── Generate reports
  └── Delete requests and users

STUDENT (Default User)
  ├── Apply for leave (up to balance limit)
  ├── Submit emergency leave (fast-track)
  ├── Apply for on-duty requests
  ├── Upload proof for emergency leaves
  ├── Upload proof for OD requests
  ├── View own requests and status
  └── Upload leave proof
  
FACULTY (Instructor/Class Advisor)
  ├── All STUDENT permissions
  ├── Review pending leave requests for assigned class
  ├── Review pending OD requests
  ├── Approve or reject student requests with comments
  ├── View class-specific leave/OD requests
  └── Be assigned as HOD (optional)
  
HOD (Head of Department)
  ├── All FACULTY permissions
  ├── Review faculty-approved leaves for their department
  ├── Final approval/rejection of leave requests
  ├── View department-wide statistics
  └── Oversee all department leave management
```

### Permission Matrix

| Action | Student | Faculty | Mentor | Event Coordinator | HOD | Admin |
|--------|---------|---------|--------|-------------------|-----|-------|
| Apply Leave | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ |
| Apply OD | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Review Pending Leaves | ✗ | ✓ (assigned class) | ✓ (mentored) | ✗ | ✓ (dept) | ✓ |
| Review Pending ODs | ✗ | ✓ (assigned) | ✓ (mentored) | ✓ (assigned event) | ✓ (dept) | ✓ |
| Upload Leave Proof | ✓ (own emergency) | ✓ (own emergency) | ✓ (own emergency) | ✗ | ✓ (own emergency) | ✗ |
| Create Department | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Create Class | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Assign Faculty | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Assign Mentor | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| Create Users | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| View Reports | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Delete Requests | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Reset Balances | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |

---

## Features & Workflows

### 1. Leave Management System

#### Leave Types
- **Regular Leave**: Standard leave with pre-approval requirement
- **Emergency Leave**: Fast-track leave with post-proof requirement

#### Leave Workflow
```
Student Applies for Leave
        ↓
[Dates Valid? Reason Given?]
        ↓ Yes
[Leave Balance Sufficient?]
        ↓ Yes
Request Stored as PENDING → Faculty Email Notification
        ↓
Faculty Reviews Request (checks for conflicts)
        ↓
[Approve or Reject?]
        ↓ Approve
Status → FACULTY_APPROVED → HOD Email Notification
        ↓ Reject
Status → REJECTED → Student Email Notification
        ↓
HOD Reviews FACULTY_APPROVED Requests
        ↓
[Approve or Reject?]
        ↓ Approve
Status → APPROVED
Leave Balance Deducted → Student Notification Email
        ↓ Reject
Status → REJECTED → Student Notification Email
```

#### Emergency Leave Workflow
```
Student Applies Emergency Leave
        ↓
Request Stored as PENDING (Fast-Track)
        ↓
Student Notified to Upload Proof (24-hour window recommended)
        ↓
Faculty Reviews & Can Approve Without Proof
        ↓
If Approved: Status → FACULTY_APPROVED → HOD Review
        ↓
HOD Final Approval: Status → APPROVED
        ↓
Leave Balance Deducted (even without proof)
Note: System tracks proof requirement via requires_followup_proof property
```

#### Leave Conflict Detection
- Prevents same-day approval for multiple students in same class
- Detects and alerts faculty when reviewing overlapping leaves
- Ensures consistent attendance records

---

### 2. On-Duty (OD) Management System

#### Purpose
- Track official duty activities (seminars, workshops, sports events, etc.)
- Require proof of attendance
- No impact on leave balance
- Different approval chain than leaves

#### OD Workflow
```
Student Applies for OD
  ├─ Select Event Date
  ├─ Provide Reason
  ├─ Upload Proof (Optional but recommended)
        ↓
Stored as PENDING → Faculty Email
        ↓
Faculty Reviews Proof & Details
        ↓
[Approve or Reject?]
        ↓ Approve
Status → FACULTY_APPROVED → HOD Email
        ↓ Reject
Status → REJECTED → Student Email
        ↓
HOD Reviews FACULTY_APPROVED ODs
        ↓
[Final Decision?]
        ↓ Approve
Status → APPROVED → Student Email
        ↓ Reject
Status → REJECTED → Student Email
```

#### Key Differences from Leave
- Does NOT affect leave balance
- Proof uploaded during application (not post-hoc)
- Tracks official event attendance
- No date range (single day event)

---

### 3. Administrative Features

#### Department Management
- Create and manage academic departments
- Assign HOD to each department
- Organize users and classes by department

#### Class Management
- Create academic classes with Year and Section
- Assign faculty to classes
- Link classes to departments
- Manage class-wise organization

#### User Management
- Create/edit users with role assignment
- Assign students to classes
- Assign faculty to departments and classes
- Manage user profiles and leave balances
- Reset leave balances (annual cycle)

#### Reporting
- **Leave Report**: Export leave requests (CSV/PDF)
  - Filter by date, user, status
  - Includes approval timeline and comments
- **OD Report**: Export OD requests (CSV/PDF)
  - Track event attendance
  - Generate event statistics
- **Statistics Dashboard**: Real-time metrics
  - Total users, departments, classes
  - Total leave and OD requests
  - Approval statistics

#### Data Management
- Delete leave/OD requests (with balance restoration for approved leaves)
- Delete user records with cascading cleanup
- Bulk data operations via admin panel

---

## API Routes & Endpoints

### Main Blueprint (`/`)

| Route | Method | Description | Auth |
|-------|--------|-------------|------|
| `/` | GET | Homepage/Dashboard | Optional |
| `/healthz` | GET | Health check | None |

### Authentication Blueprint (`/auth`)

| Route | Method | Description | Auth |
|-------|--------|-------------|------|
| `/login` | GET, POST | User login | None |
| `/logout` | POST | User logout | Required |

### Leave Management Blueprint (`/leaves`)

| Route | Method | Description | Auth | Role |
|-------|--------|-------------|------|------|
| `/apply` | GET, POST | Apply for leave | Required | Student, Faculty |
| `/my_leaves` | GET | View own leave requests | Required | Any |
| `/pending` | GET | View pending reviews | Required | Faculty, HOD |
| `/review/<id>` | GET, POST | Review leave request | Required | Faculty, HOD |
| `/leave/<id>/upload_proof` | GET, POST | Upload emergency leave proof | Required | Requester |
| `/leave_proof/<id>` | GET | Download leave proof | Required | Authorized |
| `/leave/<id>/download_letter` | GET | Download leave approval letter (PDF) | Required | Authorized |

### On-Duty Blueprint (`/ods`)

| Route | Method | Description | Auth | Role |
|-------|--------|-------------|------|------|
| `/apply_od` | GET, POST | Apply for OD | Required | Student |
| `/my_ods` | GET | View own OD requests | Required | Any |
| `/pending_od` | GET | View pending OD reviews | Required | Faculty, HOD |
| `/review_od/<id>` | GET, POST | Review OD request | Required | Faculty, HOD |
| `/od_proof/<id>` | GET | Download OD proof | Required | Authorized |
| `/od/<id>/download_letter` | GET | Download OD approval letter (PDF) | Required | Authorized |

### Admin Blueprint (`/admin`)

| Route | Method | Description | Auth | Role |
|-------|--------|-------------|------|------|
| `/admin/create_department` | GET, POST | Create department | Required | Admin |
| `/admin/create_class` | GET, POST | Create class | Required | Admin |
| `/admin/create_user` | GET, POST | Create user | Required | Admin |
| `/admin/assign_faculty` | GET, POST | Assign faculty to class | Required | Admin |
| `/admin/assign_hod` | GET, POST | Assign HOD to department | Required | Admin |
| `/admin/admin_all_leaves` | GET | View all leaves | Required | Admin |
| `/admin/admin_all_ods` | GET | View all ODs | Required | Admin |
| `/admin/reports` | GET | Generate reports | Required | Admin |
| `/admin/initdb` | POST | Initialize database | Required | Admin |

---

## Leave Management System

### Core Features

#### 1. Leave Application
**Endpoint**: `POST /apply`
```
Input:
- start_date: Date (YYYY-MM-DD format)
- end_date: Date (YYYY-MM-DD format)
- reason: Text (required, reason for leave)
- is_emergency: Checkbox (fast-track leave if checked)

Validation:
- End date >= start date
- Dates are valid and in correct format
- Reason is provided and not empty
- User is student or faculty
- Leave balance sufficient (for non-emergency)

Processing:
1. Calculate leave days: (end_date - start_date) + 1
2. Check balance (unless emergency)
3. Create Leave record with PENDING status
4. Send email to assigned faculty advisor
5. Return success and redirect to /my_leaves

Emergency Leave Special Handling:
- No balance check at submission
- Status set to PENDING (fast-track mode)
- Balance deducted upon FINAL APPROVAL
- System flags as requires_followup_proof
- User reminded to upload proof within 24 hours
```

#### 2. Leave Review (Faculty Level)
**Endpoint**: `POST /review/<leave_id>`
```
Input:
- action: "APPROVE" or "REJECT"
- comment: Optional review comment

Faculty Responsibility:
- Check for attendance conflicts
- Verify dates don't overlap with other approved leaves in same class
- Validate leave reason adequacy
- Ensure balance sufficiency

Processing if APPROVE:
1. Update leave status to FACULTY_APPROVED
2. Add faculty comment and timestamp
3. Send notification to HOD
4. Await HOD final review

Processing if REJECT:
1. Update status to REJECTED
2. Add rejection reason in comment
3. Send rejection email to student
4. Don't deduct balance (still pending)
5. Student may reapply

Conflict Detection:
- Alerts faculty of overlapping leaves in same class
- Prevents approval of conflicting requests
- Highlights emergency leaves in review list
```

#### 3. Leave Review (HOD Level)
**Endpoint**: `POST /review/<leave_id>` (same endpoint, different permissions)
```
Processing if APPROVE:
1. Update status to APPROVED
2. Calculate deduction: (end_date - start_date) + 1 days
3. Deduct from student leave_balance
4. Record approval timestamp
5. Trigger email notification to student
6. Update review_comment and reviewed_on

Processing if REJECT:
1. Update status to REJECTED
2. Send rejection email with HOD comment
3. No balance change
4. Student may reapply after addressing concerns
```

#### 4. Leave Proof Upload (Emergency Leaves)
**Endpoint**: `POST /leave/<leave_id>/upload_proof`
```
Purpose: Upload supporting documentation for emergency leaves

Validation:
- Leave is emergency leave
- File size acceptable (checked in validate_uploaded_document)
- File type valid (PDF, Word, Images)
- User is the requester

Processing:
1. Validate uploaded file
2. Generate unique filename
3. Store in LEAVE_UPLOAD_PREFIX directory
4. Update leave.proof_filename and proof_mimetype
5. Set proof_uploaded_on timestamp
6. Commit to database

Note: Can be uploaded before or after approval
```

#### 5. Leave Proof Download
**Endpoint**: `GET /leave_proof/<leave_id>`
```
Access Control:
- Requester can always access their own proof
- Faculty can access for pending/their-class leaves
- HOD can access for faculty-approved/their-dept leaves
- Admin can access any proof

Returns:
- File download with correct MIME type
- Proper error handling for missing files
```

#### 6. View My Leaves
**Endpoint**: `GET /my_leaves`
```
Display:
- All leaves submitted by current user
- Sorted by applied_on (DESC)
- Shows status, dates, reason, comments
- Links to upload proof for emergency leaves
- Links to download uploaded proofs

Template: my_leaves.html
```

#### 7. Pending Leaves for Review
**Endpoint**: `GET /pending`
```
Faculty View (for assigned class):
- Displays all PENDING leaves for their class
- Sorted by is_emergency (DESC), then applied_on (ASC)
- Shows conflict warnings
- Highlights emergency requests
- Links to review each request

HOD View (for department):
- Displays FACULTY_APPROVED leaves from their department
- Ready for final approval/rejection
- Shows faculty's initial comment
- Awaiting HOD decision
```

#### 8. Leave Approval Letter Download
**Endpoint**: `GET /leave/<leave_id>/download_letter`
```
Access Control:
- Requester can download their own approved letter
- Mentor can download for their mentored students
- Faculty can download for students in their assigned class
- HOD can download for students in their department
- Admin can download any approved letter

Returns:
- Dynamically generated PDF containing the official leave approval status and remarks
```

---

## On-Duty (OD) Management System

### Core Features

#### 1. OD Application
**Endpoint**: `POST /apply_od`
```
Input:
- event_date: Date (YYYY-MM-DD)
- reason: Text (event/activity reason)
- proof: File upload (optional but recommended)

Validation:
- Event date is valid
- Reason provided and not empty
- Assigned faculty exists
- Proof file format valid (if provided)

Processing:
1. Validate and save uploaded proof file (if provided)
2. Generate unique filename for proof
3. Store proof in OD_UPLOAD_PREFIX directory
4. Create OD record with PENDING status
5. Set faculty_id to student's assigned faculty
6. Send email notification to faculty
7. Redirect to /my_ods

Faculty Assignment:
- Determined by ClassGroup.faculty_id if student has class assignment
- Falls back to User.faculty_id if direct assignment
- Error if no faculty assigned
```

#### 2. OD Review (Faculty Level)
**Endpoint**: `POST /review_od/<od_id>`
```
Input:
- action: "APPROVE" or "REJECT"
- comment: Optional review comment

Processing if APPROVE:
1. Update status to FACULTY_APPROVED
2. Add faculty comment
3. Send notification to HOD
4. OD awaits HOD final review

Processing if REJECT:
1. Update status to REJECTED
2. Send rejection email with comment
3. Student may reapply

Reviewer Verification:
- Faculty can only review ODs assigned to them
- Status must be PENDING for faculty review
```

#### 3. OD Review (HOD Level)
**Endpoint**: `POST /review_od/<od_id>` (same endpoint)
```
Processing if APPROVE:
1. Update status to APPROVED
2. Record HOD approval timestamp
3. Send approval email to student
4. OD marked as completed

Processing if REJECT:
1. Update status to REJECTED
2. Send rejection email with HOD reasoning
```

#### 4. OD Proof Download
**Endpoint**: `GET /od_proof/<od_id>`
```
Access Control:
- Requester can always download
- Event Coordinator can download for assigned ODs
- Mentor can download for mentored students
- Faculty can download for assigned ODs
- HOD can download for department ODs
- Admin can download any

Returns: File with appropriate MIME type
```

#### 5. View My ODs
**Endpoint**: `GET /my_ods`
```
Display:
- All OD requests submitted by user
- Sorted by applied_on (DESC)
- Shows event_date, reason, status, comments
- Links to download proof
```

#### 6. Pending ODs for Review
**Endpoint**: `GET /pending_od`
```
Faculty View:
- Displays PENDING ODs assigned to them
- Sorted by applied_on (ASC)
- Shows student, event date, reason, proof

HOD View:
- Displays FACULTY_APPROVED ODs from department
- Ready for final decision
- Shows faculty's initial comment
```

#### 7. OD Approval Letter Download
**Endpoint**: `GET /od/<od_id>/download_letter`
```
Access Control:
- Requester can download their own approved letter
- Event Coordinator can download for assigned ODs
- Mentor can download for mentored students
- Faculty can download for assigned ODs
- HOD can download for department ODs
- Admin can download any approved letter

Returns:
- Dynamically generated PDF containing the official OD approval status and event details
```

---

## Decision-Support: Leave & OD Risk Scoring Engine

The application includes an automated decision-support heuristic engine that evaluates each leave or OD request and assigns a risk score and level before a reviewer opens it. This transforms the application from a simple application form into an active decision-making assistant.

### Risk Metrics

#### 1. Leave Risk Heuristics
Risk scores range from `0` to `100` and are categorized into levels: **High Risk** (>= 50), **Medium Risk** (20-49), and **Low Risk** (< 20).
The scoring is computed using the following factors:
- **Leave Balance Check**:
  - Balance < 3 days: **+40 points**
  - Balance < 8 days: **+20 points**
- **Emergency Leave Frequency**:
  - >= 3 emergency leaves in past 30 days: **+35 points**
  - 2 emergency leaves in past 30 days: **+15 points**
- **Cumulative Absence Risk (Attendance Drop Risk)**:
  - Tracks total missed class days (approved leaves + approved ODs + current requested days) in the past 90 days:
    - > 15 days (High risk of drop below 80% attendance): **+30 points**
    - > 8 days (Medium risk of drop below 90% attendance): **+15 points**
- **Long Request Duration**:
  - Single request length > 5 days: **+15 points**

#### 2. OD Risk Heuristics
- **Cumulative Absence Check**:
  - > 15 total absence days in past 90 days: **+30 points**
  - > 8 total absence days in past 90 days: **+15 points**
- **Monthly OD Request Frequency**:
  - >= 5 OD requests submitted in past 30 days: **+40 points**
  - >= 3 OD requests submitted in past 30 days: **+20 points**

### Interface Integration
- **Pending Review Lists**: Displays a colored badge (**High** / **Medium** / **Low**) beside each request, showing the numeric score and displaying details on hover.
- **Review Form Detail Page**: Renders an alert card outlining the specific factors that contributed to the risk score, giving faculty and HODs context for their decisions.

---

## Administration Features

### User Management

#### Create User
**Endpoint**: `POST /admin/create_user`
```
Input:
- username: Unique identifier
- email: Valid email address
- password: Account password
- full_name: Display name
- role: Role selection (student/faculty/hod/admin)
- For STUDENT: Department, Year, Section
- For FACULTY: Department, optional Class assignment
- For HOD: Department assignment

Processing:
1. Validate uniqueness of username and email
2. Hash password with Werkzeug security
3. Create User record
4. If student: link to ClassGroup
5. If faculty/hod: assign to department
6. Redirect with success message
```

#### Edit User
**Endpoint**: `POST /admin/edit_user/<user_id>`
```
Modifications:
- Update full_name
- Change role
- Update department/class assignments
- Modify leave_balance

Cannot modify:
- Username (unique identifier)
- Email (unique identifier) - might support in future
- Password (separate endpoint)
```

#### Assign Faculty to Class
**Endpoint**: `POST /admin/assign_faculty`
```
Process:
1. Select target class (Department, Year, Section)
2. Select faculty to assign
3. Update ClassGroup.faculty_id
4. Faculty now can review that class's leaves and ODs
```

#### Assign HOD to Department
**Endpoint**: `POST /admin/assign_hod`
```
Process:
1. Select target department
2. Select faculty to assign as HOD
3. Update Department.hod_id and User.role
4. HOD gains approval authority for department
```

#### Delete User
**Process**:
1. Find all leaves where user is requester or approver
2. Find all ODs where user is requester, approver, or assigned faculty
3. Delete associated records
4. Delete user record
5. Deduct leave balance from deleted approved requests

---

### Department & Class Management

#### Create Department
**Endpoint**: `POST /admin/create_department`
```
Input:
- name: Department name (unique)

Processing:
1. Validate name is not blank
2. Check uniqueness (case-insensitive)
3. Create Department record
4. Redirect with confirmation
```

#### Create Class
**Endpoint**: `POST /admin/create_class`
```
Input:
- department_id: Parent department
- year: Academic year (1-4)
- section: Section code (A, B, C, etc.)

Validation:
- All fields required
- Unique combination of (department_id, year, section)
- Year >= 1

Processing:
1. Create ClassGroup record
2. No faculty assigned initially
3. Faculty assigned later via assign_faculty endpoint
```

---

### Reporting & Analytics

#### Leave Report
**Endpoint**: `GET /admin/reports?type=leave`
```
Filters:
- Date range (from_date, to_date)
- Specific user/student
- Leave status
- Department

Output:
- CSV or PDF format
- Columns: Student, Leave Dates, Reason, Duration (days),
           Faculty Approval Date, HOD Approval Date, Status
- Summary statistics: Total leaves, approved %, rejected %
```

#### OD Report
**Endpoint**: `GET /admin/reports?type=od`
```
Filters:
- Date range
- Specific user
- Event type/reason
- Department

Output:
- CSV or PDF format
- Columns: Student, Event Date, Reason, Proof Status,
           Faculty Approval Date, HOD Approval Date, Status
- Statistics: Total ODs, approval rate
```

#### Dashboard Metrics
- Total users by role
- Total departments
- Total classes
- Total leave and OD requests
- Approval rate statistics

---

### Data Initialization

#### Database Initialization
**Endpoint**: `POST /admin/initdb`
```
Purpose: Initialize database with seed data

Process:
1. Create all tables (via Flask-Migrate)
2. Seed default admin user
3. Create sample departments
4. Create sample classes
5. Create sample users for testing

Seed Data Provided:
- Admin user (username: admin, password: admin)
- 2-3 departments (Engineering, Science, Arts)
- Multiple classes per department
- Sample students and faculty
```

---

## Security Features

### 1. Authentication
- **Session Management**: Flask-Login with secure cookies
- **Password Hashing**: Werkzeug generate_password_hash
- **Password Verification**: Werkzeug check_password_hash
- **Login Rate Limiting**: LoginAttempt model tracks failed attempts
- **OTP Verification Rate Limiting**: Prevents brute-forcing password reset OTPs

### 2. Login Rate Limiting
**Implementation**: `services/auth_security.py`
```python
# Configuration
- Max attempts: 5 failures
- Time window: 15 minutes
- Lockout duration: 30 minutes (exponential backoff)
- Tracking by: username + IP address

Process:
1. Check if account locked (locked_until > now)
2. If locked, deny access and display lockout time
3. If not locked but failed, increment attempt_count
4. If attempts >= threshold, set locked_until = now + lockout_duration
5. On successful login, clear attempt record
```

### 2b. Password Reset OTP Rate Limiting
**Implementation**: `services/auth_security.py`
```python
# Configuration
- Max attempts: 5 failures
- Time window: 15 minutes
- Lockout duration: 15 minutes
- Tracking by: email + IP address (using key `otp|<email>|<ip_address>` in `LoginAttempt` model)

Process:
1. Check if OTP verification is allowed (locked_until > now)
2. If locked, deny access and display lockout duration
3. If verification fails (invalid/expired OTP), register failure
4. If attempts >= threshold, set locked_until = now + lockout_duration
5. On successful password reset, clear attempt record
```

### 3. Authorization (Role-Based Access Control)
- **Route Decorators**: `@admin_required`, `@login_required`
- **Endpoint Validation**: Check user role and permissions
- **Object-Level Authorization**: 
  - Can only review own class's leaves
  - Can only upload proof for own requests
  - HOD can only approve from own department
  - Event Coordinators can access and review OD requests assigned to them
  - Mentors can access and review OD/leave requests from their mentored students

### 4. Data Protection
- **Optimistic Locking**: All request models use version_id
  - Prevents concurrent modification conflicts
  - Incremented on each update
  - Raises StaleDataError if version mismatch
- **Password Hashing**: Industry-standard Werkzeug hashing
- **Email Validation**: Valid email format requirement

### 5. CSRF Protection
- **Configuration**: Flask-WTF CSRF enabled (configurable)
- **Token Validation**: On all POST/PUT/DELETE requests
- **Testing Mode**: CSRF can be disabled for tests

### 6. Session Security
- **Secure Cookies**: HTTPS-only in production
- **Session Timeout**: Configurable timeout period
- **Remember Me**: Optional persistent login

### 7. File Upload Security
**File Upload Handling**:
- **Filename Sanitization**: Prevents directory traversal
- **File Type Validation**: Whitelist of allowed MIME types
- **File Size Limits**: Configurable upload limits
- **Storage**: Uploads stored outside web root
- **Access Control**: Proof files only accessible to authorized users

---

## File Upload System

### Upload Configuration

#### Leave Proof Upload
```python
Prefix: LEAVE_UPLOAD_PREFIX (config setting)
Directory: uploads/leave_proofs/
Allowed Types: PDF, Word, Images
Max Size: Configurable (default 10MB)

Storage Location:
- Instance folder for local environment
- S3 or external storage for production
```

#### OD Proof Upload
```python
Prefix: OD_UPLOAD_PREFIX (config setting)
Directory: uploads/od_proofs/
Allowed Types: PDF, Word, Images, Videos
Max Size: Configurable

Storage Location:
- Instance folder for local environment
- S3 or external storage for production
```

### Upload Services
**Module**: `services/uploads.py`

```python
Functions:
- validate_uploaded_document(file): Verify file for leave proof
- validate_uploaded_proof(file): Verify file for OD proof
- save_uploaded_file(file, prefix, filename, mimetype): Store file
- uploaded_file_exists(prefix, filename): Check file existence
- build_file_response(prefix, filename, mimetype): Serve file download
- delete_uploaded_file(prefix, filename): Remove file (on admin delete)
```

### Security Measures
1. **Filename Generation**: UUID-based random filenames to prevent collisions
2. **MIME Type Validation**: Check both extension and content type
3. **Access Control**: Files only served to authorized users
4. **Deletion**: Files removed when associated request is deleted
5. **Storage Isolation**: Separate directories for leave and OD proofs

---

## Email System

### Email Queue

#### Purpose
- Asynchronous email sending (non-blocking)
- Retry mechanism for failed sends
- Email delivery tracking
- Support for multiple backends (SMTP, Brevo API)

#### Email Queue Model
```python
Columns:
- id: Unique email identifier
- subject: Email subject line
- recipients: Comma-separated email addresses
- body: Email body text
- status: QUEUED → SENDING → SENT or FAILED
- attempts: Number of send attempts (max 3)
- last_error: Error message if failed
- available_at: When email is available to send
- created_at: When email was queued
- sent_at: When successfully sent
```

#### Status Flow
```
1. Email Creation: Status = QUEUED
2. Scheduler picks up: Status = SENDING
3. Success: Status = SENT, sent_at = timestamp
4. Failure: Status = FAILED, last_error = error message
5. Retry: If attempts < 3, requeue with exponential backoff
```

### Email Triggers

#### Automatic Emails
1. **Leave Application**: Faculty notified of pending leave
2. **Leave Approved by Faculty**: HOD notified
3. **Leave Approval**: Student notified of final approval
4. **Leave Rejection**: Student notified of rejection
5. **OD Application**: Faculty notified of OD request
6. **OD Approval**: Student notified of approval
7. **OD Rejection**: Student notified of rejection

#### Email Configuration
```python
# SMTP Backend (default)
MAIL_SERVER: SMTP server address
MAIL_PORT: SMTP port (587 for TLS)
MAIL_USE_TLS: True/False
MAIL_USERNAME: Sender email
MAIL_PASSWORD: Email password

# Brevo API Backend (alternative)
BREVO_API_KEY: Brevo API key
BREVO_SENDER_EMAIL: From email address
```

### Email Scheduler
**Service**: `services/scheduler.py`
```
Process:
1. Runs periodically (every 60 seconds by default)
2. Finds QUEUED emails in EmailQueue
3. Attempts to send via configured backend
4. Updates status to SENT or FAILED
5. Retries failed emails with exponential backoff
6. Logs all email activities

Configuration:
- Scheduler enabled/disabled via config
- Retry interval configurable
- Max attempts: 3
```

---

## Database Configuration

### Environment Variables

#### Database Connection
```
# SQLite (Development)
DATABASE_URL=sqlite:////path/to/app.db  (optional, defaults to instance/app.db)

# MySQL (Production)
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/database

# Or via components:
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DATABASE=leave_management
```

#### Connection Pooling (MySQL)
```
DB_POOL_RECYCLE_SECONDS=1800         # 30 minutes
DB_POOL_SIZE=20                       # Production
DB_MAX_OVERFLOW=30                    # Production
```

### Config Classes

#### Development Config
```python
DEBUG: True
TESTING: False
DATABASE: SQLite (instance/app.db)
Mail Backend: SMTP or console
Session Cookie: Not secure (HTTP ok)
```

#### Production Config
```python
DEBUG: False
TESTING: False
DATABASE: MySQL (via environment variables)
Mail Backend: Brevo API or SMTP
Session Cookie: Secure (HTTPS only)
Connection Pooling: Enabled
```

#### Testing Config
```python
TESTING: True
DATABASE: SQLite in-memory or separate test DB
CSRF: Disabled
Rate Limiting: Disabled
Session Cookie: Not secure
```

### Database Migrations
**Tool**: Alembic with Flask-Migrate

```bash
# Initialize migration repository
flask db init

# Create migration (auto-detect changes)
flask db migrate -m "Description of change"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade

# View migration history
flask db history
```

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager
- MySQL 5.7+ (for production) or SQLite (development)

### Setup Steps

#### 1. Clone Repository
```bash
cd /path/to/leave_flask_app
```

#### 2. Create Virtual Environment
```bash
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure Environment
Create `.env` file in project root:
```
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=true

# Database (SQLite default)
DATABASE_URL=sqlite:///instance/app.db

# Or MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DATABASE=leave_management

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=app-password

# Or Brevo
BREVO_API_KEY=your-brevo-api-key
MAIL_BACKEND=brevo_api

# Security
SECRET_KEY=your-secret-key-change-in-production
FLASK_DEBUG=false
```

#### 5. Initialize Database
```bash
# Apply migrations
flask db upgrade

# Or initialize fresh
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Seed data (optional)
flask seed-data
```

#### 6. Create Admin User
```bash
flask create-user admin admin@example.com admin --role admin --full-name "System Administrator"
```

#### 7. Run Application
```bash
python app.py

# Or use Flask command
flask run

# Application runs on http://localhost:5000
```

### Docker Setup (Optional)
```dockerfile
# Build image
docker build -t leave-management .

# Run container
docker run -p 5000:5000 \
  -e MYSQL_HOST=db \
  -e MYSQL_DATABASE=leave_management \
  leave-management
```

---

## User Workflows

### Scenario 1: Student Applying for Leave

**Flow**:
```
1. Student logs in
2. Navigates to "Apply for Leave"
3. Fills in dates (start: 2024-01-15, end: 2024-01-17)
4. Enters reason: "Family emergency"
5. Selects "Emergency Leave" checkbox
6. Submits application

System Processing:
- Validates dates and reason
- Creates Leave record (PENDING status)
- Does NOT deduct balance yet
- Sends email to assigned faculty
- Redirects to "My Leaves" dashboard

Student can see:
- Leave in PENDING state
- Option to upload proof
- Faculty comment (when reviewed)
```

**Faculty Review**:
```
1. Faculty receives email about pending leave
2. Logs in and goes to "Review Pending Leaves"
3. Sees student's leave application
4. Checks for conflicts (other students in class on same dates)
5. Reviews reason adequacy
6. Clicks "Approve" and adds comment: "Approved, emergency noted"
7. Submits approval

System Processing:
- Updates Leave status to FACULTY_APPROVED
- Sends notification to HOD
- Awaits HOD review
```

**HOD Review**:
```
1. HOD receives notification
2. Navigates to "Review Pending Leaves" (department view)
3. Sees faculty-approved leaves awaiting final approval
4. Reviews faculty's comment
5. Clicks "Approve" (final decision)
6. Adds HOD comment: "Approved by HOD"

System Processing:
- Status → APPROVED
- Calculates days: (17-15)+1 = 3 days
- Deducts 3 days from student's leave_balance
- Sends approval email to student
- Balance now reflected in dashboard
```

**Proof Upload** (if not uploaded earlier):
```
1. Student sees "Upload Proof" option for emergency leave
2. Navigates to upload page
3. Selects proof document (PDF of medical certificate)
4. Submits upload

System Processing:
- Validates file (PDF, size, MIME type)
- Stores in uploads/leave_proofs/
- Updates Leave record with filename
- Marks proof_uploaded_on timestamp
```

---

### Scenario 2: Student Applying for On-Duty

**Flow**:
```
1. Student Logs in
2. Navigates to "Apply for On-Duty"
3. Selects event date: 2024-02-10
4. Enters reason: "Participated in Technical Symposium"
5. Uploads proof: symposium_participation_certificate.pdf
6. Clicks "Submit"

System Processing:
- Validates event date
- Saves proof file
- Creates OD record (PENDING)
- Identifies assigned faculty from student's class
- Sends email to faculty
- Redirects to "My ODs"
```

**Faculty Review**:
```
1. Faculty receives OD notification
2. Reviews student's OD request and proof
3. Verifies event details
4. Clicks "Approve" with comment: "Verified participation"

System Processing:
- Status → FACULTY_APPROVED
- Sends to HOD for final approval
```

**HOD Final Approval**:
```
1. HOD reviews faculty-approved OD
2. Verifies department-wide OD policy compliance
3. Approves: "Approved - recorded in attendance"

System Processing:
- Status → APPROVED
- Student notified of approval
- OD recorded in student's academic file
- No leave balance impact (unlike leave)
```

---

### Scenario 3: Admin Creating New Department

**Flow**:
```
1. Admin logs in
2. Goes to Admin Panel
3. Selects "Create Department"
4. Enters name: "Computer Science"
5. Submits

System Processing:
- Validates name is unique
- Creates Department record
- Displays success message
- Lists all existing departments

Next Steps:
- Admin creates classes under this department
- Admin assigns faculty and HOD
```

**Creating Classes**:
```
1. Admin selects "Create Class"
2. Selects department: "Computer Science"
3. Enters year: 2 (second year)
4. Enters section: A
5. Submits

System Processing:
- Validates (CS, 2, A) doesn't exist
- Creates ClassGroup record
- Department → CS
- Year → 2
- Section → A

Class is now ready for:
- Student assignment (during user creation)
- Faculty assignment (for leave/OD review)
```

---

### Scenario 4: Faculty Reviewing Conflicting Leaves

**Situation**:
```
Two students from same class apply for overlapping leave dates:
- Student A: Jan 10-12, 2024 (3 days)
- Student B: Jan 11-13, 2024 (3 days)

Faculty reviews both applications
```

**System Behavior**:
```
When reviewing Student A's leave:
- System detects Student B has overlapping dates
- Displays conflict warning
- Faculty can see both requests side-by-side
- Faculty decides which to approve based on:
  - Leave type priority (emergency vs regular)
  - Reason adequacy
  - Class attendance needs

Faculty's decision:
- Approve Student A (emergency medical leave)
- Mark Student B for discussion (ask to reschedule)

System processing:
- Prevents both from being approved if conflict remains
- Allows faculty to make informed decisions
```

---

### Scenario 5: Admin Reviewing Analytics & Generating Reports

**Leave Report Generation**:
```
1. Admin goes to "Reports" section
2. Selects "Leave Report"
3. Filters:
   - Department: Computer Science
   - Date range: Jan 1 - Jan 31, 2024
   - Status: APPROVED
4. Clicks "Generate PDF"

Report contains:
- Student names and details
- Leave dates and duration
- Reasons (summarized)
- Approval timeline
- Status summary
- Statistics:
  * Total approved: 45 leaves
  * Total rejected: 3 leaves
  * Average duration: 2.5 days
  * Top reason: Medical (60%), Family (30%), Other (10%)
```

**Dashboard Metrics**:
```
Real-time statistics shown:
- Total users: 150
- Total departments: 5
- Total classes: 15
- Total leave requests: 500
- Total OD requests: 200
- Approval rate: 92%
- Pending approvals: 12
```

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Flask Application                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Routes (Blueprints)                  │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ • Main (Dashboard, Health Check)                        │  │
│  │ • Auth (Login, Logout)                                 │  │
│  │ • Leaves (Apply, Review, Upload Proof)                 │  │
│  │ • ODs (Apply, Review)                                  │  │
│  │ • Admin (Departments, Classes, Users, Reports)         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Business Logic (Services)                  │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ • Workflows: Leave/OD submission & review               │  │
│  │ • Auth Security: Rate limiting, login attempts          │  │
│  │ • Emailing: Queue management & sending                  │  │
│  │ • Reports: CSV/PDF generation                           │  │
│  │ • Uploads: File handling & validation                   │  │
│  │ • Scheduler: Background jobs & email queue processor    │  │
│  │ • Seed: Database initialization                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Data Layer (SQLAlchemy ORM)                │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ • User, Department, ClassGroup                          │  │
│  │ • Leave, OD, EmailQueue                                 │  │
│  │ • LoginAttempt (Rate Limiting)                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
            ┌─────────────────────────────────────┐
            │      Database Layer                │
            ├─────────────────────────────────────┤
            │ • SQLite (Development)              │
            │ • MySQL (Production)                │
            │ • Connection Pooling                │
            │ • Optimistic Locking (version_id)   │
            └─────────────────────────────────────┘
                              ↓
            ┌─────────────────────────────────────┐
            │      External Services              │
            ├─────────────────────────────────────┤
            │ • Email: SMTP or Brevo API          │
            │ • File Storage: Local or S3         │
            │ • Report Generation: PDF/CSV        │
            └─────────────────────────────────────┘
```

---

## Performance Optimization Features

### Database Indexing
```
User Table:
- Indexes on: role, (department_id, role), class_group_id, faculty_id

Leave Table:
- Indexes on: (requested_by, status), (status, applied_on),
              (start_date, end_date), approved_by

OD Table:
- Indexes on: (requested_by, status), (faculty_id, status),
              (status, applied_on), event_date

Email Queue:
- Indexes on: (status, available_at), created_at

Login Attempt:
- Indexes on: locked_until, last_attempt_at
```

### Connection Pooling
- MySQL: Pool size 20 (production), 10 (development)
- Connection recycling: 1800 seconds (30 minutes)
- Max overflow: 30 (production), 10 (development)

### Query Optimization
- Use `.first()` instead of `.all()` when expecting single result
- Leverage indexes on frequently filtered columns
- Lazy load relationships (backref configuration)
- Use `select()` for complex queries with joins

---

## Troubleshooting Guide

### Common Issues & Solutions

#### 1. Database Connection Errors
**Problem**: "Cannot connect to database"
**Solution**:
- Check DATABASE_URL environment variable
- Verify MySQL is running (production)
- Check credentials in connection string
- Run database migrations: `flask db upgrade`

#### 2. Email Not Sending
**Problem**: "Emails in queue but not sent"
**Solution**:
- Check email scheduler is enabled
- Verify MAIL_SERVER and MAIL_PORT configuration
- Check MAIL_USERNAME and MAIL_PASSWORD
- Review email logs for error details
- Ensure firewall allows SMTP port

#### 3. Login Rate Limiting Issues
**Problem**: "Account locked after failed logins"
**Solution**:
- Check LoginAttempt table for locked records
- Clear record: DELETE FROM login_attempt WHERE key='...'
- Wait for lockout expiry (default 30 minutes)
- Verify IP address in login_attempt (VPN might show different IP)

#### 4. File Upload Failures
**Problem**: "Unable to save proof document"
**Solution**:
- Check upload directory exists: `instance/uploads/leave_proofs/`
- Verify directory permissions (writable)
- Check file size doesn't exceed UPLOAD_MAX_SIZE
- Verify MIME type is in allowed list

#### 5. Permission Denied on Pages
**Problem**: "You are not authorized to view this page"
**Solution**:
- Verify user role in database
- Check role matches required permission
- Ensure user is assigned to correct department/class
- Verify faculty assignment for class
- Check HOD assignment for department

---

## Future Enhancements

### Potential Features
1. **Mobile App**: React Native mobile interface
2. **Analytics Dashboard**: Advanced analytics and insights
3. **Audit Logging**: Track all system changes
4. **API Endpoints**: REST API for integrations
5. **Bulk Operations**: Bulk upload users, bulk approvals
6. **Notifications**: SMS, push notifications
7. **Document Templates**: Customizable leave letter templates
8. **Integration**: LDAP/Active Directory for enterprise
9. **Backup/Archive**: Automatic backup and archiving
10. **Advanced Reporting**: Custom report builder

---

## Support & Contribution

### Getting Help
- Review logs in application directory
- Check database for data consistency
- Verify email configuration
- Test endpoints with Postman/curl

### Reporting Bugs
- Document steps to reproduce
- Include error messages and logs
- Describe expected vs actual behavior
- Include environment details (Python version, OS)

---

**Documentation Version**: 1.0
**Last Updated**: 2024
**Maintainer**: System Administrator
