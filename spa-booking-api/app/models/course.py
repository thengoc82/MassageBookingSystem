import json
from datetime import datetime

from app.extensions import db


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=True)
    price = db.Column(db.Integer, nullable=True)
    durations_json = db.Column(db.Text, nullable=True)
    course_type = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(10), nullable=False, default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    shop = db.relationship('Shop', back_populates='courses')

    __table_args__ = (
        db.CheckConstraint("course_type IN ('main', 'addon')", name='check_course_type'),
    )

    def get_durations(self):
        if not self.durations_json:
            if self.duration and self.price:
                return [{'duration': self.duration, 'price': self.price}]
            return []
        try:
            return json.loads(self.durations_json)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_durations(self, durations):
        self.durations_json = json.dumps(durations, ensure_ascii=False)
