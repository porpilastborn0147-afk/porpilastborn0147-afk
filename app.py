from flask import Flask, render_template_string, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import random
import os

# Demo banking Flask app (all balances & transactions are simulated/dummy for demonstration only)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'demo-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank_demo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'


# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # positive for credit, negative for debit
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(255))
    counterparty = db.Column(db.String(120))
    # For demo purpose: type could be 'payment', 'deposit', 'transfer'
    txn_type = db.Column(db.String(50), default='demo')


# Constants
DEMO_START_BALANCE = 2_000_000.00


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Utilities
def format_currency(amount):
    return "${:,.2f}".format(amount)


def compute_demo_balance(user: User):
    # Start from demo starting balance and add all transaction amounts
    total = DEMO_START_BALANCE
    tx_sum = sum(tx.amount for tx in user.transactions)
    return total + tx_sum


def generate_demo_transactions_for_user(user: User, seed=None):
    """
    Populate several simulated historical transactions for a newly registered user.
    These are for demonstration only.
    """
    if seed is not None:
        random.seed(seed)
    # Simple set of merchants and incomes
    merchants = [
        'Acme Grocery', 'Utility Co.', 'Coffee Shop', 'Online Retailer', 'Gym Membership',
        'Streaming Service', 'Rent', 'Payroll', 'Dividend', 'Tax Refund'
    ]
    transactions = []
    # Generate transactions over the past 120 days
    days_back = 120
    num_tx = random.randint(12, 28)
    for i in range(num_tx):
        days_ago = random.randint(1, days_back)
        when = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        kind = random.choice(['debit', 'credit'])
        if kind == 'debit':
            # small to medium expenses
            amt = round(random.uniform(5.0, 1200.0), 2)
            merchant = random.choice(merchants[:7])
            description = f"Payment at {merchant}"
            txn_type = 'payment'
            amount = -amt
        else:
            # income events
            amt = round(random.uniform(500.0, 8000.0), 2)
            merchant = random.choice(['Payroll', 'Dividend', 'Tax Refund', 'Interest'])
            description = f"{merchant} (simulated credit)"
            txn_type = 'deposit'
            amount = amt
        tx = Transaction(user_id=user.id, amount=amount, timestamp=when, description=description, counterparty=merchant, txn_type=txn_type)
        transactions.append(tx)
    # Sort by timestamp ascending so earlier transactions have older dates
    transactions.sort(key=lambda x: x.timestamp)
    db.session.add_all(transactions)
    db.session.commit()


# Templates (rendered inline so this single file is complete)
base_tpl = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Demo Bank - {{ title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
      body {{ padding-top: 70px; }}
      .disclaimer {{ font-size: .9rem; color: #6c757d; }}
      .monospace {{ font-family: monospace; }}
    </style>
  </head>
  <body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary fixed-top">
      <div class="container">
        <a class="navbar-brand" href="{{ url_for('index') }}">Demo Bank</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav" aria-controls="nav" aria-expanded="false" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="nav">
          <ul class="navbar-nav ms-auto">
            {% if current_user.is_authenticated %}
              <li class="nav-item"><a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a></li>
              <li class="nav-item"><a class="nav-link" href="{{ url_for('transfer') }}">Transfer</a></li>
              <li class="nav-item"><a class="nav-link" href="{{ url_for('settings') }}">Account</a></li>
              <li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Logout</a></li>
            {% else %}
              <li class="nav-item"><a class="nav-link" href="{{ url_for('login') }}">Login</a></li>
              <li class="nav-item"><a class="nav-link" href="{{ url_for('register') }}">Register</a></li>
            {% endif %}
          </ul>
        </div>
      </div>
    </nav>

    <main class="container">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          {% for category, message in messages %}
            <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
              {{ message }}
              <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
          {% endfor %}
        {% endif %}
      {% endwith %}
      {% block content %}{% endblock %}
    </main>

    <footer class="text-center mt-5 mb-3">
      <p class="disclaimer">All balances and transactions shown here are simulated and for demonstration purposes only. This application does not represent a real financial institution.</p>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
  </body>
</html>
"""

index_tpl = """
{% extends base %}
{% block content %}
  <div class="row justify-content-center">
    <div class="col-md-8 text-center">
      <h1 class="mb-3">Welcome to Demo Bank</h1>
      <p class="lead">This is a demo banking application built with Flask. All balances and transactions are simulated for demonstration only.</p>
      {% if not current_user.is_authenticated %}
        <p>
          <a href="{{ url_for('register') }}" class="btn btn-success me-2">Register</a>
          <a href="{{ url_for('login') }}" class="btn btn-primary">Login</a>
        </p>
      {% else %}
        <p>
          <a href="{{ url_for('dashboard') }}" class="btn btn-primary">Go to Dashboard</a>
        </p>
      {% endif %}
    </div>
  </div>
{% endblock %}
"""

register_tpl = """
{% extends base %}
{% block content %}
  <div class="row justify-content-center">
    <div class="col-md-6">
      <h2>Register</h2>
      <form method="post" novalidate>
        <div class="mb-3">
          <label for="username" class="form-label">Username</label>
          <input required name="username" id="username" class="form-control" value="{{ request.form.get('username','') }}">
        </div>
        <div class="mb-3">
          <label for="email" class="form-label">Email</label>
          <input required name="email" id="email" type="email" class="form-control" value="{{ request.form.get('email','') }}">
        </div>
        <div class="mb-3">
          <label for="password" class="form-label">Password</label>
          <input required name="password" id="password" type="password" class="form-control">
        </div>
        <button class="btn btn-success" type="submit">Create account</button>
        <a class="btn btn-link" href="{{ url_for('login') }}">Already have an account?</a>
      </form>
      <hr>
      <p class="text-muted small">By registering you will receive a simulated balance of {{ demo_balance }}. This is a demo-only balance and not real money.</p>
    </div>
  </div>
{% endblock %}
"""

login_tpl = """
{% extends base %}
{% block content %}
  <div class="row justify-content-center">
    <div class="col-md-5">
      <h2>Login</h2>
      <form method="post" novalidate>
        <div class="mb-3">
          <label for="username" class="form-label">Username or Email</label>
          <input required name="identity" id="username" class="form-control" value="{{ request.form.get('identity','') }}">
        </div>
        <div class="mb-3">
          <label for="password" class="form-label">Password</label>
          <input required name="password" id="password" type="password" class="form-control">
        </div>
        <button class="btn btn-primary" type="submit">Login</button>
        <a class="btn btn-link" href="{{ url_for('register') }}">Create account</a>
      </form>
    </div>
  </div>
{% endblock %}
"""

dashboard_tpl = """
{% extends base %}
{% block content %}
  <div class="row">
    <div class="col-md-8">
      <h2>Dashboard</h2>
      <p class="lead">Hello, {{ current_user.username }}!</p>

      <div class="card mb-4">
        <div class="card-body">
          <h5 class="card-title">Demo Balance</h5>
          <p class="display-6 monospace">{{ balance }}</p>
          <p class="mb-0 text-muted">Starting demo balance: {{ demo_start }}</p>
          <p class="mt-2"><small class="text-muted">All balances are simulated and for demonstration only.</small></p>
        </div>
      </div>

      <div class="card">
        <div class="card-body">
          <h5 class="card-title">Recent Transactions</h5>
          {% if transactions %}
            <div class="table-responsive">
              <table class="table table-striped">
                <thead><tr><th>Date</th><th>Description</th><th>Counterparty</th><th class="text-end">Amount</th></tr></thead>
                <tbody>
                  {% for t in transactions %}
                    <tr>
                      <td>{{ t.timestamp.strftime('%Y-%m-%d %H:%M') }}</td>
                      <td>{{ t.description }}</td>
                      <td>{{ t.counterparty or '-' }}</td>
                      <td class="text-end {% if t.amount < 0 %}text-danger{% else %}text-success{% endif %}">{{ "{:,.2f}".format(t.amount) | replace('-', '-') | currency_prefix }}</td>
                    </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
            <a href="{{ url_for('transfer') }}" class="btn btn-outline-primary">Make a Demo Transfer</a>
          {% else %}
            <p class="text-muted">No transactions yet.</p>
          {% endif %}
        </div>
      </div>

    </div>

    <div class="col-md-4">
      <div class="card mb-3">
        <div class="card-body">
          <h6>Quick Actions</h6>
          <p><a href="{{ url_for('transfer') }}" class="btn btn-sm btn-primary w-100">Demo Transfer</a></p>
          <p><a href="{{ url_for('settings') }}" class="btn btn-sm btn-secondary w-100">Account Settings</a></p>
        </div>
      </div>

      <div class="card">
        <div class="card-body">
          <h6>About this Demo</h6>
          <p class="small text-muted">This site simulates banking features. Balances, transactions, and transfers are not real and are intended for demonstration and testing only.</p>
        </div>
      </div>
    </div>
  </div>
{% endblock %}
"""

transfer_tpl = """
{% extends base %}
{% block content %}
  <div class="row justify-content-center">
    <div class="col-md-6">
      <h2>Make a Demo Transfer</h2>
      <form method="post" novalidate>
        <div class="mb-3">
          <label for="recipient" class="form-label">Recipient Name</label>
          <input name="recipient" id="recipient" class="form-control" value="{{ request.form.get('recipient','') }}" required>
        </div>
        <div class="mb-3">
          <label for="amount" class="form-label">Amount (USD)</label>
          <input name="amount" id="amount" type="number" step="0.01" min="0.01" class="form-control" value="{{ request.form.get('amount','') }}" required>
        </div>
        <div class="mb-3">
          <label for="note" class="form-label">Note / Description</label>
          <input name="note" id="note" class="form-control" value="{{ request.form.get('note','Demo transfer') }}">
        </div>
        <button class="btn btn-primary" type="submit">Send Demo Transfer</button>
        <a class="btn btn-link" href="{{ url_for('dashboard') }}">Cancel</a>
      </form>
      <hr>
      <p class="text-muted small">Transfers are simulated: this will record a transaction in your demo history and adjust your demo balance. No real money moves.</p>
    </div>
  </div>
{% endblock %}
"""

settings_tpl = """
{% extends base %}
{% block content %}
  <div class="row justify-content-center">
    <div class="col-md-7">
      <h2>Account Settings</h2>

      <div class="card mb-3">
        <div class="card-body">
          <h6>Profile</h6>
          <form method="post" action="{{ url_for('settings') }}">
            <input type="hidden" name="form_type" value="profile">
            <div class="mb-3">
              <label class="form-label">Username</label>
              <input name="username" class="form-control" value="{{ current_user.username }}" required>
            </div>
            <div class="mb-3">
              <label class="form-label">Email</label>
              <input name="email" type="email" class="form-control" value="{{ current_user.email }}" required>
            </div>
            <button class="btn btn-primary" type="submit">Save Profile</button>
          </form>
        </div>
      </div>

      <div class="card">
        <div class="card-body">
          <h6>Change Password</h6>
          <form method="post" action="{{ url_for('settings') }}">
            <input type="hidden" name="form_type" value="password">
            <div class="mb-3">
              <label class="form-label">Current Password</label>
              <input name="current_password" type="password" class="form-control" required>
            </div>
            <div class="mb-3">
              <label class="form-label">New Password</label>
              <input name="new_password" type="password" class="form-control" required>
            </div>
            <button class="btn btn-warning" type="submit">Change Password</button>
          </form>
        </div>
      </div>

    </div>
  </div>
{% endblock %}
"""

# Jinja helpers
@app.template_filter('currency_prefix')
def currency_prefix_filter(s):
    # s is formatted like "1,234.56" possibly with negative
    try:
        # s may be a literal number string
        f = float(s)
        return format_currency(f)
    except Exception:
        # fallback: try to replace and add $
        return "$" + str(s)


# Routes
@app.route('/')
def index():
    return render_template_string(index_tpl, base=base_tpl, title="Home")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        if not username or not email or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template_string(register_tpl, base=base_tpl, title="Register", demo_balance=format_currency(DEMO_START_BALANCE))
        # uniqueness checks
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('A user with that username or email already exists.', 'danger')
            return render_template_string(register_tpl, base=base_tpl, title="Register", demo_balance=format_currency(DEMO_START_BALANCE))
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        # generate demo transactions
        generate_demo_transactions_for_user(user)
        flash('Account created. You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template_string(register_tpl, base=base_tpl, title="Register", demo_balance=format_currency(DEMO_START_BALANCE))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        identity = (request.form.get('identity') or '').strip()
        password = request.form.get('password') or ''
        if not identity or not password:
            flash('Please enter both username/email and password.', 'danger')
            return render_template_string(login_tpl, base=base_tpl, title="Login")
        user = User.query.filter((User.username == identity) | (User.email == identity)).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template_string(login_tpl, base=base_tpl, title="Login")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    # Show last 20 transactions by timestamp descending
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).limit(20).all()
    balance = compute_demo_balance(current_user)
    return render_template_string(dashboard_tpl, base=base_tpl, title="Dashboard",
                                  transactions=transactions, balance=format_currency(balance),
                                  demo_start=format_currency(DEMO_START_BALANCE))


@app.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    if request.method == 'POST':
        recipient = (request.form.get('recipient') or '').strip()
        amount_raw = request.form.get('amount') or ''
        note = (request.form.get('note') or 'Demo transfer').strip()
        try:
            amount = float(amount_raw)
        except ValueError:
            flash('Invalid amount.', 'danger')
            return render_template_string(transfer_tpl, base=base_tpl, title="Transfer")
        if amount <= 0:
            flash('Amount must be positive.', 'danger')
            return render_template_string(transfer_tpl, base=base_tpl, title="Transfer")
        # Compute balance and check (even though demo)
        balance = compute_demo_balance(current_user)
        if amount > balance:
            # For demo, allow overdraft but warn user and record transaction as usual.
            flash('Warning: This demo transfer exceeds your current demo balance. This is a simulation; no real funds are moved.', 'warning')
        # Create a debit transaction for sender
        debit = Transaction(user_id=current_user.id, amount=-amount, timestamp=datetime.utcnow(),
                            description=f"Demo transfer to {recipient}: {note}", counterparty=recipient, txn_type='transfer')
        db.session.add(debit)
        db.session.commit()
        # Optionally create a simulated credit to "recipient" if we wanted - for demo we only track user's side
        flash(f'Demo transfer of {format_currency(amount)} recorded to {recipient}.', 'success')
        return redirect(url_for('dashboard'))
    return render_template_string(transfer_tpl, base=base_tpl, title="Transfer")


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'profile':
            username = (request.form.get('username') or '').strip()
            email = (request.form.get('email') or '').strip().lower()
            if not username or not email:
                flash('Username and email cannot be empty.', 'danger')
                return redirect(url_for('settings'))
            # Check unique excluding current user
            existing = User.query.filter(((User.username == username) | (User.email == email)) & (User.id != current_user.id)).first()
            if existing:
                flash('That username or email is already in use.', 'danger')
                return redirect(url_for('settings'))
            current_user.username = username
            current_user.email = email
            db.session.commit()
            flash('Profile updated.', 'success')
            return redirect(url_for('settings'))
        elif form_type == 'password':
            current_password = request.form.get('current_password') or ''
            new_password = request.form.get('new_password') or ''
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('settings'))
            if len(new_password) < 6:
                flash('New password must be at least 6 characters.', 'danger')
                return redirect(url_for('settings'))
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password changed successfully.', 'success')
            return redirect(url_for('settings'))
        else:
            flash('Invalid form submission.', 'danger')
            return redirect(url_for('settings'))
    return render_template_string(settings_tpl, base=base_tpl, title="Account Settings")


# CLI / startup helpers
@app.before_first_request
def ensure_db():
    db.create_all()


# Simple debug route to reset a user's transactions (for demo testing) - not linked in UI
@app.route('/_dev/reset_transactions', methods=['POST'])
def _dev_reset_transactions():
    # Only allow when running in debug/development (to avoid accidental public use)
    if not app.debug:
        abort(404)
    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()
    if not user:
        return "No such user", 404
    # delete existing transactions
    Transaction.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    generate_demo_transactions_for_user(user, seed=42)
    return f"Reset transactions for {username}", 200


if __name__ == '__main__':
    # Run app in debug by default for demo; in production this should be served by a WSGI server.
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)