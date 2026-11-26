"""Proof of control of a booking phone number, without customer accounts."""

import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from flask import current_app, request
from flask_jwt_extended import create_access_token, get_jwt_identity, verify_jwt_in_request

from app import extensions
from app.utils.errors import APIError, Forbidden, ResourceNotFound, Unauthorized, ValidationError


def canonical_phone(value):
    if not isinstance(value, str):
        raise ValidationError('A valid phone number is required')
    phone = value.strip()
    if re.fullmatch(r'0\d{9,10}', phone):
        return phone
    if re.fullmatch(r'\+84\d{9,10}', phone):
        return '0' + phone[3:]
    if re.fullmatch(r'84\d{9,10}', phone):
        return '0' + phone[2:]
    if re.fullmatch(r'\+[1-9]\d{8,14}', phone):
        return phone
    raise ValidationError('A valid phone number is required')


def phone_aliases(value):
    phone = canonical_phone(value)
    if phone.startswith('0'):
        return [phone, '+84' + phone[1:], '84' + phone[1:]]
    return [phone]


def _digest(value):
    secret = current_app.config['SECRET_KEY'].encode()
    return hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()


def _redis():
    if extensions.redis_client is None:
        raise APIError('VERIFICATION_UNAVAILABLE', 'Phone verification is unavailable', 503)
    try:
        extensions.redis_client.ping()
    except Exception as error:
        current_app.logger.warning('Booking access Redis unavailable: %s', type(error).__name__)
        raise APIError('VERIFICATION_UNAVAILABLE', 'Phone verification is unavailable', 503) from error
    return extensions.redis_client


def _terminal_delivery(phone, code):
    print(f'Booking access code for {phone}: {code} (expires in 5 minutes)', flush=True)


# Add another provider here when an external delivery service is needed.
_DELIVERY_PROVIDERS = {'terminal': _terminal_delivery}


def _deliver_code(phone, code):
    provider_name = current_app.config.get('BOOKING_ACCESS_DELIVERY_PROVIDER', 'disabled')
    if provider_name == 'terminal' and not (
        current_app.config.get('BOOKING_ACCESS_RUNTIME_ENV') == 'development'
        and current_app.debug
    ):
        raise APIError('VERIFICATION_UNAVAILABLE', 'Phone verification is unavailable', 503)
    provider = _DELIVERY_PROVIDERS.get(provider_name)
    if provider is None:
        raise APIError('VERIFICATION_UNAVAILABLE', 'Phone verification is unavailable', 503)
    provider(phone, code)
    return provider_name


def request_code(phone_number):
    phone = canonical_phone(phone_number)
    redis = _redis()
    key_id = _digest(phone)
    ip_id = _digest(request.remote_addr or 'unknown')
    try:
        for key, limit, ttl in ((f'booking-access:phone-rate:{key_id}', 3, 900),
                                (f'booking-access:ip-rate:{ip_id}', 20, 3600)):
            count = redis.incr(key)
            if count == 1:
                redis.expire(key, ttl)
            if count > limit:
                raise APIError('RATE_LIMITED', 'Please try again later', 429)
        code = f'{secrets.randbelow(1000000):06d}'
        key = f'booking-access:code:{key_id}'
        redis.hset(key, mapping={'digest': _digest(f'{phone}:{code}'), 'attempts': 0})
        redis.expire(key, 300)
        try:
            delivery = _deliver_code(phone, code)
        except Exception as error:
            redis.delete(key)
            if not isinstance(error, APIError):
                current_app.logger.warning('Booking access code delivery failed: %s', type(error).__name__)
            raise APIError('VERIFICATION_UNAVAILABLE', 'Phone verification is unavailable', 503) from error
        return delivery
    except APIError:
        raise
    except Exception as error:
        raise APIError('VERIFICATION_UNAVAILABLE', 'Phone verification is unavailable', 503) from error


_VERIFY_SCRIPT = """
local saved = redis.call('HGET', KEYS[1], 'digest')
if not saved then return 0 end
local attempts = redis.call('HINCRBY', KEYS[1], 'attempts', 1)
if attempts > 5 then redis.call('DEL', KEYS[1]); return 0 end
if saved == ARGV[1] then redis.call('DEL', KEYS[1]); return 1 end
return 0
"""


def verify_code(phone_number, code):
    phone = canonical_phone(phone_number)
    if not isinstance(code, str) or not re.fullmatch(r'\d{6}', code):
        raise ValidationError('A six-digit verification code is required')
    key = f'booking-access:code:{_digest(phone)}'
    try:
        valid = _redis().eval(_VERIFY_SCRIPT, 1, key, _digest(f'{phone}:{code}'))
    except APIError:
        raise
    except Exception as error:
        raise APIError('VERIFICATION_UNAVAILABLE', 'Phone verification is unavailable', 503) from error
    if valid != 1:
        raise Unauthorized('Invalid or expired verification code')
    return create_access_token(
        identity={'role': 'customer', 'type': 'customer_access', 'phone': phone},
        expires_delta=timedelta(minutes=30),
    )


def booking_identity():
    verify_jwt_in_request()
    identity = get_jwt_identity()
    if not isinstance(identity, dict):
        raise Forbidden()
    return identity


def require_customer_phone(phone):
    identity = booking_identity()
    if identity.get('type') != 'customer_access' or identity.get('role') != 'customer':
        raise Forbidden()
    if identity.get('phone') != canonical_phone(phone):
        raise Forbidden()
    return identity


def require_booking_access(booking, *, write=False):
    identity = booking_identity()
    role = identity.get('role')
    if role == 'admin' and identity.get('type') == 'admin':
        return identity
    if not write and role == 'therapist' and identity.get('type') == 'therapist':
        therapist_id = identity.get('user_id') or identity.get('ref_id')
        if therapist_id and (booking.therapist_id == therapist_id or any(
            row.therapist_id == therapist_id for row in booking.booking_therapists
        )):
            return identity
    if (
        role == 'customer'
        and identity.get('type') == 'customer_access'
        and identity.get('phone') == canonical_phone(booking.phone_number)
    ):
        return identity
    raise ResourceNotFound('Booking')
