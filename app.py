from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import requests

app = Flask(__name__)
app.secret_key = 'vtu_secret_key_2024'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    phone = db.Column(db.String(20))
    is_admin = db.Column(db.Boolean, default=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(50))
    amount = db.Column(db.Float)
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Success')
    date = db.Column(db.DateTime, default=datetime.utcnow)

from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return "Access denied: Admins only", 403
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.session.execute(
            db.select(User).filter_by(username=username)
        ).scalar_one_or_none()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        phone = request.form['phone']
        existing = User.query.filter_by(username=username).first()
        if existing:
            return render_template('register.html', error='Username already exists')
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            phone=phone
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/signup', methods=['GET', 'POST'])
@login_required
@admin_required
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = True if request.form.get('role') == 'admin' else False

        existing = db.session.execute(
            db.select(User).filter_by(username=username)
        ).scalar_one_or_none()
        if existing:
            return render_template('signup.html', error='Username already exists')

        new_user = User(
            username=username,
            password=generate_password_hash(password),
            is_admin=is_admin
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user = db.session.get(User, session['user_id'])
    transactions = Transaction.query.filter_by(
        user_id=session['user_id']
    ).order_by(Transaction.date.desc()).limit(5).all()
    return render_template('dashboard.html',
                         user=user,
                         transactions=transactions)

@app.route('/buy-airtime', methods=['GET', 'POST'])
@login_required
def buy_airtime():
    user = db.session.get(User, session['user_id'])
    if request.method == 'POST':
        phone = request.form['phone']
        amount = float(request.form['amount'])
        network = request.form['network']
        if user.balance < amount:
            return render_template('airtime.html',
                                 user=user,
                                 error='Insufficient balance!')
        user.balance -= amount
        transaction = Transaction(
            user_id=user.id,
            type=f'{network} Airtime',
            amount=amount,
            phone=phone,
            status='Success'
        )
        db.session.add(transaction)
        db.session.commit()
        return render_template('airtime.html',
                             user=user,
                             success=f'Airtime of ₦{amount} sent to {phone}!')
    return render_template('airtime.html', user=user)

@app.route('/buy-data', methods=['GET', 'POST'])
@login_required
def buy_data():
    user = db.session.get(User, session['user_id'])
    data_plans = {
        'MTN': ['500MB - ₦200', '1GB - ₦350', '2GB - ₦700'],
        'Airtel': ['500MB - ₦200', '1GB - ₦300', '2GB - ₦600'],
        'Glo': ['500MB - ₦150', '1GB - ₦250', '2GB - ₦500'],
        '9mobile': ['500MB - ₦200', '1GB - ₦300', '2GB - ₦600'],
    }
    if request.method == 'POST':
        phone = request.form['phone']
        amount = float(request.form['amount'])
        network = request.form['network']
        plan = request.form['plan']
        if user.balance < amount:
            return render_template('data.html',
                                 user=user,
                                 data_plans=data_plans,
                                 error='Insufficient balance!')
        user.balance -= amount
        transaction = Transaction(
            user_id=user.id,
            type=f'{network} Data - {plan}',
            amount=amount,
            phone=phone,
            status='Success'
        )
        db.session.add(transaction)
        db.session.commit()
        return render_template('data.html',
                             user=user,
                             data_plans=data_plans,
                             success=f'Data {plan} sent to {phone}!')
    return render_template('data.html', user=user, data_plans=data_plans)

@app.route('/fund-wallet', methods=['GET', 'POST'])
@login_required
def fund_wallet():
    user = db.session.get(User, session['user_id'])
    if request.method == 'POST':
        amount = float(request.form['amount'])
        user.balance += amount
        transaction = Transaction(
            user_id=user.id,
            type='Wallet Funding',
            amount=amount,
            phone=user.phone,
            status='Success'
        )
        db.session.add(transaction)
        db.session.commit()
        return render_template('fund_wallet.html',
                             user=user,
                             success=f'₦{amount} added to your wallet!')
    return render_template('fund_wallet.html', user=user)

@app.route('/transactions')
@login_required
def transactions():
    user = db.session.get(User, session['user_id'])
    all_transactions = Transaction.query.filter_by(
        user_id=session['user_id']
    ).order_by(Transaction.date.desc()).all()
    return render_template('transactions.html',
                         user=user,
                         transactions=all_transactions)

@app.route('/admin')
@login_required
def admin():
    users = User.query.all()
    transactions = Transaction.query.order_by(
        Transaction.date.desc()
    ).all()
    return render_template('admin.html',
                         users=users,
                         transactions=transactions)

@app.route('/weather', methods=['GET', 'POST'])
@login_required
def weather():
    weather_data = None
    if request.method == 'POST':
        city = request.form['city']
        url = f"https://wttr.in/{city}?format=j1"
        response = requests.get(url)
        data = response.json()
        weather_data = {
            'city': city,
            'temp': data['current_condition'][0]['temp_C'],
            'description': data['current_condition'][0]['weatherDesc'][0]['value']
        }
    return render_template('weather.html', weather=weather_data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        admin = db.session.execute(
            db.select(User).filter_by(username='admin')
        ).scalar_one_or_none()
        if not admin:
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                phone='08000000000',
                balance=0.0,
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
