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

# Twilio Configuration (update these)
TWILIO_SID = 'AC364e2b135409c4067c7fe9f76bb73273'
TWILIO_AUTH_TOKEN = '12795d9603c20884df2fac9eae8b1048'
TWILIO_NUMBER = '+12184032878'

# Email Configuration (update with your real Gmail & app password)
EMAIL_ADDRESS = 'hanumantharaya1177@gmail.com'
EMAIL_PASSWORD = 'mexxtplxucttgftp'

def send_sms(to_number, message):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=TWILIO_NUMBER,
            to=to_number
        )
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
    with open(COMPLAINTS_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['ticket ID', 'customer', 'category', 'message', 'status', 'timestamp', 'assigned_To']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(complaints)

# Route for exporting tickets to CSV
@app.route('/export_tickets')
def export_tickets():
    complaints = read_csv(COMPLAINTS_FILE)
    # Create CSV in memory
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=['ticket ID', 'customer', 'category', 'message', 'status', 'timestamp', 'assigned_To'])
    writer.writeheader()
    writer.writerows(complaints)
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, attachment_filename='complaints.csv')

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

        users.append({
            'username': username,
            'password': password,
            'email': email,
            'phone': phone,
            'is_admin': 'no'
        })

        write_csv(USERS_FILE, users, ['username', 'password', 'email', 'phone', 'is_admin'])

        return redirect('/login')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the credentials are for the admin
        if username == 'admin1' and password == 'admin1234':
            session['username'] = username
            session['is_admin'] = 'yes'  # Mark as admin
            return redirect('/admin/dashboard')

        # Otherwise, check if the credentials are for a regular user
        users = read_csv(USERS_FILE)
        user = next((u for u in users if u['username'] == username and u['password'] == password), None)

        if user:
            session['username'] = username
            session['is_admin'] = user['is_admin']  # Store if the user is admin
            if user['is_admin'] == 'yes':
                return redirect('/admin/dashboard')
            else:
                return redirect('/dashboard')
        else:
            return "Invalid credentials!"

    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('username', None)
    session.pop('is_admin', None)  # Clear admin status on logout
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    is_admin = session.get('is_admin', 'no')  # 'yes' or 'no'

    complaints = read_csv(COMPLAINTS_FILE)

    if is_admin == 'yes':
        return redirect('/admin/dashboard')
    
    user_complaints = [c for c in complaints if c['customer'] == username]
    return render_template('dashboard.html', username=username, complaints=user_complaints)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']

    # Read complaints
    complaints = read_csv('complaints.csv')

    # Get current admin's department (optional)
    current_user = next((u for u in read_csv('users.csv') if u['username'] == username), None)
    department = current_user.get('department') if current_user else None

    # Filter by category and status from query params
    selected_category = request.args.get('category', '').lower()
    selected_status = request.args.get('status', '')

    # Apply filters
    filtered_complaints = [
        c for c in complaints
        if (not selected_category or c['category'].lower() == selected_category)
        and (not selected_status or c['status'] == selected_status)
        and (not department or c['assigned_To'].lower() == department.lower())
    ]

    return render_template('dashboard.html',
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

        if category.lower() == 'payment':
            assigned_To = 'Billing Department'
        elif category.lower() == 'account access':
            assigned_To = 'Account Support Team'
        elif category.lower() == 'refund':
            assigned_To = 'Finance Team'
        elif category.lower() == 'technical':
            assigned_To = 'Technical Support'
        else:
            assigned_To = 'General Support'

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

        phone_number = get_user_phone(username)
        email_address = get_user_email(username)

        if phone_number:
            sms_message = f"Hi {username}, your complaint ({ticket_id}) has been submitted. Status: {status}."
            send_sms(phone_number, sms_message)

        if email_address:
            email_subject = f"Complaint Submitted: {ticket_id}"
            email_body = f"""
            Dear {username},

            Your complaint has been registered successfully.

            Ticket ID : {ticket_id}
            Category  : {category}
            Message   : {message}
            Status    : {status}

            We will get back to you shortly.
            - Support Team
            """
            send_email(email_address, email_subject, email_body)

        return redirect('/dashboard')

    return render_template('submit-form.html')

@app.route('/admin/update-status/<ticket_id>', methods=['GET', 'POST'])
def update_complaint_status(ticket_id):
    if 'username' not in session or session.get('is_admin', 'no') != 'yes':
        return redirect('/login')

    complaints = read_csv(COMPLAINTS_FILE)

    # Find the complaint by ticket_id
    complaint = next((c for c in complaints if c['ticket ID'] == ticket_id), None)
    
    if not complaint:
        return "Complaint not found!"

    if request.method == 'POST':
        new_status = request.form['status']
        complaint['status'] = new_status

        write_csv(COMPLAINTS_FILE, complaints, ['ticket ID', 'customer', 'category', 'message', 'status', 'timestamp', 'assigned_To'])

        return redirect('/admin/dashboard')

    return render_template('update_status.html', complaint=complaint)

if __name__ == '__main__':
    app.run(debug=True)
