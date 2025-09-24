# app.py
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory
from flask_migrate import Migrate
from flask_login import UserMixin
from flask_mail import Mail, Message
from flask_apscheduler import APScheduler

app = Flask(__name__)
from flask_mail import Mail, Message
from flask_apscheduler import APScheduler

# Mail configuration (example with Gmail SMTP)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'permitrack.application@gmail.com'
app.config['MAIL_PASSWORD'] = 'deps fjwz cowk hoyc' 

mail = Mail(app)

app.config['SECRET_KEY'] = os.environ.get('LEAVE_SECRET', 'dev-secret-change-this')

# MySQL DB URI - change credentials as required
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'mysql+pymysql://root:34597409raja@localhost/leave_mgmt'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads', 'od_proofs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['OD_UPLOAD_FOLDER'] = UPLOAD_FOLDER
# allow common image/doc types
ALLOWED_OD_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB per request (optional)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def send_email(subject, recipients, body):
    with app.app_context():
        msg = Message(
            subject=subject,
            sender=app.config['MAIL_USERNAME'],
            recipients=recipients,
            body=body
        )
        mail.send(msg)



# ------------------ MODELS ------------------

class Department(db.Model):
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    # hod_id links to a user who is HOD for this department (nullable)
    hod_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    # relationship to fetch hod user object (uselist=False)
    hod = db.relationship('User', foreign_keys=[hod_id], backref='hod_of_department', uselist=False)

    classes = db.relationship('ClassGroup', back_populates='department', lazy=True)


class ClassGroup(db.Model):
    __tablename__ = 'class_group'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(10), nullable=False)

    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    department = db.relationship('Department', back_populates='classes')
    faculty = db.relationship('User', foreign_keys=[faculty_id], backref='assigned_classes', uselist=False)

    # convenience string
    def __repr__(self):
        return f"<Class {self.department.name if self.department else 'NA'} Y{self.year}{self.section}>"


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)   # login username
    email = db.Column(db.String(120), unique=True, nullable=False)     # required email
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(150))
    role = db.Column(db.String(20), default='student', nullable=False)
    leave_balance = db.Column(db.Integer, default=20)

    # ✅ Self-referential faculty link
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    faculty = db.relationship('User', remote_side=[id], backref='students')

    # links to department and class (for students & faculty)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    class_group_id = db.Column(db.Integer, db.ForeignKey('class_group.id'), nullable=True)

    department = db.relationship('Department', foreign_keys=[department_id], backref='users', uselist=False)
    class_group = db.relationship('ClassGroup', foreign_keys=[class_group_id], backref='students', uselist=False)

    # Leave relationships
    requested_leaves = db.relationship('Leave', foreign_keys='Leave.requested_by', backref='requester', lazy=True)
    approved_leaves = db.relationship('Leave', foreign_keys='Leave.approved_by', backref='approver', lazy=True)


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Leave(db.Model):
    __tablename__ = 'leave'
    id = db.Column(db.Integer, primary_key=True)
    requested_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # who applied
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)    # last approver (faculty/hod)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='PENDING')  # PENDING, FACULTY_APPROVED, APPROVED, REJECTED
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)
    review_comment = db.Column(db.Text, nullable=True)
    reviewed_on = db.Column(db.DateTime, nullable=True)
    @property
    def applicant(self):
        return self.requester

class OD(db.Model):
    """On-Duty (OD) application model."""
    __tablename__ = 'od'
    id = db.Column(db.Integer, primary_key=True)
    requested_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    event_date = db.Column(db.Date, nullable=False)            # date of the OD event
    reason = db.Column(db.Text, nullable=False)
    proof_filename = db.Column(db.String(300), nullable=True)  # stored filename on server
    proof_mimetype = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), default='PENDING')      # same states as Leave
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'))  
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)
    review_comment = db.Column(db.Text, nullable=True)
    reviewed_on = db.Column(db.DateTime, nullable=True)
    faculty = db.relationship('User', foreign_keys=[faculty_id])
    requester = db.relationship('User', foreign_keys=[requested_by])
    approver = db.relationship('User', foreign_keys=[approved_by])

    # convenience
    @property
    def applicant(self):
        return User.query.get(self.requested_by)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ------------------ HELPERS ------------------
def admin_required(func):
    """Simple admin check decorator (no separate blueprint)."""
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return wrapper


def allowed_od_file(filename):
    """Check if the uploaded file has an allowed extension for OD proofs."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_OD_EXTENSIONS


# ------------------ ROUTES ------------------

@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('dashboard.html')
    return render_template('index.html')

# LOGIN / LOGOUT
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('index.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('index'))


# -------- ADMIN: create departments, classes, users --------
@app.route('/admin/create_department', methods=['GET', 'POST'])
@login_required
@admin_required
def create_department():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Department name required', 'danger')
            return redirect(url_for('create_department'))
        if Department.query.filter_by(name=name).first():
            flash('Department already exists', 'danger')
            return redirect(url_for('create_department'))
        d = Department(name=name)
        db.session.add(d)
        db.session.commit()
        flash('Department created', 'success')
        return redirect(url_for('create_department'))
    departments = Department.query.all()
    return render_template('admin_create_department.html', departments=departments)


@app.route('/admin/create_class', methods=['GET', 'POST'])
@login_required
@admin_required
def create_class():
    if request.method == 'POST':
        dept_id = request.form.get('department_id', type=int)
        year = request.form.get('year', type=int)
        section = request.form.get('section', '').strip()
        if not (dept_id and year and section):
            flash('Department, year and section are required', 'danger')
            return redirect(url_for('create_class'))
        cg = ClassGroup(year=year, section=section, department_id=dept_id)
        db.session.add(cg)
        db.session.commit()
        flash('Class created', 'success')
        return redirect(url_for('create_class'))
    departments = Department.query.all()
    classes = ClassGroup.query.order_by(ClassGroup.department_id, ClassGroup.year, ClassGroup.section).all()
    return render_template('admin_create_class.html', departments=departments, classes=classes)


@app.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_user():
    """
    Admin-only page to create users.
    - Student: must select class, department inferred.
    - Faculty: optional class assignment.
    - HOD: must select department.
    """
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        register_number = request.form.get('register_number')
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'student')
        department_id = request.form.get('department_id', type=int)
        class_group_id = request.form.get('class_group_id', type=int)

        # Basic required fields
        if not (username and email and password and role):
            flash('Username, email, password, and role are required.', 'danger')
            return redirect(url_for('admin_create_user'))

        # Check unique username/email
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('User with that username or email already exists', 'danger')
            return redirect(url_for('admin_create_user'))

        # Role-specific validation
        if role == 'student' and not class_group_id:
            flash('Student must be assigned to a class.', 'danger')
            return redirect(url_for('admin_create_user'))
        if role == 'hod' and not department_id:
            flash('HOD must be assigned to a department.', 'danger')
            return redirect(url_for('admin_create_user'))

        # Create user
        u = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            leave_balance=20
        )

        # Assign department and class based on role
        if role == 'student':
            cg = ClassGroup.query.get(class_group_id)
            if not cg:
                flash('Selected class not found.', 'danger')
                return redirect(url_for('admin_create_user'))
            u.class_group_id = cg.id
            u.department_id = cg.department_id
        else:
            if department_id:
                u.department_id = department_id
            if class_group_id:
                u.class_group_id = class_group_id

        # Set password and save
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

        # Post actions
        if role == 'hod' and department_id:
            dept = Department.query.get(department_id)
            if dept:
                dept.hod_id = u.id
                db.session.commit()
        if role == 'faculty' and class_group_id:
            cg = ClassGroup.query.get(class_group_id)
            if cg:
                cg.faculty_id = u.id
                db.session.commit()

        flash(f'{role.capitalize()} user created successfully.', 'success')
        return redirect(url_for('admin_create_user'))

    departments = Department.query.all()
    classes = ClassGroup.query.all()
    return render_template('admin_create_user.html', departments=departments, classes=classes)


# -------- APPLY LEAVE (students & faculty can apply) --------
@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply_leave():
    if current_user.role not in ('student', 'faculty'):
        flash('Only students or faculty may apply for leave', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        start = request.form.get('start_date')
        end = request.form.get('end_date')
        reason = request.form.get('reason', '').strip()
        try:
            start_d = datetime.fromisoformat(start).date()
            end_d = datetime.fromisoformat(end).date()
        except Exception:
            flash('Enter valid dates in YYYY-MM-DD format', 'danger')
            return redirect(url_for('apply_leave'))
        if end_d < start_d:
            flash('End date cannot be before start date', 'danger')
            return redirect(url_for('apply_leave'))

        # check overlap with existing approved/pending leaves
        overlapping = Leave.query.filter(
            Leave.requested_by == current_user.id,
            Leave.status.in_(['PENDING', 'FACULTY_APPROVED', 'APPROVED']),
            Leave.start_date <= end_d,
            Leave.end_date >= start_d
        ).first()
        if overlapping:
            flash('You already have a leave overlapping this period', 'danger')
            return redirect(url_for('apply_leave'))

        days = (end_d - start_d).days + 1
        if current_user.leave_balance < days and current_user.role == 'student':
            # students must have enough balance at apply time (optional: you can decide to only check at HOD approval)
            flash(f'Not enough leave balance. You have {current_user.leave_balance} days left.', 'danger')
            return redirect(url_for('apply_leave'))

        # find assigned faculty for student's class (if exists)
        assigned_faculty_id = None
        if current_user.class_group_id:
            cg = ClassGroup.query.get(current_user.class_group_id)
            if cg and cg.faculty_id:
                assigned_faculty_id = cg.faculty_id

        new_leave = Leave(
            requested_by=current_user.id,
            approved_by=assigned_faculty_id,   # initial approver
            start_date=start_d,
            end_date=end_d,
            reason=reason,
            status='PENDING'  # faculty will review first
        )
        db.session.add(new_leave)
        db.session.commit()
        flash('Leave applied successfully', 'success')
        return redirect(url_for('my_leaves'))

    return render_template('apply.html')

@app.route('/my_ods', methods=['GET', 'POST'])
@login_required
def my_ods():
    if request.method == 'POST':
        event_date_str = request.form.get('od_date')
        reason = request.form.get('reason')

        if not event_date_str:
            flash("Event date is required.", "danger")
            return redirect(request.url)

        try:
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format.", "danger")
            return redirect(request.url)

        proof_filename = None
        proof_mimetype = None
        if 'proof' in request.files:
            file = request.files['proof']
            if file and file.filename and allowed_od_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['OD_UPLOAD_FOLDER'], filename))
                proof_filename = filename
                proof_mimetype = file.mimetype
            elif file and file.filename:
                flash("Invalid file type.", "danger")
                return redirect(request.url)

        assigned_faculty_id = None
        if current_user.class_group_id:
            cg = ClassGroup.query.get(current_user.class_group_id)
            if cg and cg.faculty_id:
                assigned_faculty_id = cg.faculty_id

        new_od = OD(
        requested_by=current_user.id,
        faculty_id=assigned_faculty_id,
        event_date=event_date,
        reason=reason,
        proof_filename=proof_filename,
        proof_mimetype=proof_mimetype,
        status='PENDING'
        )

        db.session.add(new_od)
        db.session.commit()
        flash("OD application submitted successfully.", "success")
        return redirect(url_for('my_ods'))

    # Fetch all OD requests of logged-in user
    ods = OD.query.filter_by(requested_by=current_user.id).order_by(OD.applied_on.desc()).all()
    return render_template('my_ods.html', ods=ods)


from flask import request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os

@app.route('/apply_od', methods=['GET', 'POST'])
@login_required
def apply_od():
    if request.method == 'POST':
        # Get form values safely
        event_date = request.form.get('event_date')
        reason = request.form.get('reason')
        proof = request.files.get('proof')

        # Validate required fields
        if not event_date or not reason:
            flash("Date and reason are required.", "danger")
            return redirect(request.url)

        # Handle proof file
        proof_filename, proof_mimetype = None, None
        if proof and proof.filename:
            proof_filename = secure_filename(proof.filename)
            proof_mimetype = proof.mimetype
            proof.save(os.path.join(app.config['OD_UPLOAD_FOLDER'], proof_filename))

        # ✅ Faculty assignment
        assigned_faculty_id = None

        # 1. Try via class group
        if current_user.class_group_id:
            cg = ClassGroup.query.get(current_user.class_group_id)
            if cg and cg.faculty_id:
                assigned_faculty_id = cg.faculty_id

        # 2. Fallback: use faculty_id directly from user table
        if not assigned_faculty_id and current_user.faculty_id:
            assigned_faculty_id = current_user.faculty_id

        # 3. If none found, reject
        if not assigned_faculty_id:
            flash("No faculty assigned to your class or profile. Please contact admin.", "danger")
            return redirect(url_for('my_ods'))

        # ✅ Create OD request
        new_od = OD(
            requested_by=current_user.id,
            faculty_id=assigned_faculty_id,
            event_date=event_date,
            reason=reason,
            proof_filename=proof_filename,
            proof_mimetype=proof_mimetype,
            status='PENDING'
        )
        db.session.add(new_od)
        db.session.commit()

        flash("OD request submitted successfully.", "success")
        return redirect(url_for('my_ods'))

    return render_template('apply_od.html')




# -------- PENDING OD: faculty sees PENDING; hod sees FACULTY_APPROVED --------
@app.route('/pending_od')
@login_required
def pending_od():
    if current_user.role == 'faculty':
        # Faculty sees only PENDING OD requests assigned to them
        ods = OD.query.filter_by(faculty_id=current_user.id, status='PENDING').all()

    elif current_user.role == 'hod':
        # HOD sees only requests already approved by faculty
        ods = OD.query.filter_by(status='FACULTY_APPROVED').all()

    else:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('index'))

    return render_template('pending_od.html', ods=ods)


@app.context_processor
def inject_pending_count():
    if current_user.is_authenticated:
        if current_user.role == 'faculty':
            count = OD.query.filter_by(status='PENDING', faculty_id=current_user.id).count()
        elif current_user.role == 'hod':
            count = OD.query.filter_by(status='FACULTY_APPROVED').count()
        else:
            count = 0
    else:
        count = 0
    return dict(pending_count=count)


# -------- REVIEW OD (faculty / hod) --------
@app.route('/review_od/<int:od_id>', methods=['GET', 'POST'])
@login_required
def review_od(od_id):
    od = OD.query.get_or_404(od_id)
    student = User.query.get(od.requested_by)

    if current_user.role == 'faculty' and od.status != 'PENDING':
        flash('Faculty can only review pending ODs.', 'danger')
        return redirect(url_for('pending_od'))

    if current_user.role == 'hod' and od.status != 'FACULTY_APPROVED':
        flash('HOD can only review faculty-approved ODs.', 'danger')
        return redirect(url_for('pending_od'))

    if current_user.role not in ('faculty', 'hod'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        action = request.form.get('action')
        comment = request.form.get('comment', '').strip()

        if action not in ('APPROVE', 'REJECT'):
            flash('Invalid action', 'danger')
            return redirect(url_for('review_od', od_id=od_id))

        approver_name = current_user.full_name
        approver_role = current_user.role.upper()
        # Try to get faculty department from direct assignment or from class
        if current_user.department:
            approver_department = current_user.department.name
        elif current_user.assigned_classes:
            # Use the department of the first assigned class
            approver_department = current_user.assigned_classes[0].department.name if current_user.assigned_classes[0].department else "N/A"
        else:
            approver_department = "N/A"


        if action == 'APPROVE':
            if current_user.role == 'faculty':
                od.status = 'FACULTY_APPROVED'
                od.approved_by = None
                send_email(
                    "OD Forwarded to HOD",
                    [student.email],
                    f"""Dear {student.full_name},

Your OD request on {od.event_date} has been **approved by Faculty**: {approver_name}, {approver_department} department.
It has now been forwarded to the HOD for final approval.

Comment: {comment}

Regards,
Easwari Engineering College
"""
                )
            elif current_user.role == 'hod':
                od.status = 'APPROVED'
                od.approved_by = current_user.id
                send_email(
                    "OD Approved by HOD",
                    [student.email],
                    f"""Dear {student.full_name},

Your OD request on {od.event_date} has been **approved by HOD**: {approver_name}, Head of {approver_department} Department.

Comment: {comment}

Regards,
Easwari Engineering College
"""
                )
        else:  # REJECT
            od.status = 'REJECTED'
            od.approved_by = current_user.id
            send_email(
                "OD Rejected",
                [student.email],
                f"""Dear {student.full_name},

Your OD request on {od.event_date} has been **rejected** by {approver_role}: {approver_name}, {approver_department} Department.

Comment: {comment}

Regards,
Easwari Engineering College
"""
            )

        od.review_comment = comment
        od.reviewed_on = datetime.utcnow()
        db.session.commit()
        flash(f'OD {od.status}', 'success')
        return redirect(url_for('pending_od'))

    return render_template('review_od.html', od=od)




# -------- Serve / Download OD proof (permission-check) --------
@app.route('/od_proof/<int:od_id>')
@login_required
def send_od_proof(od_id):
    od = OD.query.get_or_404(od_id)
    if not od.proof_filename:
        flash('No proof uploaded for this OD', 'danger')
        return redirect(url_for('index'))

    # permission: requester, faculty for their class, hod of dept, or admin
    allowed = False
    if current_user.id == od.requested_by or current_user.role == 'admin':
        allowed = True
    elif current_user.role == 'faculty':
        # is this faculty assigned to requester's class?
        requester = User.query.get(od.requested_by)
        if requester and requester.class_group_id:
            cg = ClassGroup.query.get(requester.class_group_id)
            if cg and cg.faculty_id == current_user.id:
                allowed = True
    elif current_user.role == 'hod':
        requester = User.query.get(od.requested_by)
        if requester and requester.department_id:
            dept = Department.query.get(requester.department_id)
            if dept and dept.hod_id == current_user.id:
                allowed = True

    if not allowed:
        flash('You are not authorized to access this file', 'danger')
        return redirect(url_for('index'))

    return send_from_directory(app.config['OD_UPLOAD_FOLDER'], od.proof_filename, as_attachment=True)

# -------- VIEW PERSONAL LEAVES --------
@app.route('/my_leaves')
@login_required
def my_leaves():
    leaves = Leave.query.filter_by(requested_by=current_user.id).order_by(Leave.applied_on.desc()).all()
    return render_template('my_leaves.html', leaves=leaves)


# -------- PENDING: faculty sees pending for their classes; hod sees faculty-approved for their dept --------
@app.route('/pending')
@login_required
def pending():
    if current_user.role == 'faculty':
        # faculty sees leaves of students in classes assigned to them, status == PENDING
        leaves = (Leave.query
                  .join(User, User.id == Leave.requested_by)
                  .join(ClassGroup, ClassGroup.id == User.class_group_id)
                  .filter(ClassGroup.faculty_id == current_user.id, Leave.status == 'PENDING')
                  .order_by(Leave.applied_on.asc())
                  .all())
    elif current_user.role == 'hod':
        # hod sees leaves that have been approved by faculty (FACULTY_APPROVED) in their department
        leaves = (Leave.query
                  .join(User, User.id == Leave.requested_by)
                  .join(Department, Department.id == User.department_id)
                  .filter(Department.hod_id == current_user.id, Leave.status == 'FACULTY_APPROVED')
                  .order_by(Leave.applied_on.asc())
                  .all())
    else:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    return render_template('pending.html', leaves=leaves)


# -------- REVIEW: faculty approves => FACULTY_APPROVED; hod approves => APPROVED & deduct balance --------
@app.route('/review/<int:leave_id>', methods=['GET', 'POST'])
@login_required
def review(leave_id):
    leave = Leave.query.get_or_404(leave_id)
    student = User.query.get(leave.requested_by)
    department = student.department.name if student.department else "N/A"

    # Determine faculty and HOD
    faculty = User.query.get(leave.approved_by) if leave.approved_by else None
    hod = None
    if current_user.role == 'hod':
        hod = current_user

    if current_user.role not in ('faculty', 'hod'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('pending'))

    # Role-based status check
    if current_user.role == 'faculty' and leave.status != 'PENDING':
        flash('Faculty can only review pending leaves.', 'danger')
        return redirect(url_for('pending'))
    if current_user.role == 'hod' and leave.status != 'FACULTY_APPROVED':
        flash('HOD can only review faculty-approved leaves.', 'danger')
        return redirect(url_for('pending'))

    if request.method == 'POST':
        action = request.form.get('action')
        comment = request.form.get('comment', '').strip()

        if action not in ('APPROVE', 'REJECT'):
            flash('Invalid action', 'danger')
            return redirect(url_for('review', leave_id=leave_id))

        # APPROVE action
        if action == 'APPROVE':
            if current_user.role == 'faculty':
                leave.status = 'FACULTY_APPROVED'
                leave.approved_by = current_user.id
                approver_name = current_user.full_name
                # Try to get faculty department from direct assignment or from class
                if current_user.department:
                    approver_department = current_user.department.name
                elif current_user.assigned_classes:
                    # Use the department of the first assigned class
                    approver_department = current_user.assigned_classes[0].department.name if current_user.assigned_classes[0].department else "N/A"
                else:
                    approver_department = "N/A"

                send_email(
                    "Leave Forwarded to HOD",
                    [student.email],
                    f"""Dear {student.full_name},

Your leave request from {leave.start_date} to {leave.end_date} has been **approved by Faculty**: {approver_name}, {approver_department} department.
It has now been forwarded to the HOD for final approval.

Comment: {comment}

Regards,
Easwari Engineering College
"""
                )
            elif current_user.role == 'hod':
                # Final approval
                days = (leave.end_date - leave.start_date).days + 1
                if student.leave_balance < days:
                    flash(f"Student doesn't have enough leave balance ({student.leave_balance})", 'danger')
                    return redirect(url_for('review', leave_id=leave_id))
                student.leave_balance -= days
                leave.status = 'APPROVED'
                leave.approved_by = current_user.id
                approver_name = current_user.full_name
                send_email(
                    "Leave Approved by HOD",
                    [student.email],
                    f"""Dear {student.full_name},

Your leave request from {leave.start_date} to {leave.end_date} has been **approved by HOD**: {approver_name}, Head of {department} Department.

Comment: {comment}

Please ensure that you complete any missed lectures or assignments.

Regards,
Easwari Engineering College
"""
                )
        else:  # REJECT
            leave.status = 'REJECTED'
            leave.approved_by = current_user.id
            approver_name = current_user.full_name
            approver_role = current_user.role.upper()
            send_email(
                "Leave Rejected",
                [student.email],
                f"""Dear {student.full_name},

Your leave request from {leave.start_date} to {leave.end_date} has been **rejected** by {approver_role}: {approver_name}, {department} Department.

Comment: {comment}

Regards,
Easwari Engineering College
"""
            )

        leave.review_comment = comment
        leave.reviewed_on = datetime.utcnow()
        db.session.commit()
        flash(f'Leave {leave.status}', 'success')
        return redirect(url_for('pending'))

    return render_template('review.html', leave=leave)



# -------- ADMIN: assign HOD to a dept or faculty to a class (alternate routes) --------
@app.route('/admin/assign_hod', methods=['GET', 'POST'])
@login_required
@admin_required
def assign_hod():
    departments = Department.query.all()
    faculty_users = User.query.filter_by(role='hod').all()  # allow creating hod users first, or filter role='faculty'
    if request.method == 'POST':
        dept_id = request.form.get('department_id', type=int)
        hod_user_id = request.form.get('hod_user_id', type=int)
        dept = Department.query.get(dept_id)
        if not dept:
            flash('Department not found', 'danger')
            return redirect(url_for('assign_hod'))
        dept.hod_id = hod_user_id
        db.session.commit()
        flash('HOD assigned', 'success')
        return redirect(url_for('assign_hod'))
    return render_template('admin_assign_hod.html', departments=departments, faculty_users=faculty_users)


@app.route('/admin/assign_faculty', methods=['GET', 'POST'])
@login_required
@admin_required
def assign_faculty():
    classes = ClassGroup.query.all()
    faculty_users = User.query.filter_by(role='faculty').all()
    if request.method == 'POST':
        class_id = request.form.get('class_group_id', type=int)
        faculty_id = request.form.get('faculty_id', type=int)
        cg = ClassGroup.query.get(class_id)
        if not cg:
            flash('Class not found', 'danger')
            return redirect(url_for('assign_faculty'))
        cg.faculty_id = faculty_id
        db.session.commit()
        flash('Faculty assigned to class', 'success')
        return redirect(url_for('assign_faculty'))
    return render_template('admin_assign_faculty.html', classes=classes, faculty_users=faculty_users)

@app.route('/admin_all_ods')
@login_required
def admin_all_ods():
    if current_user.role != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('index'))

    ods = OD.query.all()
    return render_template('admin_all_ods.html', ods=ods)


# -------- INIT DB (create sample data) --------
@app.route('/initdb')
def initdb():
    db.create_all()

    # -------- Create sample department --------
    cs = Department.query.filter_by(name='Computer Science').first()
    if not cs:
        cs = Department(name='Computer Science')
        db.session.add(cs)
        db.session.commit()

    # -------- Create sample class --------
    cg = ClassGroup.query.filter_by(year=1, section='A', department_id=cs.id).first()
    if not cg:
        cg = ClassGroup(year=1, section='A', department_id=cs.id)
        db.session.add(cg)
        db.session.commit()

    # -------- Create admin user --------
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@example.com',
            full_name='Administrator',
            role='admin',
            leave_balance=999
        )
        admin.set_password('adminpass')  # default password
        db.session.add(admin)
        db.session.commit()

    # -------- Create HOD --------
    if not User.query.filter_by(username='hod').first():
        hod = User(
            username='hod',
            email='hod@example.com',
            full_name='Head of Dept',
            role='hod',
            leave_balance=20,
            department_id=cs.id
        )
        hod.set_password('hodpass')
        db.session.add(hod)
        db.session.commit()
        cs.hod_id = hod.id
        db.session.commit()

    # -------- Create faculty --------
    if not User.query.filter_by(username='faculty').first():
        faculty = User(
            username='faculty',
            email='faculty@example.com',
            full_name='Faculty Member',
            role='faculty',
            leave_balance=20
        )
        faculty.set_password('facpass')
        db.session.add(faculty)
        db.session.commit()
        cg.faculty_id = faculty.id
        db.session.commit()

    # -------- Create student --------
    if not User.query.filter_by(username='student').first():
        student = User(
            username='student',
            email='student@example.com',
            full_name='Student One',
            role='student',
            class_group_id=cg.id,
            department_id=cs.id,
            leave_balance=20
        )
        student.set_password('studpass')
        db.session.add(student)
        db.session.commit()

    return "Database initialized with sample departments, classes, and users (admin/hod/faculty/student)."



# -------- ADMIN VIEW: see all leaves (optional) --------
@app.route('/admin/all_leaves')
@login_required
@admin_required
def admin_all_leaves():
    leaves = Leave.query.order_by(Leave.applied_on.desc()).all()
    return render_template('admin_all_leaves.html', leaves=leaves)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

@scheduler.task('cron', id='daily_summary', hour=15, minute=30)  # 3:30 PM daily
def send_daily_summary():
    with app.app_context():
        faculties = User.query.filter_by(role='faculty').all()
        hods = User.query.filter_by(role='hod').all()

        # Notify faculty about pending ODs and leaves
        for fac in faculties:
            pending_ods = OD.query.filter_by(faculty_id=fac.id, status='PENDING').count()
            pending_leaves = (Leave.query
                .join(ClassGroup, ClassGroup.id == User.class_group_id)
                .filter(ClassGroup.faculty_id == fac.id, Leave.status == 'PENDING')
                .count())
            
            if pending_ods or pending_leaves:
                body = f"Hello {fac.full_name},\n\nYou have:\n- {pending_ods} OD requests\n- {pending_leaves} Leave requests\npending for review."
                send_email("Daily Pending Applications", [fac.email], body)

        # Notify HOD about pending ODs and leaves
        for hod in hods:
            pending_ods = OD.query.filter_by(status='FACULTY_APPROVED').count()
            pending_leaves = (Leave.query
                .join(User, User.department_id == hod.department_id)
                .filter(Leave.status == 'FACULTY_APPROVED')
                .count())

            if pending_ods or pending_leaves:
                body = f"Hello {hod.full_name},\n\nYou have:\n- {pending_ods} OD requests\n- {pending_leaves} Leave requests\nwaiting for your review."
                send_email("Daily Pending Applications", [hod.email], body)


# -------- RUN APP --------
if __name__ == '__main__':
    app.run(debug=True)
