from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from flask_bcrypt import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default="client")  # client / staff

    cases = db.relationship("Case", backref="user", lazy=True)

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password).decode('utf-8')

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_name = db.Column(db.String(200), nullable=True)
    delivery_target = db.Column(db.String(200), nullable=False)
    given_location = db.Column(db.String(200), nullable=False)
    given_to_staff_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="pending")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CaseUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
