from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, flash, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import random
import string
import os
import csv
import io
from datetime import datetime
from werkzeug.utils import secure_filename
import json

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cbt_exam.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialize extensions
db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matric_number = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(10), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'matricNumber': self.matric_number,
            'fullName': self.full_name,
            'level': self.level,
            'department': self.department
        }

class ExamSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    exam_time = db.Column(db.String(20), nullable=False)
    exam_center = db.Column(db.String(20), nullable=False)
    token_id = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(20), default='Scheduled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('Student', backref=db.backref('exam_schedule', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'matricNumber': self.student.matric_number,
            'fullName': self.student.full_name,
            'level': self.student.level,
            'department': self.student.department,
            'email': self.email,
            'examTime': self.exam_time,
            'examCenter': self.exam_center,
            'tokenId': self.token_id,
            'status': self.status,
            'createdAt': self.created_at.isoformat()
        }

# Helper functions
def generate_token():
    prefix = "EX-" + datetime.now().strftime("%Y")
    random_part = ''.join(random.choices(string.digits, k=5))
    return f"{prefix}-{random_part}"

def assign_exam_slot(student):
    # Get counts for each time slot and center
    time_slots = ["9:00 AM", "11:00 AM", "1:00 PM"]
    centers = ["ICT1", "ICT2"]
    
    slot_counts = {}
    for slot in time_slots:
        slot_counts[slot] = ExamSchedule.query.filter_by(exam_time=slot).count()
    
    center_counts = {}
    for center in centers:
        center_counts[center] = ExamSchedule.query.filter_by(exam_center=center).count()
    
    # Assign based on level and balance
    if student.level == "100L":
        # Prefer morning slots for 100L
        preferred_slots = ["9:00 AM", "11:00 AM", "1:00 PM"]
    else:
        # Prefer later slots for 200L
        preferred_slots = ["11:00 AM", "1:00 PM", "9:00 AM"]
    
    # Find the least populated slot from preferred slots
    min_slot = min(preferred_slots, key=lambda s: slot_counts.get(s, 0))
    
    # Find the least populated center
    min_center = min(centers, key=lambda c: center_counts.get(c, 0))
    
    return {
        'examTime': min_slot,
        'examCenter': min_center,
        'tokenId': generate_token()
    }

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple authentication for demo
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get statistics for dashboard
    total_students = Student.query.count()
    total_scheduled = ExamSchedule.query.count()
    
    # Get level distribution
    level_100 = Student.query.filter_by(level="100L").count()
    level_200 = Student.query.filter_by(level="200L").count()
    
    # Get center capacity
    ict1_count = ExamSchedule.query.filter_by(exam_center="ICT1").count()
    ict2_count = ExamSchedule.query.filter_by(exam_center="ICT2").count()
    
    # Get time slot distribution
    slot_9am = ExamSchedule.query.filter_by(exam_time="9:00 AM").count()
    slot_11am = ExamSchedule.query.filter_by(exam_time="11:00 AM").count()
    slot_1pm = ExamSchedule.query.filter_by(exam_time="1:00 PM").count()
    
    # Get department distribution
    departments = db.session.query(
        Student.department, 
        db.func.count(Student.id)
    ).group_by(Student.department).all()
    
    department_stats = [{"name": dept, "count": count} for dept, count in departments]
    
    stats = {
        'totalStudents': total_students,
        'totalScheduled': total_scheduled,
        'levelDistribution': {
            '100L': level_100,
            '200L': level_200
        },
        'centerCapacity': {
            'ICT1': {
                'scheduled': ict1_count,
                'capacity': 50
            },
            'ICT2': {
                'scheduled': ict2_count,
                'capacity': 40
            }
        },
        'timeSlots': {
            '9:00 AM': {
                'scheduled': slot_9am,
                'capacity': 30
            },
            '11:00 AM': {
                'scheduled': slot_11am,
                'capacity': 30
            },
            '1:00 PM': {
                'scheduled': slot_1pm,
                'capacity': 30
            }
        },
        'departmentStats': department_stats
    }
    
    # Get all students for the table
    students = Student.query.all()
    students_list = [student.to_dict() for student in students]
    
    return render_template('admin/dashboard.html', stats=stats, students=students_list)

@app.route('/api/upload-students', methods=['POST'])
def upload_students():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Read the CSV file
            df = pd.read_csv(file_path)
            required_columns = ['Matric Number', 'Full Name', 'Level']
            
            # Check if all required columns are present
            if not all(col in df.columns for col in required_columns):
                return jsonify({'error': 'CSV file must contain Matric Number, Full Name, and Level columns'}), 400
            
            # Process each row
            success_count = 0
            duplicate_count = 0
            error_count = 0
            
            for _, row in df.iterrows():
                try:
                    matric_number = row['Matric Number']
                    full_name = row['Full Name']
                    level = row['Level']
                    department = row.get('Department', '')
                    
                    # Format matric number to 9 digits (e.g., 220903042)
                    if isinstance(matric_number, (int, float)):
                        matric_number = str(int(matric_number)).zfill(9)
                    
                    # Check if student already exists
                    existing_student = Student.query.filter_by(matric_number=matric_number).first()
                    if existing_student:
                        duplicate_count += 1
                        continue
                    
                    # Create new student
                    new_student = Student(
                        matric_number=matric_number,
                        full_name=full_name,
                        level=level,
                        department=department
                    )
                    
                    db.session.add(new_student)
                    success_count += 1
                    
                except Exception as e:
                    print(f"Error processing row: {e}")
                    error_count += 1
            
            db.session.commit()
            
            # Clean up
            os.remove(file_path)
            
            return jsonify({
                'message': 'Student data uploaded successfully',
                'success': success_count,
                'duplicates': duplicate_count,
                'errors': error_count
            }), 200
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': str(e)}), 500

@app.route('/student/register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        matric_number = request.form.get('matricNumber')
        email = request.form.get('email')
        
        if not matric_number or not email:
            flash('Matriculation number and email are required', 'danger')
            return render_template('student/register.html')
        
        # Check if student exists
        student = Student.query.filter_by(matric_number=matric_number).first()
        if not student:
            flash('Student not found in the database', 'danger')
            return render_template('student/register.html')
        
        # Check if student is already scheduled
        existing_schedule = ExamSchedule.query.filter_by(student_id=student.id).first()
        if existing_schedule:
            flash('Student is already registered for an exam', 'danger')
            return render_template('student/register.html')
        
        # Assign exam slot
        exam_details = assign_exam_slot(student)
        exam_details['email'] = email
        
        # Create exam schedule
        new_schedule = ExamSchedule(
            student_id=student.id,
            email=email,
            exam_time=exam_details['examTime'],
            exam_center=exam_details['examCenter'],
            token_id=exam_details['tokenId'],
            status='Scheduled'
        )
        
        db.session.add(new_schedule)
        db.session.commit()
        
        # Prepare data for confirmation page
        confirmation_data = {
            'matricNumber': student.matric_number,
            'fullName': student.full_name,
            'level': student.level,
            'department': student.department,
            'email': email,
            'examTime': exam_details['examTime'],
            'examCenter': exam_details['examCenter'],
            'tokenId': exam_details['tokenId']
        }
        
        session['confirmation_data'] = confirmation_data
        return redirect(url_for('student_confirmation'))
    
    return render_template('student/register.html')

@app.route('/student/confirmation')
def student_confirmation():
    confirmation_data = session.get('confirmation_data')
    if not confirmation_data:
        return redirect(url_for('student_register'))
    
    return render_template('student/confirmation.html', data=confirmation_data)

@app.route('/student/portal')
def student_portal():
    return render_template('student/index.html')

@app.route('/api/check-status', methods=['POST'])
def check_status():
    data = request.json
    matric_number = data.get('matricNumber')
    token_id = data.get('tokenId')
    
    if not matric_number or not token_id:
        return jsonify({'error': 'Matriculation number and token ID are required'}), 400
    
    # Find the student
    student = Student.query.filter_by(matric_number=matric_number).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    # Find the exam schedule
    schedule = ExamSchedule.query.filter_by(student_id=student.id, token_id=token_id).first()
    if not schedule:
        return jsonify({'error': 'No exam scheduled with this token ID'}), 404
    
    return jsonify({
        'matricNumber': student.matric_number,
        'fullName': student.full_name,
        'level': student.level,
        'department': student.department,
        'email': schedule.email,
        'examTime': schedule.exam_time,
        'examCenter': schedule.exam_center,
        'status': schedule.status
    }), 200

@app.route('/api/students')
def get_students():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    center = request.args.get('center', 'all')
    time_slot = request.args.get('timeSlot', 'all')
    level = request.args.get('level', 'all')
    
    query = db.session.query(ExamSchedule, Student).join(Student)
    
    if center != 'all':
        query = query.filter(ExamSchedule.exam_center == center)
    
    if time_slot != 'all':
        query = query.filter(ExamSchedule.exam_time == time_slot)
    
    if level != 'all':
        query = query.filter(Student.level == level)
    
    results = query.all()
    
    students = []
    for schedule, student in results:
        students.append({
            **student.to_dict(),
            'email': schedule.email,
            'examTime': schedule.exam_time,
            'examCenter': schedule.exam_center,
            'tokenId': schedule.token_id,
            'status': schedule.status
        })
    
    return jsonify(students), 200

@app.route('/api/stats')
def get_stats():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Get statistics for dashboard
    total_students = Student.query.count()
    total_scheduled = ExamSchedule.query.count()
    
    # Get level distribution
    level_100 = Student.query.filter_by(level="100L").count()
    level_200 = Student.query.filter_by(level="200L").count()
    
    return jsonify({
        'totalStudents': total_students,
        'totalScheduled': total_scheduled,
        'levelDistribution': {
            '100L': level_100,
            '200L': level_200
        }
    }), 200

@app.route('/api/update-status', methods=['POST'])
def update_status():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    matric_number = data.get('matricNumber')
    status = data.get('status')  # 'Present' or 'Absent'
    
    if not matric_number or not status:
        return jsonify({'error': 'Matriculation number and status are required'}), 400
    
    # Find the student and their schedule
    student = Student.query.filter_by(matric_number=matric_number).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    schedule = ExamSchedule.query.filter_by(student_id=student.id).first()
    if not schedule:
        return jsonify({'error': 'Student not scheduled for an exam'}), 404
    
    # Update status
    schedule.status = status
    db.session.commit()
    
    return jsonify({
        'message': f'Student status updated to {status}',
        'student': {
            **student.to_dict(),
            'email': schedule.email,
            'examTime': schedule.exam_time,
            'examCenter': schedule.exam_center,
            'tokenId': schedule.token_id,
            'status': schedule.status
        }
    }), 200

@app.route('/admin/queue')
def admin_queue():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    return render_template('admin/queue.html')

@app.route('/api/export-students')
def export_students():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    center = request.args.get('center', 'all')
    time_slot = request.args.get('timeSlot', 'all')
    level = request.args.get('level', 'all')
    
    query = db.session.query(ExamSchedule, Student).join(Student)
    
    if center != 'all':
        query = query.filter(ExamSchedule.exam_center == center)
    
    if time_slot != 'all':
        query = query.filter(ExamSchedule.exam_time == time_slot)
    
    if level != 'all':
        query = query.filter(Student.level == level)
    
    results = query.all()
    
    # Create a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Matric Number', 'Full Name', 'Level', 'Department', 'Email', 'Exam Time', 'Exam Center', 'Token ID', 'Status'])
    
    # Write data
    for schedule, student in results:
        writer.writerow([
            student.matric_number,
            student.full_name,
            student.level,
            student.department,
            schedule.email,
            schedule.exam_time,
            schedule.exam_center,
            schedule.token_id,
            schedule.status
        ])
    
    # Prepare response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='scheduled_students.csv'
    )

# Initialize database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
