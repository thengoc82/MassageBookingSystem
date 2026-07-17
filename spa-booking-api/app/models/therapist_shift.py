from app.extensions import db
from datetime import datetime

class TherapistShift(db.Model):
    __tablename__ = 'therapist_shifts'
    
    id = db.Column(db.Integer, primary_key=True)
    therapist_id = db.Column(db.Integer, db.ForeignKey('therapists.id'), nullable=False, index=True)
    day_of_week = db.Column(db.String(10), nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    effective_from = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    therapist = db.relationship('Therapist', back_populates='shifts')
    
    __table_args__ = (
        db.CheckConstraint("day_of_week IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')", name='check_day_of_week'),
        db.CheckConstraint('end_time > start_time', name='check_shift_time'),
    )
