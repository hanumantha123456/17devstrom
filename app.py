from flask import Flask, render_template, request, redirect, session, url_for, send_file
import csv, os, uuid
from datetime import datetime
from twilio.rest import Client
import smtplib
from email.message import EmailMessage
from io import StringIO

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# File paths
USERS_FILE = 'users.csv'
COMPLAINTS_FILE = 'complaints.csv'

# Twilio Configuration
TWILIO_SID = 'AC364e2b135409c4067c7fe9f76bb73273'
TWILIO_AUTH_TOKEN = '12795d9603c20884df2fac9eae8b1048'
TWILIO_NUMBER = '+12184032878'

# Email Configuration
EMAIL_ADDRESS = 'hanumantharaya1177@gmail.com'
EMAIL_PASSWORD = 'mexxtplxucttgftp'

# Helper Functions
def send_sms(to_number, message):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_=TWILIO_NUMBER, to=to_number)
    except Exception as e:
        print("SMS sending failed:", e)

def send_email(to_email, subject, content):
    try:
        msg = EmailMessage()
        msg.set_content(content)
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        print("Email sending failed:", e)

def read_csv(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def write_csv(file_path, data, fieldnames):
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def get_user_phone(username):
    users = read_csv(USERS_FILE)
    for user in users:
        if user['username'] == username:
            return user['phone']
    return None

def get_user_email(username):
    users = read_csv(USERS_FILE)
    for user in users:
        if user['username'] == username:
            return user['email']
    return None

def generate_ticket_id():
    return str(uuid.uuid4())[:8]

def save_complaint_to_csv(complaint):
    complaints = read_csv(COMPLAINTS_FILE)
    complaints.append(complaint)
    write_csv(COMPLAINTS_FILE, complaints, ['ticket ID', 'customer', 'category', 'message', 'status', 'timestamp', 'assigned_To'])

# Routes
@app.route('/')
def home():
    return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form['phone']
        users = read_csv(USERS_FILE)
        if any(u['username'] == username for u in users):
            return "Username already exists!"
        users.append({'username': username, 'password': password, 'email': email, 'phone': phone, 'is_admin': 'no'})
        write_csv(USERS_FILE, users, ['username', 'password', 'email', 'phone', 'is_admin'])
        return redirect('/login')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin1' and password == 'admin1234':
            session['username'] = username
            session['is_admin'] = 'yes'
            return redirect('/admin/dashboard')
        users = read_csv(USERS_FILE)
        user = next((u for u in users if u['username'] == username and u['password'] == password), None)
        if user:
            session['username'] = username
            session['is_admin'] = user['is_admin']
            return redirect('/dashboard')
        else:
            return "Invalid credentials!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/login')
    if session.get('is_admin') == 'yes':
        return redirect('/admin/dashboard')
    username = session['username']
    complaints = read_csv(COMPLAINTS_FILE)
    user_complaints = [c for c in complaints if c['customer'] == username]
    return render_template('dashboard.html', username=username, complaints=user_complaints)

@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'username' not in session or session.get('is_admin') != 'yes':
        return redirect('/login')
    
    # Get complaints from CSV file
    complaints = read_csv(COMPLAINTS_FILE)
    
    # Get filter options from the query parameters
    selected_category = request.args.get('category', '').lower()  # Filter by category
    selected_status = request.args.get('status', '')  # Filter by status
    
    # Apply filtering based on category and status
    filtered_complaints = [
        c for c in complaints
        if (not selected_category or c['category'].lower() == selected_category)
        and (not selected_status or c['status'] == selected_status)
    ]
    
    return render_template('admin_dashboard.html',
                           complaints=filtered_complaints,
                           selected_category=selected_category,
                           selected_status=selected_status)

@app.route('/submit-form', methods=['GET', 'POST'])
def submit_form():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    if request.method == 'POST':
        category = request.form['category']
        message = request.form['message']
        ticket_id = generate_ticket_id()
        status = 'Submitted'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        assigned_To = {
            'payment': 'Billing Department',
            'account access': 'Account Support Team',
            'refund': 'Finance Team',
            'technical': 'Technical Support'
        }.get(category.lower(), 'General Support')
        complaint = {
            'timestamp': timestamp,
            'ticket ID': ticket_id,
            'category': category,
            'customer': username,
            'assigned_To': assigned_To,
            'message': message,
            'status': status
        }
        save_complaint_to_csv(complaint)
        phone = get_user_phone(username)
        email = get_user_email(username)
        if phone:
            send_sms(phone, f"Hi {username}, your complaint ({ticket_id}) has been submitted. Status: {status}.")
        if email:
            send_email(email, f"Complaint Submitted: {ticket_id}",
                       f"Dear {username},\n\nYour complaint has been registered.\n\nTicket ID: {ticket_id}\nCategory: {category}\nMessage: {message}\nStatus: {status}\n\n- Support Team")
        return redirect('/dashboard')
    return render_template('submit-form.html')

@app.route('/admin/update-status/<ticket_id>', methods=['GET', 'POST'])
def update_complaint_status(ticket_id):
    if 'username' not in session or session.get('is_admin') != 'yes':
        return redirect('/login')
    complaints = read_csv(COMPLAINTS_FILE)
    complaint = next((c for c in complaints if c['ticket ID'] == ticket_id), None)
    if not complaint:
        return "Complaint not found!"
    if request.method == 'POST':
        complaint['status'] = request.form['status']
        write_csv(COMPLAINTS_FILE, complaints, ['ticket ID', 'customer', 'category', 'message', 'status', 'timestamp', 'assigned_To'])
        return redirect('/admin/dashboard')
    return render_template('update_status.html', complaint=complaint)

@app.route('/export_tickets')
def export_tickets():
    complaints = read_csv(COMPLAINTS_FILE)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=['ticket ID', 'customer', 'category', 'message', 'status', 'timestamp', 'assigned_To'])
    writer.writeheader()
    writer.writerows(complaints)
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='complaints.csv')

if __name__ == '__main__':
    app.run(debug=True)
