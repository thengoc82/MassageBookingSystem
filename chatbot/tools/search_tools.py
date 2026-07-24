
from gateway.client import HTTPClient
from gateway.errors import ChatbotError, ChatbotErrorCode
from models import (
    CheckEligibilityRequest,
    CheckEligibilityResponse,
    FAQSearchRequest,
    FAQSearchResponse,
    GetTherapistsRequest,
    GetTherapistsResponse,
    LookupBookingRequest,
    LookupBookingResponse,
    SearchAvailableSlotsRequest,
    SearchAvailableSlotsResponse,
    SearchCoursesRequest,
    SearchCoursesResponse,
    SearchShopsRequest,
    SearchShopsResponse,
)
from tools.base import BaseTool


class SearchShopsTool(BaseTool[SearchShopsRequest, SearchShopsResponse]):
    """Tool to search for all available shops."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__("searchShops")
        self._client = http_client

    async def execute(self, request: SearchShopsRequest) -> SearchShopsResponse:
        response = await self._client.get("/shops")
        return SearchShopsResponse(**response)


class SearchCoursesTool(BaseTool[SearchCoursesRequest, SearchCoursesResponse]):
    """Tool to search for courses at a specific shop."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__("searchCourses")
        self._client = http_client

    async def execute(self, request: SearchCoursesRequest) -> SearchCoursesResponse:
        if request.shopId is None:
            raise ChatbotError(ChatbotErrorCode.VALIDATION_ERROR, "shopId is required")
        path = f"/shops/{request.shopId}/courses"
        params = {}
        if request.type:
            params["type"] = request.type
        response = await self._client.get(path, params=params)
        return SearchCoursesResponse(**response)


class SearchAvailableSlotsTool(BaseTool[SearchAvailableSlotsRequest, SearchAvailableSlotsResponse]):
    """Tool to search for available time slots."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__("searchAvailableSlots")
        self._client = http_client

    async def execute(self, request: SearchAvailableSlotsRequest) -> SearchAvailableSlotsResponse:
        path = f"/shops/{request.shopId}/available-slots"
        params = {
            "date": request.date.isoformat(),
            "duration": request.duration,
            "numberOfPeople": request.numberOfPeople,
        }
        if request.startTime:
            params["startTime"] = request.startTime.isoformat()
        if request.courseIds:
            params["courseIds"] = request.courseIds
        if request.gender:
            params["gender"] = request.gender
        if request.showTherapists:
            params["show_therapists"] = "true"
        response = await self._client.get(path, params=params)
        return SearchAvailableSlotsResponse(**response)


class GetTherapistsTool(BaseTool[GetTherapistsRequest, GetTherapistsResponse]):
    """Tool to get available therapists at a specific time."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__("getTherapists")
        self._client = http_client

    async def execute(self, request: GetTherapistsRequest) -> GetTherapistsResponse:
        path = f"/shops/{request.shopId}/available-therapists"
        params = {
            "date": request.date.isoformat(),
            "startTime": request.startTime.isoformat(),
            "duration": request.duration,
        }
        if request.gender:
            params["gender"] = request.gender
        response = await self._client.get(path, params=params)
        return GetTherapistsResponse(**response)


class LookupBookingTool(BaseTool[LookupBookingRequest, LookupBookingResponse]):
    """Tool to look up booking by booking code or phone number."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__("lookupBooking")
        self._client = http_client

    async def execute(self, request: LookupBookingRequest) -> LookupBookingResponse:
        params = {}
        if request.bookingCode:
            # Try to get by booking code first
            path = f"/bookings/{request.bookingCode}"
            try:
                response = await self._client.get(path)
                return LookupBookingResponse(success=True, data=[response["data"]], message="Success")
            except ChatbotError:
                pass
        if request.phoneNumber:
            params["phone"] = request.phoneNumber
        response = await self._client.get("/bookings", params=params)
        return LookupBookingResponse(**response)


class CheckEligibilityTool(BaseTool[CheckEligibilityRequest, CheckEligibilityResponse]):
    """Tool to check customer booking eligibility."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__("checkEligibility")
        self._client = http_client

    async def execute(self, request: CheckEligibilityRequest) -> CheckEligibilityResponse:
        response = await self._client.post("/booking-eligibility-checks", json={"phoneNumber": request.phoneNumber})
        return CheckEligibilityResponse(**response)


class FAQSearchTool(BaseTool[FAQSearchRequest, FAQSearchResponse]):
    """Tool to search FAQ knowledge base."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__("faqSearch")
        self._client = http_client

    async def execute(self, request: FAQSearchRequest) -> FAQSearchResponse:
        # Note: FAQ endpoint may not exist in Flask API yet
        # This is a placeholder for the knowledge system in Phase 4
        return FAQSearchResponse(
            success=True,
            data=[],
            message="FAQ search not yet implemented - will be available in Phase 4",
        )