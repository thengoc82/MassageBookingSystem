

class ChatbotErrorCode(str):
    """Standardized error codes for chatbot."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    SHOP_NOT_FOUND = "SHOP_NOT_FOUND"
    BOOKING_NOT_FOUND = "BOOKING_NOT_FOUND"
    THERAPIST_NOT_FOUND = "THERAPIST_NOT_FOUND"
    COURSE_NOT_FOUND = "COURSE_NOT_FOUND"
    CONFLICT = "CONFLICT"
    TIME_SLOT_UNAVAILABLE = "TIME_SLOT_UNAVAILABLE"
    THERAPIST_UNAVAILABLE = "THERAPIST_UNAVAILABLE"
    BOOKING_CONFLICT = "BOOKING_CONFLICT"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    INVALID_BOOKING_DATE = "INVALID_BOOKING_DATE"
    CUSTOMER_BLOCKED = "CUSTOMER_BLOCKED"
    SHOP_CLOSED = "SHOP_CLOSED"
    THERAPIST_NOT_ALLOWED_GROUP = "THERAPIST_NOT_ALLOWED_GROUP"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"
    GATEWAY_CONNECTION_ERROR = "GATEWAY_CONNECTION_ERROR"
    TOOL_ERROR = "TOOL_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"


class ChatbotError(Exception):
    """Base exception for chatbot errors."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable


class ValidationError(ChatbotError):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(ChatbotErrorCode.VALIDATION_ERROR, message, details, retryable=False)


class NotFoundError(ChatbotError):
    def __init__(
        self, message: str, resource_type: str = "resource"
    ) -> None:
        super().__init__(
            ChatbotErrorCode.NOT_FOUND,
            message,
            {"resource_type": resource_type},
            retryable=False,
        )



class ShopNotFoundError(NotFoundError):
    def __init__(self, message: str = "Shop not found") -> None:
        super().__init__(message, "shop")
        self.code = ChatbotErrorCode.SHOP_NOT_FOUND


class BookingNotFoundError(NotFoundError):
    def __init__(self, message: str = "Booking not found") -> None:
        super().__init__(message, "booking")
        self.code = ChatbotErrorCode.BOOKING_NOT_FOUND


class ConflictError(ChatbotError):
    def __init__(self, message: str) -> None:
        super().__init__(ChatbotErrorCode.CONFLICT, message, retryable=True)


class TimeSlotUnavailableError(ConflictError):
    def __init__(self, message: str = "Time slot no longer available") -> None:
        super().__init__(message)
        self.code = ChatbotErrorCode.TIME_SLOT_UNAVAILABLE


class TherapistUnavailableError(ConflictError):
    def __init__(self, message: str = "Therapist not available at selected time") -> None:
        super().__init__(message)
        self.code = ChatbotErrorCode.THERAPIST_UNAVAILABLE


class BusinessRuleError(ChatbotError):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(
            ChatbotErrorCode.BUSINESS_RULE_VIOLATION,
            message,
            details,
            retryable=False,
        )



class InvalidBookingDateError(BusinessRuleError):
    def __init__(self, message: str = "Booking date is in the past") -> None:
        super().__init__(message)
        self.code = ChatbotErrorCode.INVALID_BOOKING_DATE


class CustomerBlockedError(BusinessRuleError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Customer is blocked: {reason}", {"block_reason": reason})
        self.code = ChatbotErrorCode.CUSTOMER_BLOCKED


class ShopClosedError(BusinessRuleError):
    def __init__(self, message: str = "Shop is closed at the selected time") -> None:
        super().__init__(message)
        self.code = ChatbotErrorCode.SHOP_CLOSED


class TherapistNotAllowedGroupError(BusinessRuleError):
    def __init__(self) -> None:
        super().__init__("Cannot assign specific therapist for group bookings")
        self.code = ChatbotErrorCode.THERAPIST_NOT_ALLOWED_GROUP


class GatewayTimeoutError(ChatbotError):
    def __init__(self, message: str = "Gateway request timed out") -> None:
        super().__init__(ChatbotErrorCode.GATEWAY_TIMEOUT, message, retryable=True)


class GatewayConnectionError(ChatbotError):
    def __init__(self, message: str = "Failed to connect to gateway") -> None:
        super().__init__(ChatbotErrorCode.GATEWAY_CONNECTION_ERROR, message, retryable=True)


class UnauthorizedError(ChatbotError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(ChatbotErrorCode.UNAUTHORIZED, message)


class ForbiddenError(ChatbotError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(ChatbotErrorCode.FORBIDDEN, message)


def map_flask_error(status_code: int, error_code: str, message: str) -> ChatbotError:
    """Map Flask API error to chatbot error."""
    error_map: dict[str, type] = {
        "VALIDATION_ERROR": ValidationError,
        "INVALID_REQUEST": ValidationError,
        "INVALID_PHONE_NUMBER": ValidationError,
        "DATE_REQUIRED": ValidationError,
        "DURATION_REQUIRED": ValidationError,
        "NUMBER_OF_PEOPLE_REQUIRED": ValidationError,
        "SERVICES_REQUIRED": ValidationError,
        "SHOP_NAME_REQUIRED": ValidationError,
        "ADDRESS_REQUIRED": ValidationError,
        "SHOP_NOT_FOUND": ShopNotFoundError,
        "BOOKING_NOT_FOUND": BookingNotFoundError,
        "THERAPIST_NOT_FOUND": NotFoundError,
        "COURSE_NOT_FOUND": NotFoundError,
        "SHIFT_NOT_FOUND": NotFoundError,
        "CUSTOMER_NOT_FOUND": NotFoundError,
        "RESOURCE_NOT_FOUND": NotFoundError,
        "DUPLICATE_RESOURCE": ConflictError,
        "BOOKING_CONFLICT": ConflictError,
        "TIME_SLOT_UNAVAILABLE": TimeSlotUnavailableError,
        "THERAPIST_UNAVAILABLE": TherapistUnavailableError,
        "BUSINESS_RULE_VIOLATION": BusinessRuleError,
        "INVALID_BOOKING_DATE": InvalidBookingDateError,
        "CUSTOMER_BLOCKED": CustomerBlockedError,
        "SHOP_CLOSED": ShopClosedError,
        "THERAPIST_NOT_ALLOWED_GROUP": TherapistNotAllowedGroupError,
        "INVALID_COURSE_TYPE": BusinessRuleError,
        "INVALID_MODIFY_STATUS": BusinessRuleError,
        "UNAUTHORIZED": UnauthorizedError,
        "FORBIDDEN": ForbiddenError,
    }

    if error_code in error_map:
        return error_map[error_code](message)  # type: ignore[call-arg]

    # Default mapping by status code
    if status_code == 400:
        return ValidationError(message)
    if status_code == 404:
        return NotFoundError(message)
    if status_code in (409, 422):
        return BusinessRuleError(message)
    if status_code >= 500:
        return ChatbotError(ChatbotErrorCode.INTERNAL_SERVER_ERROR, message, retryable=True)

    return ChatbotError(ChatbotErrorCode.INTERNAL_SERVER_ERROR, message)
