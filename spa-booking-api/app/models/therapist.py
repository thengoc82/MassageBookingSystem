from app.extensions import db
from datetime import datetime

class Therapist(db.Model):
    __tablename__ = 'therapists'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    status = db.Column(db.String(10), nullable=False, default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    shop = db.relationship('Shop', back_populates='therapists')
    shifts = db.relationship('TherapistShift', back_populates='therapist', lazy='dynamic')
    bookings = db.relationship('Booking', back_populates='therapist', lazy='dynamic')
    
    __table_args__ = (
        db.CheckConstraint("gender IN ('Male', 'Female')", name='check_gender'),
    )
