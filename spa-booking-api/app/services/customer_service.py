from app.extensions import db
from app.models.customer import Customer
from app.models.customer_restriction import CustomerRestriction
from app.services.booking_access import phone_aliases
from app.utils.errors import ValidationError


class CustomerService:
    @staticmethod
    def phone_matches(phone_number):
        if not isinstance(phone_number, str) or not phone_number.strip():
            raise ValidationError('phoneNumber is required')
        phone = phone_number.strip()
        try:
            return phone_aliases(phone)
        except ValidationError:
            # Existing booking creation accepts noncanonical phones. Preserve
            # exact matching for those legacy customer records.
            return [phone]

    @staticmethod
    def matching_customers(phone_number, lock=False):
        query = Customer.query.filter(Customer.phone_number.in_(
            CustomerService.phone_matches(phone_number)))
        if lock and db.engine.dialect.name != 'sqlite':
            query = query.with_for_update()
        return query.order_by(Customer.id).all()

    @staticmethod
    def find_or_create(phone_number):
        customer = Customer.query.filter_by(phone_number=phone_number).first()

        if not customer:
            customer = Customer(phone_number=phone_number)
            db.session.add(customer)
            db.session.flush()

        return customer

    @staticmethod
    def check_eligibility(phone_number, lock=False):
        customers = CustomerService.matching_customers(phone_number, lock=lock)
        customer = next((c for c in customers if c.phone_number == phone_number.strip()),
                        customers[0] if customers else None)

        if not customer:
            return {
                'customerId': None,
                'isEligible': True,
                'memberRank': 'Silver',
                'visitCount': 0,
                'isBlocked': False
            }

        restriction = CustomerRestriction.query.filter(
            CustomerRestriction.customer_id.in_([c.id for c in customers]),
            CustomerRestriction.is_active.is_(True),
        ).order_by(CustomerRestriction.blocked_at.desc(), CustomerRestriction.id.desc()).first()
        # The migration turns legacy flag-only blocks into records. Keep the
        # original flag fallback safe if code starts before that upgrade runs.
        is_blocked = restriction is not None or any(c.is_blocked for c in customers)

        result = {
            'customerId': customer.id,
            'isEligible': not is_blocked,
            'memberRank': customer.member_rank,
            'visitCount': customer.visit_count,
            'isBlocked': is_blocked
        }

        if restriction:
            result['blockReason'] = restriction.reason

        return result
