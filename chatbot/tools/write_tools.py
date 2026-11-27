# chatbot/tools/write_tools.py
from chatbot.gateway.client import HTTPClient
from chatbot.gateway.errors import ChatbotError, ChatbotErrorCode
from chatbot.models import (
    CancelBookingRequest,
    CancelBookingResponse,
    CreateBookingRequest,
    CreateBookingResponse,
    ModifyBookingRequest,
    ModifyBookingResponse,
)
from chatbot.tools.base import BaseTool


class CreateBookingTool(BaseTool[CreateBookingRequest, CreateBookingResponse]):
    """Tool to create a new booking."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__(
            "createBooking", CreateBookingRequest, CreateBookingResponse, is_write=True
        )
        self._client = http_client

    async def execute(self, request: CreateBookingRequest) -> CreateBookingResponse:
        payload = request.model_dump(mode="json", exclude_none=True)
        payload["startTime"] = request.startTime.strftime("%H:%M")
        response = await self._client.post("/bookings", json=payload)
        data = response.get("data") or response
        return CreateBookingResponse(
            success=response["success"],
            bookingId=data.get("bookingId"),
            bookingCode=data.get("bookingCode"),
            status=data.get("status"),
            therapistId=data.get("therapistId"),
            therapistName=data.get("therapistName"),
            therapistAssignments=data.get("therapistAssignments") or [],
            message=response.get("message"),
        )


class ModifyBookingTool(BaseTool[ModifyBookingRequest, ModifyBookingResponse]):
    """Tool to modify an existing booking."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__(
            "modifyBooking", ModifyBookingRequest, ModifyBookingResponse, is_write=True
        )
        self._client = http_client

    async def execute(self, request: ModifyBookingRequest) -> ModifyBookingResponse:
        if not request.accessToken:
            raise ChatbotError(ChatbotErrorCode.VALIDATION_ERROR, "Phone verification is required")
        booking_id = request.bookingId
        payload = request.model_dump(mode="json", exclude={"bookingId", "accessToken"}, exclude_none=True)
        unsupported = set(payload) - {"bookingDate", "startTime"}
        if unsupported or not payload:
            raise ChatbotError(
                ChatbotErrorCode.VALIDATION_ERROR,
                "This booking change is not supported by the booking API",
            )
        if request.startTime:
            payload["startTime"] = request.startTime.strftime("%H:%M")
        response = await self._client.patch(f"/bookings/{booking_id}", json=payload, headers={"Authorization": f"Bearer {request.accessToken}"})
        data = response.get("data") or response
        return ModifyBookingResponse(
            success=response["success"], bookingId=data.get("bookingId"),
            status=data.get("status"),
            message=response.get("message"),
        )


class CancelBookingTool(BaseTool[CancelBookingRequest, CancelBookingResponse]):
    """Tool to cancel an existing booking."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__(
            "cancelBooking", CancelBookingRequest, CancelBookingResponse, is_write=True
        )
        self._client = http_client

    async def execute(self, request: CancelBookingRequest) -> CancelBookingResponse:
        if not request.accessToken:
            raise ChatbotError(ChatbotErrorCode.VALIDATION_ERROR, "Phone verification is required")
        booking_id = request.bookingId
        response = await self._client.patch(f"/bookings/{booking_id}/cancel", json={}, headers={"Authorization": f"Bearer {request.accessToken}"})
        data = response.get("data") or response
        return CancelBookingResponse(
            success=response["success"], bookingId=data.get("bookingId"),
            status=data.get("status"),
            message=response.get("message"),
        )
