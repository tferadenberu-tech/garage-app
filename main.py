from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'steely_rmi_garage_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///garage_dashboard.db'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# የተጠቃሚ ሞዴል (Login System)
class User(db.Model, LoginManager = None):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='Technician')

# የጥገና መዝገብ ሞዴል
class MaintenanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    work_order_no = db.Column(db.String(50), nullable=True)
    vehicle_or_machine = db.Column(db.String(100), nullable=False)
    vehicle_type = db.Column(db.String(100), nullable=True)
    maintenance_type = db.Column(db.String(50), nullable=False)
    current_km = db.Column(db.Float, default=0.0)
    technicians = db.Column(db.String(150), nullable=True)
    start_date = db.Column(db.String(50), nullable=True)
    end_date = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# አፕሊኬሽኑ ሲጀመር ዳታቤዝ እና ነባሪ አድሚን መፍጠር
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
        admin_user = User(username='admin', password=hashed_pw, role='Admin')
        db.session.add(admin_user)
        db.session.commit()

# መግቢያ ገጽ (Login Route)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('የተሳሳተ መግቢያ ስም ወይም የይለፍ ቃል።', 'danger')
            
    return render_template('login.html')

# መውጫ (Logout Route)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ዋናው ዳሽቦርድ
@app.route('/')
@login_required
def dashboard():
    records = MaintenanceRecord.query.all()
    return render_template('dashboard.html', records=records)

# አዲስ መዝገብ መጨመሪያ
@app.route('/add', methods=['POST'])
@login_required
def add_record():
    new_record = MaintenanceRecord(
        work_order_no=request.form.get('work_order_no'),
        vehicle_or_machine=request.form.get('vehicle_or_machine'),
        vehicle_type=request.form.get('vehicle_type'),
        maintenance_type=request.form.get('maintenance_type'),
        current_km=float(request.form.get('current_km', 0)),
        technicians=request.form.get('technicians'),
        start_date=request.form.get('start_date'),
        end_date=request.form.get('end_date'),
        description=request.form.get('description')
    )
    db.session.add(new_record)
    db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
