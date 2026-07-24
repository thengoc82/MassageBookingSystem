"""Tests for gateway — errors and error mapping"""
import pytest

from gateway.errors import (
    BookingNotFoundError,
    ChatbotError,
    ChatbotErrorCode,
    ConflictError,
    CustomerBlockedError,
    GatewayConnectionError,
    GatewayTimeoutError,
    InvalidBookingDateError,
    NotFoundError,
    ShopClosedError,
    ShopNotFoundError,
    TherapistNotAllowedGroupError,
    TherapistUnavailableError,
    TimeSlotUnavailableError,
    ValidationError,
    map_flask_error,
)


def test_chatbot_error_basic():
    err = ChatbotError("TEST", "Test message")
    assert err.code == "TEST"
    assert err.message == "Test message"
    assert err.retryable is False


def test_chatbot_error_with_details():
    err = ChatbotError("TEST", "Test message", details={"key": "value"}, retryable=True)
    assert err.details == {"key": "value"}
    assert err.retryable is True


def test_validation_error():
    err = ValidationError("Invalid input")
    assert err.code == ChatbotErrorCode.VALIDATION_ERROR
    assert err.retryable is False


def test_not_found_error():
    err = NotFoundError("Resource not found", "test")
    assert "test" in err.details["resource_type"]


def test_shop_not_found_error():
    err = ShopNotFoundError()
    assert err.code == ChatbotErrorCode.SHOP_NOT_FOUND


def test_booking_not_found_error():
    err = BookingNotFoundError()
    assert err.code == ChatbotErrorCode.BOOKING_NOT_FOUND


def test_conflict_error_is_retryable():
    err = ConflictError("Conflict")
    assert err.retryable is True


def test_time_slot_unavailable_error():
    err = TimeSlotUnavailableError()
    assert err.code == ChatbotErrorCode.TIME_SLOT_UNAVAILABLE
    assert err.retryable is True


def test_therapist_unavailable_error():
    err = TherapistUnavailableError()
    assert err.code == ChatbotErrorCode.THERAPIST_UNAVAILABLE


def test_business_rule_errors():
    assert InvalidBookingDateError().code == ChatbotErrorCode.INVALID_BOOKING_DATE
    assert CustomerBlockedError("reason").code == ChatbotErrorCode.CUSTOMER_BLOCKED
    assert ShopClosedError().code == ChatbotErrorCode.SHOP_CLOSED
    assert TherapistNotAllowedGroupError().code == ChatbotErrorCode.THERAPIST_NOT_ALLOWED_GROUP


def test_gateway_errors():
    assert GatewayTimeoutError().code == ChatbotErrorCode.GATEWAY_TIMEOUT
    assert GatewayTimeoutError().retryable is True
    assert GatewayConnectionError().code == ChatbotErrorCode.GATEWAY_CONNECTION_ERROR


def test_map_flask_error_validation():
    err = map_flask_error(400, "VALIDATION_ERROR", "Invalid input")
    assert isinstance(err, ValidationError)


def test_map_flask_error_shop_not_found():
    err = map_flask_error(404, "SHOP_NOT_FOUND", "Not found")
    assert isinstance(err, ShopNotFoundError)


def test_map_flask_error_booking_not_found():
    err = map_flask_error(404, "BOOKING_NOT_FOUND", "Not found")
    assert isinstance(err, BookingNotFoundError)


def test_map_flask_error_customer_blocked():
    err = map_flask_error(403, "CUSTOMER_BLOCKED", "Blocked")
    assert isinstance(err, CustomerBlockedError)


def test_map_flask_error_time_slot_unavailable():
    err = map_flask_error(409, "TIME_SLOT_UNAVAILABLE", "Unavailable")
    assert isinstance(err, TimeSlotUnavailableError)
    assert err.retryable is True


def test_map_flask_error_invalid_booking_date():
    err = map_flask_error(422, "INVALID_BOOKING_DATE", "Invalid date")
    assert isinstance(err, InvalidBookingDateError)


def test_map_flask_error_default_400():
    err = map_flask_error(400, "UNKNOWN", "Bad request")
    assert isinstance(err, ValidationError)


def test_map_flask_error_default_404():
    err = map_flask_error(404, "UNKNOWN", "Not found")
    assert isinstance(err, NotFoundError)


def test_map_flask_error_default_500():
    err = map_flask_error(500, "UNKNOWN", "Server error")
    assert err.retryable is True


def test_map_flask_error_default_500_with_code():
    err = map_flask_error(500, "INTERNAL_SERVER_ERROR", "Server error")
    assert err.code == ChatbotErrorCode.INTERNAL_SERVER_ERROR
    assert err.retryable is True


def test_map_flask_error_default_other():
    err = map_flask_error(200, "UNKNOWN", "OK")
    assert err.code == ChatbotErrorCode.INTERNAL_SERVER_ERROR