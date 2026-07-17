from app.extensions import db
from datetime import datetime

class CustomerRestriction(db.Model):
    __tablename__ = 'customer_restrictions'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    phone_number = db.Column(db.String(20), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    blocked_by = db.Column(db.String(100), nullable=False)
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    customer = db.relationship('Customer', back_populates='restrictions')
