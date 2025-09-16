from flask import Flask, request, render_template, redirect, url_for, session, flash,jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from concurrent.futures import ThreadPoolExecutor
import threading
import mysql.connector
from mysql.connector import Error
from config import Config
from matplotlib.figure import Figure
import io
import base64
from werkzeug.utils import secure_filename
import os
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY  # Use secret key from Config
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'jpg', 'png'}

# Thread pool executor for multithreading
executor = ThreadPoolExecutor(max_workers=5)
lock = threading.Lock()

# Helper function to get database connection
def get_db_connection():
    return Config.get_db_connection()

# Helper function to check if user is logged in
def is_logged_in():
    return 'user_id' in session

# Custom exception for employee operations
class EmployeeException(Exception):
    pass

# Subject/Observer pattern implementation
class Subject:
    def __init__(self):
        self._observers = []

    def register_observer(self, observer):
        self._observers.append(observer)

    def notify_observers(self, message):
        for observer in self._observers:
            observer.update(message)

class Observer:
    def update(self, message):
        raise NotImplementedError

# Logger class as Observer
class EmployeeLogger(Observer):
    def update(self, message):
        print(f"Log: {message}")

# Factory pattern to create Employee instances
class EmployeeFactory:
    def create_employee(self, id, name, email, year_of_birth, qualification, salary, job_title, date_of_joining, department, status):
        # Convert id to integer if it's a string
        if isinstance(id, str):
            try:
                id = int(id)
            except ValueError:
                raise EmployeeException("ID must be an integer.")

        # Check that ID is a positive integer
        if id <= 0:
            raise EmployeeException("Invalid ID. ID must be a positive integer.")

        # Validate email
        if not email or "@" not in email:
            raise EmployeeException("Invalid email address.")
        
        # Validate year_of_birth
        if not isinstance(year_of_birth, int) or year_of_birth < 1900 or year_of_birth > 2100:
            raise EmployeeException("Invalid year of birth.")
        
        # Validate salary
        if not isinstance(salary, (int, float)) or salary < 0:
            raise EmployeeException("Salary cannot be negative.")
        
        # Create and return Employee instance
        return Employee(id, name, email, year_of_birth, qualification, salary, job_title, date_of_joining, department, status)

# Employee model class
class Employee:
    def __init__(self, id, name, email, year_of_birth, qualification, salary, job_title, date_of_joining, department, status):
        self.id = id
        self.name = name
        self.email = email
        self.year_of_birth = year_of_birth
        self.qualification = qualification
        self.salary = salary
        self.job_title = job_title
        self.date_of_joining = date_of_joining
        self.department = department
        self.status = status

    def __str__(self):
        return f"ID: {self.id}, Name: {self.name}, Email: {self.email}, Year: {self.year_of_birth}, Department: {self.department}, Status: {self.status}"

# EmployeeList with observer pattern support
class EmployeeList(Subject):
    def __init__(self):
        super().__init__()

    def add_employee(self, employee):
        with lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(""" 
                INSERT INTO employees (id, name, email, year_of_birth, qualification, salary, job_title, date_of_joining, department, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (employee.id, employee.name, employee.email, employee.year_of_birth, employee.qualification, employee.salary, employee.job_title, employee.date_of_joining, employee.department, employee.status))
            conn.commit()
            cursor.close()
            conn.close()
            self.notify_observers(f"Added employee: {employee.name}")

    def update_employee(self, id, name, email, year_of_birth, qualification, salary, job_title, date_of_joining, department, status):
        with lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(""" 
                UPDATE employees
                SET name = %s, email = %s, year_of_birth = %s, qualification = %s, salary = %s, job_title = %s, date_of_joining = %s, department = %s, status = %s
                WHERE id = %s
            """, (name, email, year_of_birth, qualification, salary, job_title, date_of_joining, department, status, id))
            conn.commit()
            cursor.close()
            conn.close()
            self.notify_observers(f"Updated employee with ID: {id}")

    def delete_employee(self, id):
        with lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM employees WHERE id = %s", (id,))
            conn.commit()
            cursor.close()
            conn.close()
            self.notify_observers(f"Deleted employee with ID: {id}")

    def get_all_employees(self):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM employees")
        employees = cursor.fetchall()
        cursor.close()
        conn.close()
        return employees

    def get_employee_by_id(self, id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM employees WHERE id = %s", (id,))
        employee = cursor.fetchone()
        cursor.close()
        conn.close()
        return employee

    def get_employee_count(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM employees")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count

    def get_recent_hires(self):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(""" 
            SELECT name, date_of_joining
            FROM employees
            ORDER BY date_of_joining DESC
            LIMIT 5
        """)
        recent_hires = cursor.fetchall()
        cursor.close()
        conn.close()
        return recent_hires

    def get_upcoming_anniversaries(self):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(""" 
            SELECT name, DATE_FORMAT(date_of_joining, '%Y-%m-%d') AS joining_date
            FROM employees
            WHERE DATE_ADD(date_of_joining, INTERVAL YEAR(CURDATE()) - YEAR(date_of_joining) YEAR) BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 1 MONTH)
        """)
        anniversaries = cursor.fetchall()
        cursor.close()
        conn.close()
        return anniversaries

# Initialize the employee logger and list
employee_list = EmployeeList()
employee_factory = EmployeeFactory()
logger = EmployeeLogger()
employee_list.register_observer(logger)

# Routes

# Home Page (Only accessible if logged in)
@app.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('login'))

    employee_count = employee_list.get_employee_count()
    recent_hires = employee_list.get_recent_hires()
    upcoming_anniversaries = employee_list.get_upcoming_anniversaries()

    return render_template('index.html',
                           employee_count=employee_count,
                           recent_hires=recent_hires,
                           upcoming_anniversaries=upcoming_anniversaries)

# User Registration Route (Sign Up)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not name or not email or not password:
            flash('Please fill all fields.', 'error')
            return redirect(url_for('signup'))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the user already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user:
            flash('User already exists. Please log in.', 'error')
            return redirect(url_for('login'))

        # Hash the password for security
        hashed_password = generate_password_hash(password)

        # Insert the new user into the database
        cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
        conn.commit()

        cursor.close()
        conn.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

# User Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):  # Assuming password is the 4th column
            session['user_id'] = user[0]
            flash('Login successful!', 'success')
            return redirect(url_for('index'))

        flash('Invalid credentials. Please try again.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')

# Add Employee Route
@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        id = request.form.get('id')
        name = request.form.get('name')
        email = request.form.get('email')
        year_of_birth = int(request.form.get('year_of_birth'))
        qualification = request.form.get('qualification')
        salary = float(request.form.get('salary'))
        job_title = request.form.get('job_title')
        date_of_joining = request.form.get('date_of_joining')
        department = request.form.get('department')
        status = request.form.get('status')

        errors = []

        # Validate Name
        if any(char.isdigit() for char in name):
            errors.append("Name cannot contain numbers.")

        # Validate Email
        if not email or "@" not in email:
            errors.append("Invalid email address.")

        # Validate Year of Birth
        if year_of_birth < 1900 or year_of_birth > 2100:
            errors.append("Invalid year of birth.")

        # Validate Salary
        if salary <= 0:
            errors.append("Salary must be a positive number.")

        if errors:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('add_employee'))

        try:
            employee = employee_factory.create_employee(id, name, email, year_of_birth, qualification, salary, job_title, date_of_joining, department, status)
            employee_list.add_employee(employee)
            flash('Employee added successfully!', 'success')
        except EmployeeException as e:
            flash(str(e), 'error')

        return redirect(url_for('index'))

    return render_template('add_employee.html')

# View Employee Route
@app.route('/employee/<int:id>', methods=['GET', 'POST'])
def employee(id):
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        year_of_birth = int(request.form.get('year_of_birth'))
        qualification = request.form.get('qualification')
        salary = float(request.form.get('salary'))
        job_title = request.form.get('job_title')
        date_of_joining = request.form.get('date_of_joining')
        department = request.form.get('department')
        status = request.form.get('status')

        try:
            employee_list.update_employee(id, name, email, year_of_birth, qualification, salary, job_title, date_of_joining, department, status)
            flash('Employee updated successfully!', 'success')
        except EmployeeException as e:
            flash(str(e), 'error')

        return redirect(url_for('index'))

    employee = employee_list.get_employee_by_id(id)
    if not employee:
        flash('Employee not found.', 'error')
        return redirect(url_for('index'))

    return render_template('profile_employee.html', employee=employee)

# Delete Employee Route
@app.route('/delete_employee/<int:id>', methods=['POST'])
def delete_employee(id):
    try:
        employee_list.delete_employee(id)
        flash('Employee deleted successfully!', 'success')
    except EmployeeException as e:
        flash(str(e), 'error')

    return redirect(url_for('index'))

# Logout Route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/list_employees')
def list_employees():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, name, email, job_title,department, status FROM employees")
    employees = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('list_employees.html', employees=employees)

@app.route('/employee/edit/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    employee = employee_list.get_employee_by_id(id)
    if not employee:
        flash('Employee not found.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        year_of_birth = int(request.form.get('year_of_birth'))
        qualification = request.form.get('qualification')
        salary = float(request.form.get('salary'))
        job_title = request.form.get('job_title')
        date_of_joining = request.form.get('date_of_joining')
        department = request.form.get('department')
        status = request.form.get('status')

        try:
            employee_list.update_employee(id, name, email, year_of_birth, qualification, salary, job_title, date_of_joining, department, status)
            flash('Employee updated successfully!', 'success')
        except EmployeeException as e:
            flash(str(e), 'error')

        return redirect(url_for('index'))

    return render_template('edit_employee.html', employee=employee)

@app.route('/dashboard_data')
def dashboard_data():
    if not is_logged_in():
        return jsonify({'error': 'User not logged in'}), 401

    try:
        employee_count = employee_list.get_employee_count()
        recent_hires = employee_list.get_recent_hires()
        upcoming_anniversaries = employee_list.get_upcoming_anniversaries()
        
        # Format data for JSON response
        data = {
            'employee_count': employee_count,
            'recent_hires': recent_hires,
            'upcoming_anniversaries': upcoming_anniversaries
        }
        return jsonify(data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/chart')
def chart():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT department, COUNT(*) as count FROM employees GROUP BY department")
    data = cursor.fetchall()
    cursor.close()
    conn.close()

    departments = [row['department'] for row in data]
    counts = [row['count'] for row in data]

    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.bar(departments, counts)
    ax.set_xlabel('Department')
    ax.set_ylabel('Count')
    ax.set_title('Employee Count by Department')

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    img_str = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    return render_template('charts.html', chart_img=img_str)

# Statistics Endpoint
@app.route('/statistics')
def statistics():
    total_employees = employee_list.get_employee_count()
    recent_hires = employee_list.get_recent_hires()
    upcoming_anniversaries = employee_list.get_upcoming_anniversaries()

    return render_template('statistics.html',
                           total_employees=total_employees,
                           recent_hires=recent_hires,
                           upcoming_anniversaries=upcoming_anniversaries)


@app.route('/add_inventory', methods=['GET', 'POST'])
def add_inventory():
    if request.method == 'POST':
        name = request.form['name']
        quantity = int(request.form['quantity'])
        description = request.form.get('description', '')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO inventory (name, quantity, description) VALUES (%s, %s, %s)",
                       (name, quantity, description))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('inventory_list'))
    
    return render_template('add_inventory.html')

@app.route('/inventory_list')
def inventory_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM inventory")
    inventory_items = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('inventory_list.html', inventory_items=inventory_items)

@app.route('/assign_inventory', methods=['GET', 'POST'])
def assign_inventory():
    if request.method == 'POST':
        employee_id = int(request.form['employee_id'])
        inventory_id = int(request.form['inventory_id'])
        assigned_date = request.form['assigned_date']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO employee_inventory (employee_id, inventory_id, assigned_date) VALUES (%s, %s, %s)",
                       (employee_id, inventory_id, assigned_date))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('employee_inventory_list'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM employees")
    employees = cursor.fetchall()
    cursor.execute("SELECT id, name FROM inventory")
    inventory_items = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('assign_inventory.html', employees=employees, inventory_items=inventory_items)

@app.route('/employee_inventory_list')
def employee_inventory_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.name AS employee_name, i.name AS inventory_name, ei.assigned_date
        FROM employee_inventory ei
        JOIN employees e ON ei.employee_id = e.id
        JOIN inventory i ON ei.inventory_id = i.id
    """)
    assignments = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('employee_inventory_list.html', assignments=assignments)

@app.route('/inventory')
def inventory():
    return render_template('inventory.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_employees():
    # Replace this with actual database query
    return [
        {'id': 1, 'name': 'Ali'},
        {'id': 2, 'name': 'Ahmed'},
    ]

def get_documents():
    # Replace this with actual database query
    return [
        [1, 'Contract ABC', 'Contract'],
        [2, 'Certificate XYZ', 'Certificate'],
    ]

@app.route('/document_storage', methods=['GET', 'POST'])
def document_storage():
    if request.method == 'POST':
        document_name = request.form['document_name']
        document_type = request.form['document_type']
        employee_id = request.form['employee_id']
        file = request.files['file']
        
        # Validate and save the uploaded file
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
        
        # Process and store the document details
        # Add your logic to save document details to the database
        
        # Redirect to the same page or another page upon successful upload
        return redirect(url_for('document_storage'))

    # Fetch employee and document data
    employees = get_employees()
    documents = get_documents()

    return render_template('document_storage.html', employees=employees, documents=documents)



@app.route('/document_sharing', methods=['GET', 'POST'])
def document_sharing():
    if request.method == 'POST':
        document_id = request.form['document_id']
        recipient = request.form.getlist('recipient')
        permissions = request.form['permissions']
        
        # Process sharing logic here

        return redirect(url_for('document_sharing'))

    # Fetch documents and recipients for rendering
    documents = []  # Fetch from database
    recipients = []  # Fetch from database
    return render_template('document_sharing.html', documents=documents, recipients=recipients)

@app.route('/compliance')
def compliance():
    # Fetch compliance data and audit logs for rendering
    compliance_data = []  # Fetch from database
    audit_logs = []  # Fetch from database
    return render_template('compliance.html', compliance_data=compliance_data, audit_logs=audit_logs)

from flask import render_template

@app.route('/document_management')
def document_management():
    return render_template('document_management.html')


if __name__ == '__main__':
    app.run(debug=True)
