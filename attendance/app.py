from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
import pytz

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))
    role = db.Column(db.String(20))  # student, ta, professor

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    date = db.Column(db.String(10), default=datetime.now().strftime('%Y-%m-%d'))
    status = db.Column(db.String(10))  # present/absent

class AttendanceCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6))
    expires_at = db.Column(db.DateTime)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login_page')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        login_user(user)
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid credentials')
        return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'student':
        return redirect(url_for('student_view'))
    else:
        return redirect(url_for('ta_view'))

# Student View (Self-Marking Attendance)
@app.route('/student')
@login_required
def student_view():
    if current_user.role != 'student':
        return "Unauthorized", 403

    # Calculate attendance percentage
    attendance_days = db.session.query(Attendance.date).filter_by(student_id=current_user.id).distinct().all()
    total_days = len(attendance_days)
    present_days = db.session.query(Attendance.date)\
                    .filter_by(student_id=current_user.id, status='present')\
                    .distinct().count()
    percentage = (present_days / total_days * 100) if total_days > 0 else 0

    # Fetch all attendance records for the student
    attendance_records = Attendance.query.filter_by(student_id=current_user.id).all()

    return render_template('student.html', percentage=percentage, attendance_records=attendance_records)

# TA/Professor View
@app.route('/ta')
@login_required
def ta_view():
    if current_user.role not in ['ta', 'professor']:
        return "Unauthorized", 403

    # Fetch all students
    students = User.query.filter_by(role='student').all()

    # Fetch all unique dates from the Attendance table
    unique_dates = db.session.query(Attendance.date).distinct().all()
    unique_dates = [date[0] for date in unique_dates]  # Convert to a list of strings

    # Fetch attendance details for each student and date
    attendance_details = {}
    attendance_percentages = {}
    for student in students:
        student_attendance = {}
        total_days = len(unique_dates)
        present_days = 0

        for date in unique_dates:
            attendance_record = Attendance.query.filter_by(student_id=student.id, date=date).first()
            if attendance_record and attendance_record.status == 'present':
                student_attendance[date] = 'present'
                present_days += 1
            else:
                student_attendance[date] = 'absent'

        attendance_details[student.id] = student_attendance
        attendance_percentages[student.id] = (present_days / total_days * 100) if total_days > 0 else 0

    return render_template('ta.html', students=students, unique_dates=unique_dates, attendance_details=attendance_details, attendance_percentages=attendance_percentages)

# TA Generates Attendance Code
@app.route('/generate_code', methods=['POST'])
@login_required
def generate_code():
    if current_user.role != 'ta':
        return "Unauthorized", 403

    try:
        import random
        code = str(random.randint(100000, 999999))
        
        # Set IST timezone
        ist_timezone = pytz.timezone('Asia/Kolkata')
        expires_at = datetime.now(ist_timezone) + timedelta(minutes=5)  # Convert to IST

        new_code = AttendanceCode(code=code, expires_at=expires_at)
        db.session.add(new_code)
        db.session.commit()
        flash(f'Code generated: {code} (expires at {expires_at.strftime("%H:%M:%S")})')
    except Exception as e:
        db.session.rollback()
        flash(f'Error generating code: {str(e)}')

    return redirect(url_for('ta_view'))

# Student Marks Attendance
@app.route('/mark_attendance', methods=['POST'])
@login_required
def mark_attendance():
    if current_user.role != 'student':
        return "Unauthorized", 403

    code = request.form['code'].strip()
    valid_code = AttendanceCode.query.filter_by(code=code).filter(
        AttendanceCode.expires_at > datetime.now(pytz.timezone('Asia/Kolkata'))
    ).first()

    if valid_code:
        # Check if attendance already marked for today
        today = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d')
        existing = Attendance.query.filter_by(
            student_id=current_user.id,
            date=today
        ).first()

        if not existing:
            record = Attendance(student_id=current_user.id, status='present', date=today)
            db.session.add(record)
            db.session.delete(valid_code)
            db.session.commit()
            flash('Attendance marked!')
        else:
            flash('Already marked attendance today!')
    else:
        flash('Invalid or expired code')

    return redirect(url_for('student_view'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
