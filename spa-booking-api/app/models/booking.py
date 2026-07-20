from app.extensions import db
from datetime import datetime

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False, index=True)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    number_of_people = db.Column(db.Integer, nullable=False)
    therapist_id = db.Column(db.Integer, db.ForeignKey('therapists.id'), nullable=True)
    therapist_gender = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Booked')
    internal_notes = db.Column(db.Text, nullable=True)
    preferences_json = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.String(20), default='customer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    shop = db.relationship('Shop', back_populates='bookings')
    customer = db.relationship('Customer', back_populates='bookings')
    therapist = db.relationship('Therapist', back_populates='bookings')
    services = db.relationship('BookingService', back_populates='booking', cascade='all, delete-orphan')
    addons = db.relationship('BookingAddon', back_populates='booking', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.CheckConstraint('number_of_people > 0', name='check_number_of_people'),
        db.CheckConstraint("status IN ('Booked', 'CheckedIn', 'CheckedOut', 'Cancelled')", name='check_status'),
        db.Index('ix_bookings_customer', 'customer_id'),
        db.Index('ix_bookings_shop_date', 'shop_id', 'booking_date'),
        db.Index('ix_bookings_status', 'status'),
    )

class BookingService(db.Model):
    __tablename__ = 'booking_services'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False, index=True)
    person_index = db.Column(db.Integer, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    
    booking = db.relationship('Booking', back_populates='services')
    course = db.relationship('Course')
    
    __table_args__ = (
        db.CheckConstraint('person_index > 0', name='check_person_index'),
    )

class BookingAddon(db.Model):
    __tablename__ = 'booking_addons'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False, index=True)
    person_index = db.Column(db.Integer, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    
    booking = db.relationship('Booking', back_populates='addons')
    course = db.relationship('Course')
    
    __table_args__ = (
        db.CheckConstraint('person_index > 0', name='check_addon_person_index'),
    )
