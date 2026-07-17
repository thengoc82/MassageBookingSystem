from app.extensions import db
from datetime import datetime

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    member_rank = db.Column(db.String(20), nullable=False, default='Silver')
    visit_count = db.Column(db.Integer, nullable=False, default=0)
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    bookings = db.relationship('Booking', back_populates='customer', lazy='dynamic')
    restrictions = db.relationship('CustomerRestriction', back_populates='customer', lazy='dynamic')
