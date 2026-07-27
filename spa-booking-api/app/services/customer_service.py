from app.extensions import db
from app.models.customer import Customer
from app.models.customer_restriction import CustomerRestriction


class CustomerService:
    @staticmethod
    def find_or_create(phone_number):
        customer = Customer.query.filter_by(phone_number=phone_number).first()

        if not customer:
            customer = Customer(phone_number=phone_number)
            db.session.add(customer)
            db.session.flush()

        return customer

    @staticmethod
    def check_eligibility(phone_number):
        customer = Customer.query.filter_by(phone_number=phone_number).first()

        if not customer:
            return {
                'customerId': None,
                'isEligible': True,
                'memberRank': 'Silver',
                'visitCount': 0,
                'isBlocked': False
            }

        is_blocked = customer.is_blocked or CustomerRestriction.query.filter_by(
            customer_id=customer.id,
            is_active=True
        ).first() is not None

        result = {
            'customerId': customer.id,
            'isEligible': not is_blocked,
            'memberRank': customer.member_rank,
            'visitCount': customer.visit_count,
            'isBlocked': is_blocked
        }

        if is_blocked:
            restriction = CustomerRestriction.query.filter_by(
                customer_id=customer.id,
                is_active=True
            ).first()
            if restriction:
                result['blockReason'] = restriction.reason

        return result
