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

        # Check balance first
        if user.balance < amount:
            return render_template('airtime.html',
                                 user=user,
                                 error='Insufficient balance!')

        # Call VTpass API
        api_key = "7f1cfa18e060f0258d1f0fc78f75917d"
        secret_key = "SK_898d9e1bf7d87caddda7ee14ddc1e368db9207740b2"

        request_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)

        headers = {
            "api-key": api_key,
            "secret-key": secret_key
        }

        payload = {
            "request_id": request_id,
            "serviceID": network.lower(),
            "amount": int(amount),
            "phone": phone
        }

        vtpass_response = requests.post(
            "https://sandbox.vtpass.com/api/pay",
            headers=headers,
            json=payload
        )
        result = vtpass_response.json()
        print(result)

        if result.get('code') == '000':
            # Success — deduct balance
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
                                 success=f'Airtime of ₦{amount} sent to {phone} successfully!')
        else:
            # Failed — don't deduct balance
            return render_template('airtime.html',
                                 user=user,
                                 error=f'Transaction failed: {result.get("response_description")}')

    return render_template('airtime.html', user=user)


@app.route('/buy-data', methods=['GET', 'POST'])
@login_required
def buy_data():
    user = db.session.get(User, session['user_id'])
    
    # VTpass variation codes for data plans
    data_plans = {
    'mtn': [
        {'plan': '100MB - 24hrs', 'code': 'mtn-10mb-100', 'amount': 100},
        {'plan': '200MB - 2 days', 'code': 'mtn-50mb-200', 'amount': 200},
        {'plan': '2.5GB - 2 days', 'code': 'mtn-2-5gb-600', 'amount': 600},
        {'plan': '3GB - 2 days', 'code': 'mtn-3gb-800', 'amount': 800},
        {'plan': '1.5GB - 30 days', 'code': 'mtn-100mb-1000', 'amount': 1000},
        {'plan': '3GB - 30 days', 'code': 'mtn-3gb-1500', 'amount': 1500},
        {'plan': '7GB - 7 days', 'code': 'mtn-7gb-2000', 'amount': 2000},
    ],
    'airtel': [
        {'plan': '500MB - ₦200', 'code': 'airtel-500mb', 'amount': 200},
        {'plan': '1GB - ₦300', 'code': 'airtel-1gb', 'amount': 300},
    ],
    'glo': [
        {'plan': '500MB - ₦150', 'code': 'glo-500mb', 'amount': 150},
        {'plan': '1GB - ₦250', 'code': 'glo-1gb', 'amount': 250},
    ],
    '9mobile': [
        {'plan': '500MB - ₦200', 'code': '9mobile-500mb', 'amount': 200},
        {'plan': '1GB - ₦300', 'code': '9mobile-1gb', 'amount': 300},
    ],
}
    if request.method == 'POST':
        phone = request.form['phone']
        network = request.form['network'].lower()
        variation_code = request.form['variation_code']
        amount = float(request.form['amount'])

        if user.balance < amount:
            return render_template('data.html',
                                 user=user,
                                 data_plans=data_plans,
                                 error='Insufficient balance!')

        # Call VTpass API
        api_key = "7f1cfa18e060f0258d1f0fc78f75917d"
        secret_key = "SK_898d9e1bf7d87caddda7ee14ddc1e368db9207740b2"

        request_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(user.id)

        headers = {
            "api-key": api_key,
            "secret-key": secret_key
        }

        payload = {
            "request_id": request_id,
            "serviceID": f"{network}-data",
            "billersCode": phone,
            "variation_code": variation_code,
            "amount": int(amount),
            "phone": phone
        }
        
        print("Payload:", payload)
        vtpass_response = requests.post(
            "https://sandbox.vtpass.com/api/pay",
            headers=headers,
            json=payload
        )
        result = vtpass_response.json()
        print(result)

        if result.get('code') == '000':
            user.balance -= amount
            transaction = Transaction(
                user_id=user.id,
                type=f'{network.upper()} Data - {variation_code}',
                amount=amount,
                phone=phone,
                status='Success'
            )
            db.session.add(transaction)
            db.session.commit()
            return render_template('data.html',
                                 user=user,
                                 data_plans=data_plans,
                                 success=f'Data sent to {phone} successfully!')
        else:
            return render_template('data.html',
                                 user=user,
                                 data_plans=data_plans,
                                 error=f'Transaction failed: {result.get("response_description")}')

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