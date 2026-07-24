from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from app.config import Settings
from conversation.state import (
    ConversationManager,
    ConversationPhase,
    ConversationState,
)
from gateway.client import HTTPClient, create_client
from models import (
    CheckEligibilityRequest,
    FAQSearchRequest,
    GetTherapistsRequest,
    LookupBookingRequest,
    SearchAvailableSlotsRequest,
    SearchCoursesRequest,
    SearchShopsRequest,
)
from session.store import RedisSessionStore
from tools.registry import ToolRegistry
from tools.search_tools import (
    CheckEligibilityTool,
    FAQSearchTool,
    GetTherapistsTool,
    LookupBookingTool,
    SearchAvailableSlotsTool,
    SearchCoursesTool,
    SearchShopsTool,
)


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: str
    user_id: str | None = None


class ChatResponse(BaseModel):
    """Chat response model."""
    success: bool
    message: str
    session_id: str
    phase: ConversationPhase
    data: Any = None
    error: str | None = None


@dataclass
class IntentResponse:
    """Internal response from intent handler."""
    success: bool
    message: str
    state: ConversationState
    data: Any = None
    error: str | None = None


class ChatEndpoint:
    """Web chat endpoint handler."""

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: HTTPClient | None = None,
        session_store: RedisSessionStore | None = None,
        conversation_manager: ConversationManager | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self._settings = settings or Settings()
        self._http_client = http_client
        self._session_store = session_store
        self._conversation_manager = conversation_manager or ConversationManager()
        self._tool_registry = tool_registry
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all components."""
        if self._initialized:
            return

        self._http_client = await create_client()
        self._session_store = RedisSessionStore(self._settings)
        self._tool_registry = ToolRegistry()

        # Register all tools
        self._tool_registry.register("searchShops", SearchShopsTool(self._http_client))
        self._tool_registry.register("searchCourses", SearchCoursesTool(self._http_client))
        self._tool_registry.register("searchAvailableSlots", SearchAvailableSlotsTool(self._http_client))
        self._tool_registry.register("getTherapists", GetTherapistsTool(self._http_client))
        self._tool_registry.register("lookupBooking", LookupBookingTool(self._http_client))
        self._tool_registry.register("checkEligibility", CheckEligibilityTool(self._http_client))
        self._tool_registry.register("faqSearch", FAQSearchTool(self._http_client))

        self._initialized = True

    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.close()
        if self._session_store:
            await self._session_store.close()
        self._initialized = False

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """Process a chat message."""
        await self.initialize()

        # Get or create session
        session_store = self._session_store
        assert session_store is not None
        session = await session_store.get_session(request.session_id)
        if session is None:
            session = await session_store.create_session(request.session_id, request.user_id)

        # Get conversation state
        state_dict = session.conversation_state
        if not state_dict:
            state = ConversationState()
        else:
            state = ConversationState(**state_dict)

        # Parse intent from message (deterministic for Phase 1)
        intent = self._parse_intent(request.message, state)

        # Handle intent
        response = await self._handle_intent(intent, request.message, state, session.session_id)

        # Save updated state
        session.conversation_state = response.state.model_dump()
        await session_store.save_session(session)

        return ChatResponse(
            success=response.success,
            message=response.message,
            session_id=session.session_id,
            phase=response.state.phase,
            data=response.data,
            error=response.error,
        )

    def _parse_intent(self, message: str, state: ConversationState) -> str:
        """Parse user intent from message (deterministic keyword matching for Phase 1)."""
        message_lower = message.lower()

        # Check for explicit tool requests
        if any(keyword in message_lower for keyword in ["shop", "branch", "location"]) and state.phase == ConversationPhase.GREETING:
            return "search_shops"
        if ("course" in message_lower or "service" in message_lower or "massage" in message_lower) and state.phase in (ConversationPhase.GREETING, ConversationPhase.SEARCHING_SHOPS):
            return "search_courses"
        if ("slot" in message_lower or "time" in message_lower or "available" in message_lower) and state.phase in (ConversationPhase.SEARCHING_COURSES, ConversationPhase.SEARCHING_SLOTS):
            return "search_slots"
        if "therapist" in message_lower and state.phase in (ConversationPhase.SEARCHING_SLOTS, ConversationPhase.SELECTING_THERAPIST):
            return "get_therapists"
        if ("eligibility" in message_lower or "blocked" in message_lower or "phone" in message_lower) and state.phase == ConversationPhase.SELECTING_THERAPIST:
            return "check_eligibility"
        if "booking" in message_lower and ("lookup" in message_lower or "check" in message_lower) and state.phase == ConversationPhase.GREETING:
            return "lookup_booking"
        if "faq" in message_lower or "question" in message_lower or "help" in message_lower:
            return "faq_search"
        if "reset" in message_lower or "start over" in message_lower:
            return "reset"

        return "unknown"

    async def _handle_intent(
        self,
        intent: str,
        message: str,
        state: ConversationState,
        session_id: str,
    ) -> IntentResponse:
        """Handle parsed intent."""
        assert self._tool_registry is not None

        if intent == "reset":
            state = self._conversation_manager.reset(state)
            return IntentResponse(True, "Conversation reset. How can I help you?", state)

        if intent == "search_shops":
            state, ok = self._conversation_manager.transition(state, "search_shops")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("searchShops")
            shops_request = SearchShopsRequest()
            result = await tool.execute(shops_request)
            state.last_tool_result = result.model_dump(mode="json")
            if result.success:
                shops = result.data
                msg = f"Found {len(shops)} shops:\n" + "\n".join(
                    f"- {s.shopName} ({s.address})" for s in shops
                )
            else:
                msg = f"Error: {result.message}"
            return IntentResponse(True, msg, state, state.last_tool_result)

        if intent == "search_courses":
            # Need shop_id from context
            shop_id = state.booking_context.shop_id
            if not shop_id:
                return IntentResponse(False, "Please select a shop first", state)

            state, ok = self._conversation_manager.transition(state, "select_shop")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("searchCourses")
            courses_request = SearchCoursesRequest(shopId=shop_id)
            result = await tool.execute(courses_request)
            state.last_tool_result = result.model_dump(mode="json")
            if result.success:
                courses = result.data
                msg = f"Found {len(courses)} courses:\n" + "\n".join(
                    f"- {c.courseName} ({c.duration}min, {c.price:,}đ)" for c in courses
                )
            else:
                msg = f"Error: {result.message}"
            return IntentResponse(True, msg, state, state.last_tool_result)

        if intent == "search_slots":
            context = state.booking_context
            required = ["shop_id", "course_id", "date", "duration", "number_of_people"]
            missing = [k for k in required if getattr(context, k) is None]
            if missing:
                return IntentResponse(False, f"Missing: {', '.join(missing)}", state)

            state, ok = self._conversation_manager.transition(state, "select_course")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("searchAvailableSlots")
            from datetime import date as date_type, time as time_type
            slots_request = SearchAvailableSlotsRequest(
                shopId=context.shop_id or 0,
                date=date_type.fromisoformat(context.date) if context.date else date_type.today(),
                duration=context.duration or 60,
                numberOfPeople=context.number_of_people or 1,
                courseIds=str(context.course_id),
            )
            result = await tool.execute(slots_request)
            state.last_tool_result = result.model_dump(mode="json")
            if result.success:
                slots = result.data
                msg = f"Found {len(slots)} available slots:\n" + "\n".join(
                    f"- {s.startTime}-{s.endTime} (capacity: {s.availableCapacity})" for s in slots
                )
            else:
                msg = f"Error: {result.message}"
            return IntentResponse(True, msg, state, state.last_tool_result)

        if intent == "get_therapists":
            context = state.booking_context
            required = ["shop_id", "date", "start_time"]
            missing = [k for k in required if getattr(context, k) is None]
            if missing:
                return IntentResponse(False, f"Missing: {', '.join(missing)}", state)

            state, ok = self._conversation_manager.transition(state, "select_slot")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("getTherapists")
            from datetime import date as date_type, time as time_type
            therapists_request = GetTherapistsRequest(
                shopId=context.shop_id or 0,
                date=date_type.fromisoformat(context.date) if context.date else date_type.today(),
                startTime=time_type.fromisoformat(context.start_time) if context.start_time else time_type(9, 0),
                duration=context.duration or 60,
            )
            result = await tool.execute(therapists_request)
            state.last_tool_result = result.model_dump(mode="json")
            if result.success:
                therapists = result.data
                msg = "Available therapists:\n" + "\n".join(
                    f"- {t.name} ({t.gender}) - {'Available' if t.isAvailable else 'Busy'}" for t in therapists
                )
            else:
                msg = f"Error: {result.message}"
            return IntentResponse(True, msg, state, state.last_tool_result)

        if intent == "check_eligibility":
            phone = state.booking_context.phone_number
            if not phone:
                return IntentResponse(False, "Please provide your phone number", state)

            state, ok = self._conversation_manager.transition(state, "select_therapist")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("checkEligibility")
            eligibility_request = CheckEligibilityRequest(phoneNumber=phone)
            result = await tool.execute(eligibility_request)
            state.last_tool_result = result.model_dump(mode="json")
            if result.success:
                data = result.data
                if data.isEligible:
                    msg = f"Eligible! Member rank: {data.memberRank or 'N/A'}, Visits: {data.visitCount}"
                else:
                    msg = f"Not eligible: {data.blockReason or 'Blocked'}"
            else:
                msg = f"Error: {result.message}"
            return IntentResponse(True, msg, state, state.last_tool_result)

        if intent == "lookup_booking":
            # Extract booking code from message
            import re
            booking_code_match = re.search(r"BK\d{12}", message.upper())
            if not booking_code_match:
                return IntentResponse(False, "Please provide a booking code (format: BKYYYYMMDDXXXX)", state)

            booking_code = booking_code_match.group(0)
            state, ok = self._conversation_manager.transition(state, "lookup_booking")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("lookupBooking")
            lookup_request = LookupBookingRequest(bookingCode=booking_code)
            result = await tool.execute(lookup_request)
            state.last_tool_result = result.model_dump(mode="json")
            if result.success:
                bookings = result.data
                if bookings:
                    b = bookings[0]
                    msg = f"Booking {b.bookingCode}: {b.shopName} on {b.bookingDate} at {b.startTime} - {b.status}"
                else:
                    msg = "No booking found with that code"
            else:
                msg = f"Error: {result.message}"
            return IntentResponse(True, msg, state, state.last_tool_result)

        if intent == "faq_search":
            state, ok = self._conversation_manager.transition(state, "faq_search")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("faqSearch")
            faq_request = FAQSearchRequest(query=message)
            result = await tool.execute(faq_request)
            state.last_tool_result = result.model_dump(mode="json")
            msg = result.message
            return IntentResponse(True, msg, state, state.last_tool_result)

        return IntentResponse(
            False,
            "I didn't understand that. Try: search shops, search courses, search slots, get therapists, check eligibility, lookup booking, or faq search.",
            state,
        )


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(title="Chatbot Service", version="1.0.0")
    chat_endpoint = ChatEndpoint()

    @app.on_event("startup")
    async def startup() -> None:
        await chat_endpoint.initialize()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await chat_endpoint.close()

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        return await chat_endpoint.process_message(request)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app