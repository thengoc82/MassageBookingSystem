from datetime import datetime

from app.extensions import db


class Shop(db.Model):
    __tablename__ = 'shops'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(10), nullable=False, default='Open')
    open_time = db.Column(db.Time, nullable=False)
    close_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    courses = db.relationship('Course', back_populates='shop', lazy='dynamic')
    therapists = db.relationship('Therapist', back_populates='shop', lazy='dynamic')
    bookings = db.relationship('Booking', back_populates='shop', lazy='dynamic')
