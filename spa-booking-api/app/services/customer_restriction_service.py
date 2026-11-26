from datetime import datetime

from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.models.customer_restriction import CustomerRestriction
from app.services.customer_service import CustomerService
from app.utils.errors import APIError, ResourceNotFound, ValidationError
from app.utils.pagination import paginate


def serialize(restriction):
    return {
        'restrictionId': restriction.id,
        'customerId': restriction.customer_id,
        'phoneNumber': restriction.phone_number,
        'reason': restriction.reason,
        'blockedAt': restriction.blocked_at.isoformat() if restriction.blocked_at else None,
        'blockedBy': restriction.blocked_by,
        'updatedAt': restriction.updated_at.isoformat() if restriction.updated_at else None,
        'isActive': restriction.is_active,
    }


def _reason(value):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError('reason is required')
    return value.strip()


def _lock_write():
    if db.engine.dialect.name == 'sqlite':
        db.session.connection().exec_driver_sql('BEGIN IMMEDIATE')


def _write_error(error):
    db.session.rollback()
    if db.engine.dialect.name == 'sqlite' and any(
        marker in str(error.orig).lower() for marker in ('locked', 'busy')
    ):
        raise APIError('RESTRICTION_CONFLICT', 'Customer restriction is busy; please try again', 409) from error
    raise error


def _sync_customer_flags(customers):
    ids = [customer.id for customer in customers]
    active_ids = {row.customer_id for row in CustomerRestriction.query.filter(
        CustomerRestriction.customer_id.in_(ids),
        CustomerRestriction.is_active.is_(True),
    ).all()}
    # Alias rows represent the same phone and therefore have the same effective state.
    blocked = bool(active_ids)
    for customer in customers:
        customer.is_blocked = blocked


class CustomerRestrictionService:
    @staticmethod
    def list(phone=None, status='active', page=1, size=20):
        if status not in ('active', 'inactive', 'all'):
            raise ValidationError('status must be active, inactive, or all')
        if type(page) is not int or page <= 0 or type(size) is not int or not 1 <= size <= 100:
            raise ValidationError('page and size must be positive integers; size must be at most 100')
        query = CustomerRestriction.query
        if phone:
            query = query.filter(CustomerRestriction.phone_number.startswith(phone.strip()))
        if status != 'all':
            query = query.filter(CustomerRestriction.is_active.is_(status == 'active'))
        query = query.order_by(CustomerRestriction.blocked_at.desc(), CustomerRestriction.id.desc())
        result = paginate(query, page, size)
        return [serialize(item) for item in result['items']], result['pagination']

    @staticmethod
    def get(restriction_id):
        restriction = db.session.get(CustomerRestriction, restriction_id)
        if restriction is None:
            raise ResourceNotFound('Customer restriction')
        return serialize(restriction)

    @staticmethod
    def create(data, blocked_by):
        if not isinstance(data, dict) or set(data) != {'phoneNumber', 'reason'}:
            raise ValidationError('phoneNumber and reason are required')
        phone = data['phoneNumber']
        reason = _reason(data['reason'])
        CustomerService.phone_matches(phone)
        try:
            _lock_write()
            customers = CustomerService.matching_customers(phone, lock=True)
            if not customers:
                raise ResourceNotFound('Customer')
            ids = [customer.id for customer in customers]
            if CustomerRestriction.query.filter(
                CustomerRestriction.customer_id.in_(ids),
                CustomerRestriction.is_active.is_(True),
            ).first():
                raise APIError('CUSTOMER_ALREADY_BLOCKED', 'Customer is already blocked', 409)
            customer = next((c for c in customers if c.phone_number == phone.strip()), customers[0])
            restriction = CustomerRestriction(
                customer_id=customer.id, phone_number=customer.phone_number,
                reason=reason, blocked_by=blocked_by, is_active=True,
                blocked_at=datetime.utcnow(), updated_at=datetime.utcnow(),
            )
            db.session.add(restriction)
            db.session.flush()
            _sync_customer_flags(customers)
            db.session.commit()
            return serialize(restriction)
        except OperationalError as error:
            _write_error(error)
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def update(restriction_id, data):
        if not isinstance(data, dict) or not data or set(data) - {'reason', 'isActive'}:
            raise ValidationError('Supply reason or isActive')
        if 'isActive' in data and data['isActive'] is not False:
            raise ValidationError('isActive can only be set to false; create a new entry to block again')
        reason = _reason(data['reason']) if 'reason' in data else None
        try:
            _lock_write()
            restriction = db.session.get(CustomerRestriction, restriction_id)
            if restriction is None:
                raise ResourceNotFound('Customer restriction')
            customers = CustomerService.matching_customers(restriction.phone_number, lock=True)
            if reason is not None:
                restriction.reason = reason
            if 'isActive' in data:
                restriction.is_active = False
            restriction.updated_at = datetime.utcnow()
            db.session.flush()
            _sync_customer_flags(customers)
            db.session.commit()
            return serialize(restriction)
        except OperationalError as error:
            _write_error(error)
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def delete(restriction_id):
        CustomerRestrictionService.update(restriction_id, {'isActive': False})
        return restriction_id
