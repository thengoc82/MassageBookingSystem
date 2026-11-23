# chatbot/tools/search_tools.py
from chatbot.gateway.client import HTTPClient
from chatbot.gateway.errors import ChatbotError, ChatbotErrorCode
from chatbot.knowledge.knowledge_service import KnowledgeService
from chatbot.models import (
    CheckEligibilityRequest,
    CheckEligibilityResponse,
    FAQCitation,
    FAQItem,
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
from chatbot.tools.base import BaseTool


class SearchShopsTool(BaseTool[SearchShopsRequest, SearchShopsResponse]):
    """Tool to search for all available shops."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__("searchShops", SearchShopsRequest, SearchShopsResponse)
        self._client = http_client

    async def execute(self, request: SearchShopsRequest) -> SearchShopsResponse:
        response = await self._client.get("/shops")
        return SearchShopsResponse(**response)


class SearchCoursesTool(BaseTool[SearchCoursesRequest, SearchCoursesResponse]):
    """Tool to search for courses at a specific shop."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__("searchCourses", SearchCoursesRequest, SearchCoursesResponse)
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
        super().__init__(
            "searchAvailableSlots",
            SearchAvailableSlotsRequest,
            SearchAvailableSlotsResponse,
        )
        self._client = http_client


    async def execute(self, request: SearchAvailableSlotsRequest) -> SearchAvailableSlotsResponse:
        path = f"/shops/{request.shopId}/available-slots"
        params = {
            "date": request.date.isoformat(),
            "duration": request.duration,
            "numberOfPeople": request.numberOfPeople,
        }
        if request.startTime:
            params["startTime"] = request.startTime.strftime("%H:%M")
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
        super().__init__("getTherapists", GetTherapistsRequest, GetTherapistsResponse)
        self._client = http_client

    async def execute(self, request: GetTherapistsRequest) -> GetTherapistsResponse:
        path = f"/shops/{request.shopId}/available-therapists"
        params = {
            "date": request.date.isoformat(),
            "startTime": request.startTime.strftime("%H:%M"),
            "duration": request.duration,
        }
        if request.gender:
            params["gender"] = request.gender
        response = await self._client.get(path, params=params)
        return GetTherapistsResponse(**response)


class LookupBookingTool(BaseTool[LookupBookingRequest, LookupBookingResponse]):
    """Tool to look up booking by booking code or phone number."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__("lookupBooking", LookupBookingRequest, LookupBookingResponse)
        self._client = http_client

    async def execute(self, request: LookupBookingRequest) -> LookupBookingResponse:
        if not request.phoneNumber:
            raise ChatbotError(
                ChatbotErrorCode.VALIDATION_ERROR,
                "A phone number is required to look up a booking",
            )
        page = 1
        while True:
            params = {"phone": request.phoneNumber}
            if page > 1:
                params["page"] = page
            response = await self._client.get("/bookings", params=params)
            payload = response.get("data")
            listings = payload.get("data", []) if isinstance(payload, dict) else (payload or [])
            pagination = payload.get("pagination") if isinstance(payload, dict) else response.get("pagination")
            if request.bookingCode:
                listings = [
                    item for item in listings
                    if item.get("bookingCode") == request.bookingCode
                ]
            if listings or not request.bookingCode or not pagination or page >= pagination.get("totalPages", page):
                break
            page += 1
        return LookupBookingResponse(
            success=bool(response.get("success")),
            data=listings,
            message=response.get("message", "Success"),
            pagination=pagination,
        )


class CheckEligibilityTool(BaseTool[CheckEligibilityRequest, CheckEligibilityResponse]):
    """Tool to check customer booking eligibility."""

    def __init__(self, http_client: HTTPClient) -> None:
        super().__init__("checkEligibility", CheckEligibilityRequest, CheckEligibilityResponse)
        self._client = http_client

    async def execute(self, request: CheckEligibilityRequest) -> CheckEligibilityResponse:
        response = await self._client.post(
            "/booking-eligibility-checks", json={"phoneNumber": request.phoneNumber}
        )

        return CheckEligibilityResponse(**response)


class FAQSearchTool(BaseTool[FAQSearchRequest, FAQSearchResponse]):
    """Tool to search the FAQ knowledge base using vector search."""

    def __init__(self, knowledge_service: KnowledgeService) -> None:
        super().__init__("faqSearch", FAQSearchRequest, FAQSearchResponse)
        self._knowledge_service = knowledge_service

    async def execute(self, request: FAQSearchRequest) -> FAQSearchResponse:
        if not self._knowledge_service:
            raise ChatbotError(
                ChatbotErrorCode.INTERNAL_SERVER_ERROR,
                "Knowledge service not configured",
            )

        filters = {
            key: value for key, value in {
                "shop_id": request.shopId,
                "category": request.category,
                "language": request.language,
            }.items() if value is not None
        }
        results = self._knowledge_service.query(
            request.query, top_k=request.topK, filter=filters
        ) if filters else self._knowledge_service.query(request.query, top_k=request.topK)

        items = [
            FAQItem(
                content=result.content,
                score=result.score,
                citation=FAQCitation(
                    source_file=result.source_file,
                    document_title=result.title,
                    heading=result.heading,
                    document_id=result.document_id,
                    source=result.source,
                ),
            )
            for result in results
        ]

        return FAQSearchResponse(
            success=True,
            data=items,
            message=f"Found {len(items)} relevant chunks",
        )
