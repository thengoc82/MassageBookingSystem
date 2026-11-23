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
        booking_id = request.bookingId
        payload = request.model_dump(mode="json", exclude={"bookingId"}, exclude_none=True)
        unsupported = set(payload) - {"startTime", "therapistId"}
        if unsupported or not payload:
            raise ChatbotError(
                ChatbotErrorCode.VALIDATION_ERROR,
                "This booking change is not supported by the booking API",
            )
        if request.startTime:
            payload["startTime"] = request.startTime.strftime("%H:%M")
        response = await self._client.patch(f"/bookings/{booking_id}", json=payload)
        data = response.get("data") or response
        return ModifyBookingResponse(
            success=response["success"], bookingId=data.get("bookingId"),
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
        booking_id = request.bookingId
        response = await self._client.patch(f"/bookings/{booking_id}/cancel", json={})
        data = response.get("data") or response
        return CancelBookingResponse(
            success=response["success"], bookingId=data.get("bookingId"),
            message=response.get("message"),
        )
