from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_mail import Mail, Message
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import random
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta
from bson import ObjectId
import json
import pandas as pd
import numpy as np

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        if isinstance(obj, (pd.Timestamp,)):
            return obj.isoformat()
        return super().default(obj)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = 'aviation_corp_secret_key_2025'

# Upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Flask-Mail configuration for Gmail SMTP
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'khaldudxb@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your_app_password_here')  # Set via environment variable
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'khaldudxb@gmail.com')

mail = Mail(app)

# Helper function to send emails
def send_email(subject, recipients, body, html=None):
    msg = Message(subject, recipients=recipients, body=body, html=html)
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

# MongoDB connection
client = MongoClient(
    "mongodb+srv://khaldudxb_db_user:5zWzdlnZYrOJnXLe@mongodbcluster.clyqmaj.mongodb.net/",
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000
)
db = client["Aviation"]
aviation_data = db["Aviation_Data"]
contact_messages = db["Contact_Messages"]
employees = db["Employees"]

# Seed sample employee data if not present
def seed_employees(count=100):
    existing = employees.count_documents({})
    if existing == count:
        return
    if existing > 0:
        employees.delete_many({})

    first_names = [
        "Alex", "Jordan", "Taylor", "Morgan", "Riley", "Casey", "Jamie", "Cameron", "Drew", "Reese",
        "Avery", "Quinn", "Hayden", "Rowan", "Parker", "Sydney", "Payton", "Blake", "Kendall", "Harper"
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
        "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"
    ]
    designations = [
        "Pilot", "Co-Pilot", "Flight Attendant", "Maintenance Engineer", "Operations Manager", "Ground Support",
        "Air Traffic Controller", "Avionics Technician", "Safety Officer", "Flight Dispatcher"
    ]
    genders = ["Male", "Female"]

    used_names = set()
    base_date = datetime.utcnow() - timedelta(days=365 * 5)

    new_employees = []
    while len(new_employees) < count:
        first = random.choice(first_names)
        last = random.choice(last_names)
        full = f"{first} {last}"
        if full in used_names:
            continue
        used_names.add(full)

        age = random.randint(23, 60)
        doj = base_date + timedelta(days=random.randint(30, 365 * 5))
        gender = random.choice(genders)
        designation = random.choice(designations)

        new_employees.append({
            "name": full,
            "designation": designation,
            "gender": gender,
            "age": age,
            "date_of_joining": doj,
        })

    employees.insert_many(new_employees)

# Create a default admin user and seed employees (skip if DB unreachable)
try:
    if not aviation_data.find_one({"username": "admin"}):
        aviation_data.insert_one({
            "username": "admin",
            "email": "admin@aviationcorp.com",
            "password": generate_password_hash("admin123")
        })
    seed_employees()
except Exception as e:
    print(f"Warning: Could not connect to MongoDB on startup: {e}")
@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        contact_messages.insert_one({
            "name": name,
            "email": email,
            "message": message,
            "submitted_at": datetime.utcnow(),
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get('User-Agent'),
            "status": "unread",  # unread, read, responded
            "email_sent": True
        })

        # Send email notification
        email_body = f"""
New contact form submission received:

Name: {name}
Email: {email}
Message: {message}

Submitted at: {datetime.utcnow()}
"""
        if send_email('New Contact Form Submission - Aviation Corp', ['khaldudxb@gmail.com'], email_body):
            flash('Message sent successfully! We will get back to you soon.', 'success')
        else:
            flash('Message sent successfully, but there was an issue with email notification.', 'warning')

        return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Find user in database
        user = aviation_data.find_one({"username": username})

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash('Login successful! Welcome back.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/login-as-admin')
def login_as_admin():
    session.pop('username', None)
    flash('Please enter admin credentials to log in.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user already exists
        existing_user = aviation_data.find_one({"username": username})
        if existing_user:
            flash('Username already exists. Please choose another.', 'error')
            return redirect(url_for('register'))

        existing_email = aviation_data.find_one({"email": email})
        if existing_email:
            flash('Email already registered. Please login instead.', 'error')
            return redirect(url_for('register'))

        # Hash password and save to database
        hashed_password = generate_password_hash(password)
        aviation_data.insert_one({
            "username": username,
            "email": email,
            "password": hashed_password
        })

        # Send welcome email
        welcome_body = f"""
Welcome to Aviation Corp, {username}!

Your account has been created successfully.

You can now login and access your dashboard.

Best regards,
Aviation Corp Team
"""
        send_email('Welcome to Aviation Corp!', [email], welcome_body)

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash('Please login to access the dashboard.', 'error')
        return redirect(url_for('login'))

    # Load employees for the dashboard table
    employee_list = list(employees.find({}, {"_id": 0}).sort('name', 1))
    
    # Calculate tenure for each employee
    current_date = datetime.now()
    for emp in employee_list:
        tenure = relativedelta(current_date, emp['date_of_joining'])
        emp['tenure'] = f"{tenure.years} years, {tenure.months} months"
        emp['tenure_months'] = (tenure.years * 12) + tenure.months
        emp['year_joined'] = emp['date_of_joining'].year

    return render_template(
        'dashboard.html',
        username=session['username'],
        is_dashboard=True,
        employees=employee_list
    )

@app.route('/admin/contact-messages')
def admin_contact_messages():
    if 'username' not in session:
        flash('Please login to access admin area.', 'error')
        return redirect(url_for('login'))
    
    # Get all contact messages, sorted by newest first
    messages = list(contact_messages.find({}, {"_id": 0}).sort('submitted_at', -1))
    return render_template('admin_contact.html', messages=messages)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'username' not in session:
        flash('Please login to access the upload page.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('upload'))

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('upload'))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash(f'File "{filename}" uploaded successfully!', 'success')
            return redirect(url_for('upload'))
        else:
            flash('File type not allowed.', 'error')
            return redirect(url_for('upload'))

    # List already uploaded files
    uploaded_files = []
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f)
        if os.path.isfile(filepath):
            uploaded_files.append({
                'name': f,
                'size': os.path.getsize(filepath),
                'uploaded_at': datetime.fromtimestamp(os.path.getmtime(filepath))
            })
    uploaded_files.sort(key=lambda x: x['uploaded_at'], reverse=True)

    return render_template('upload.html', uploaded_files=uploaded_files)

@app.route('/delete-file/<filename>', methods=['POST'])
def delete_file(filename):
    if 'username' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))

    safe_filename = secure_filename(filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    if os.path.isfile(filepath):
        os.remove(filepath)
        flash(f'File "{safe_filename}" has been removed.', 'success')
    else:
        flash('File not found.', 'error')
    return redirect(url_for('upload'))

@app.route('/view-data/<filename>')
def view_data(filename):
    if 'username' not in session:
        flash('Please login to access data viewer.', 'error')
        return redirect(url_for('login'))

    safe_filename = secure_filename(filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    if not os.path.isfile(filepath):
        flash('File not found.', 'error')
        return redirect(url_for('upload'))

    ext = safe_filename.rsplit('.', 1)[1].lower()
    try:
        if ext == 'csv':
            for encoding in ('utf-8', 'latin-1', 'cp1252'):
                try:
                    df = pd.read_csv(filepath, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                df = pd.read_csv(filepath, encoding='latin-1', errors='replace')
        elif ext in ('xls', 'xlsx'):
            df = pd.read_excel(filepath)
        else:
            flash('Only CSV and Excel files can be viewed as data.', 'error')
            return redirect(url_for('upload'))
    except Exception as e:
        flash(f'Error reading file: {e}', 'error')
        return redirect(url_for('upload'))

    # Try to convert string columns that look numeric or date-like
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_datetime64_any_dtype(df[col]):
            # Try numeric conversion first
            numeric_attempt = pd.to_numeric(df[col], errors='coerce')
            non_null_orig = df[col].dropna().shape[0]
            non_null_numeric = numeric_attempt.dropna().shape[0]
            if non_null_orig > 0 and non_null_numeric / non_null_orig > 0.5:
                df[col] = numeric_attempt
                continue
            # Try date conversion
            try:
                date_attempt = pd.to_datetime(df[col], format='mixed', dayfirst=True, errors='coerce')
                non_null_dates = date_attempt.dropna().shape[0]
                if non_null_orig > 0 and non_null_dates / non_null_orig > 0.5:
                    df[col] = date_attempt
            except Exception:
                pass

    # Detect date columns and numeric columns
    date_columns = []
    numeric_columns = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            date_columns.append(col)
        elif pd.api.types.is_numeric_dtype(df[col]):
            numeric_columns.append(col)

    # Convert table data to list of dicts for template
    # Replace NaN/NaT with empty string and convert all values to JSON-safe types
    df_safe = df.copy()
    for col in df_safe.columns:
        if pd.api.types.is_datetime64_any_dtype(df_safe[col]):
            df_safe[col] = df_safe[col].dt.strftime('%Y-%m-%d').fillna('')
        elif pd.api.types.is_numeric_dtype(df_safe[col]):
            df_safe[col] = df_safe[col].fillna(0)
        else:
            df_safe[col] = df_safe[col].fillna('').astype(str)
    table_data = df_safe.to_dict(orient='records')
    columns = df_safe.columns.tolist()

    # Prepare chart data: group by month for each date column
    chart_datasets = {}
    for dcol in date_columns:
        try:
            dates = pd.to_datetime(df[dcol], format='mixed', dayfirst=False, errors='coerce')
            temp = df.copy()
            temp['_month'] = dates.dt.to_period('M').astype(str)
            for ncol in numeric_columns:
                grouped = temp.dropna(subset=[ncol]).groupby('_month')[ncol].sum().reset_index()
                grouped = grouped.sort_values('_month')
                key = f"{dcol} | {ncol}"
                chart_datasets[key] = {
                    'labels': grouped['_month'].tolist(),
                    'values': grouped[ncol].tolist(),
                    'date_col': dcol,
                    'value_col': ncol
                }
        except Exception:
            continue

    # Get all string/category columns for row filtering
    filter_columns = []
    for col in columns:
        if col not in numeric_columns and col not in date_columns:
            unique_vals = df[col].dropna().unique().tolist()
            if 1 < len(unique_vals) <= 50:
                filter_columns.append({'name': col, 'values': sorted([str(v) for v in unique_vals])})

    return render_template(
        'view_data.html',
        filename=safe_filename,
        columns=columns,
        table_data=table_data,
        raw_json=json.dumps(table_data, cls=NumpyEncoder),
        chart_datasets=json.dumps(chart_datasets, cls=NumpyEncoder),
        date_columns=date_columns,
        numeric_columns=numeric_columns,
        filter_columns=filter_columns
    )

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
