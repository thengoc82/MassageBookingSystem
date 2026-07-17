from app.extensions import db
from datetime import datetime

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    course_type = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(10), nullable=False, default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    shop = db.relationship('Shop', back_populates='courses')
    
    __table_args__ = (
        db.CheckConstraint("course_type IN ('main', 'addon')", name='check_course_type'),
    )
