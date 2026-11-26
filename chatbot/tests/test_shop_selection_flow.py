"""Regression coverage for shop replies in a persisted booking conversation."""

from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from chatbot.app.chat_endpoint import ChatEndpoint, ChatRequest
from chatbot.conversation.state import ConversationPhase, ConversationState
from chatbot.models import (
    CourseInfo,
    SearchAvailableSlotsResponse,
    SearchCoursesResponse,
    SearchShopsResponse,
    ShopInfo,
)
from chatbot.session.store import SessionData
from chatbot.tools.search_tools import SearchAvailableSlotsTool, SearchCoursesTool

SHOPS = [
    ShopInfo(shopId=1, shopName="Shinjuku Store", address="Tokyo", phoneNumber="123",
             status="Open", openTime=time(9), closeTime=time(21)),
    ShopInfo(shopId=2, shopName="Shibuya Store", address="Tokyo", phoneNumber="456",
             status="Open", openTime=time(9), closeTime=time(21)),
]


def make_endpoint(
    sessions: dict[str, SessionData], shops: list[ShopInfo] = SHOPS,
    courses: list[CourseInfo] | None = None,
) -> tuple[ChatEndpoint, MagicMock]:
    store = MagicMock()

    async def get_session(session_id: str) -> SessionData | None:
        saved = sessions.get(session_id)
        return SessionData.model_validate_json(saved.model_dump_json()) if saved else None

    async def create_session(session_id: str, user_id: str | None = None) -> SessionData:
        return SessionData(session_id=session_id, user_id=user_id)

    async def save_session(session: SessionData) -> None:
        sessions[session.session_id] = SessionData.model_validate_json(session.model_dump_json())

    store.get_session = AsyncMock(side_effect=get_session)
    store.create_session = AsyncMock(side_effect=create_session)
    store.save_session = AsyncMock(side_effect=save_session)

    shops_tool = MagicMock()
    shops_tool.execute = AsyncMock(return_value=SearchShopsResponse(
        success=True, data=shops, message="Success"
    ))
    courses_tool = MagicMock()
    courses_tool.execute = AsyncMock(return_value=SearchCoursesResponse(
        success=True,
        data=courses if courses is not None else [
            CourseInfo(courseId=7, courseName="Swedish Massage", duration=60,
                       price=500000, courseType="main", status="Active")
        ],
        message="Success",
    ))
    slots_tool = MagicMock()
    slots_tool.execute = AsyncMock(return_value=SearchAvailableSlotsResponse(
        success=True, data=[], message="Success"
    ))
    registry = MagicMock()
    registry.get.side_effect = lambda name: {
        "searchShops": shops_tool, "searchCourses": courses_tool,
        "searchAvailableSlots": slots_tool,
    }.get(name)

    endpoint = ChatEndpoint(session_store=store, tool_registry=registry)
    endpoint._http_client = MagicMock()
    endpoint._http_client.post = AsyncMock(side_effect=lambda path, json: (
        {"success": True, "data": {"accessToken": "verified-token"}}
        if path.endswith('/verifications') else {"success": True, "data": {"delivery": "terminal"}}
    ))
    endpoint._initialized = True
    return endpoint, registry


@pytest.mark.asyncio
async def test_shop_reply_advances_booking_and_persists_shop() -> None:
    sessions: dict[str, SessionData] = {}
    endpoint, registry = make_endpoint(sessions)

    first = await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))
    assert first.phase == ConversationPhase.SEARCHING_SHOPS

    selected = await endpoint.process_message(
        ChatRequest(message="shinjuku store", session_id="s1")
    )
    state = ConversationState(**sessions["s1"].conversation_state)
    assert state.booking_context.shop_id == 1
    assert selected.phase == ConversationPhase.SEARCHING_COURSES
    assert "which one would you like?" in selected.message.lower()
    assert "Swedish Massage" in selected.message
    registry.get("searchCourses").execute.assert_awaited_once()
    assert registry.get("searchCourses").execute.await_args.args[0].shopId == 1
    assert state.booking_context.course_id is None
    assert state.booking_context.date is None
    assert state.booking_context.start_time is None


@pytest.mark.asyncio
async def test_shop_reply_uses_public_courses_api_shape() -> None:
    sessions: dict[str, SessionData] = {}
    endpoint, registry = make_endpoint(sessions)
    courses_response = {
        "success": True,
        "data": [{
            "courseId": 1,
            "courseName": "Thai Massage",
            "durations": [
                {"duration": 30, "price": 3000},
                {"duration": 60, "price": 6000},
            ],
            "courseType": "main",
        }],
        "message": "Success",
    }
    client = MagicMock()
    client.get = AsyncMock(return_value=courses_response)
    shops_tool = registry.get("searchShops")
    courses_tool = SearchCoursesTool(client)
    registry.get.side_effect = lambda name: {
        "searchShops": shops_tool, "searchCourses": courses_tool
    }.get(name)

    await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))
    response = await endpoint.process_message(
        ChatRequest(message="shinjuku store", session_id="s1")
    )

    assert response.success is True
    assert response.phase == ConversationPhase.SEARCHING_COURSES
    assert "Thai Massage" in response.message
    assert "30min" in response.message
    assert "60min" in response.message
    assert "Which one would you like?" in response.message
    client.get.assert_awaited_once_with("/shops/1/courses", params={})
    state = ConversationState(**sessions["s1"].conversation_state)
    assert state.booking_context.shop_id == 1
    assert state.booking_context.course_id is None
    assert state.booking_context.duration is None


@pytest.mark.asyncio
@pytest.mark.parametrize("reply,shop_id", [
    ("Shinjuku Store", 1),
    ("Shibuya Store", 2),
    ("Shinjuku", 1),
    ("Shibuya", 2),
    ("I'd like Shinjuku", 1),
    ("The first one", 1),
    ("second", 2),
    ("Shop 1", 1),
    ("id: 2", 2),
    ("2", 2),
])
async def test_shop_reply_variations(reply: str, shop_id: int) -> None:
    sessions: dict[str, SessionData] = {}
    endpoint, registry = make_endpoint(sessions)
    await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))

    selected = await endpoint.process_message(ChatRequest(message=reply, session_id="s1"))

    assert selected.phase == ConversationPhase.SEARCHING_COURSES
    assert ConversationState(**sessions["s1"].conversation_state).booking_context.shop_id == shop_id
    assert registry.get("searchCourses").execute.await_args.args[0].shopId == shop_id


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", ["Kyoto Store", "Kyoto", "Shop 99", "the third one"])
async def test_invalid_shop_keeps_question_pending(reply: str) -> None:
    sessions: dict[str, SessionData] = {}
    endpoint, registry = make_endpoint(sessions)
    await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))

    response = await endpoint.process_message(ChatRequest(message=reply, session_id="s1"))

    assert response.phase == ConversationPhase.SEARCHING_SHOPS
    assert "choose" in response.message.lower()
    assert ConversationState(**sessions["s1"].conversation_state).booking_context.shop_id is None
    registry.get("searchCourses").execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_ambiguous_shop_name_requires_clarification() -> None:
    sessions: dict[str, SessionData] = {}
    shops = SHOPS + [SHOPS[0].model_copy(update={"shopId": 3, "shopName": "Shinjuku East Store"})]
    endpoint, registry = make_endpoint(sessions, shops)
    await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))

    ambiguous = await endpoint.process_message(ChatRequest(message="Shinjuku", session_id="s1"))
    assert ambiguous.phase == ConversationPhase.SEARCHING_SHOPS
    assert "more than one" in ambiguous.message.lower()
    assert ConversationState(**sessions["s1"].conversation_state).booking_context.shop_id is None
    registry.get("searchCourses").execute.assert_not_awaited()

    exact = await endpoint.process_message(
        ChatRequest(message="Shinjuku Store", session_id="s1")
    )
    assert exact.phase == ConversationPhase.SEARCHING_COURSES
    assert ConversationState(**sessions["s1"].conversation_state).booking_context.shop_id == 1

    # The longer name must also resolve when shown alongside a shorter prefix.
    endpoint, _ = make_endpoint(sessions, shops)
    await endpoint.process_message(ChatRequest(message="start over", session_id="s1"))
    await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))
    selected = await endpoint.process_message(
        ChatRequest(message="Shinjuku East Store", session_id="s1")
    )
    assert selected.phase == ConversationPhase.SEARCHING_COURSES
    assert ConversationState(**sessions["s1"].conversation_state).booking_context.shop_id == 3


@pytest.mark.asyncio
async def test_shop_reply_after_endpoint_restart_uses_saved_options() -> None:
    sessions: dict[str, SessionData] = {}
    original, _ = make_endpoint(sessions)
    await original.process_message(ChatRequest(message="book a massage", session_id="s1"))

    restored, registry = make_endpoint(sessions)
    selected = await restored.process_message(ChatRequest(message="Shibuya Store", session_id="s1"))

    assert selected.phase == ConversationPhase.SEARCHING_COURSES
    assert ConversationState(**sessions["s1"].conversation_state).booking_context.shop_id == 2
    assert registry.get("searchCourses").execute.await_args.args[0].shopId == 2


@pytest.mark.asyncio
async def test_shop_name_without_pending_question_is_not_selected() -> None:
    sessions: dict[str, SessionData] = {}
    endpoint, registry = make_endpoint(sessions)

    response = await endpoint.process_message(
        ChatRequest(message="Shinjuku Store", session_id="new-session")
    )

    assert response.phase == ConversationPhase.GREETING
    state = ConversationState(**sessions["new-session"].conversation_state)
    assert state.booking_context.shop_id is None
    registry.get("searchCourses").execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_shop_survives_later_booking_turn() -> None:
    sessions: dict[str, SessionData] = {}
    endpoint, registry = make_endpoint(sessions)
    await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))
    await endpoint.process_message(ChatRequest(message="Shinjuku Store", session_id="s1"))

    response = await endpoint.process_message(
        ChatRequest(message="Book a massage tomorrow at 3pm", session_id="s1")
    )

    state = ConversationState(**sessions["s1"].conversation_state)
    assert response.phase == ConversationPhase.SEARCHING_COURSES
    assert state.booking_context.shop_id == 1
    assert state.booking_context.date == (date.today() + timedelta(days=1)).isoformat()
    assert state.booking_context.start_time == "15:00"
    assert state.booking_context.course_id is None
    assert registry.get("searchCourses").execute.await_count == 2
    assert all(
        call.args[0].shopId == 1 for call in registry.get("searchCourses").execute.await_args_list
    )


COURSES = [
    CourseInfo(courseId=1, courseName="Full Body Massage", courseType="main",
               durations=[{"duration": 15, "price": 1500}, {"duration": 30, "price": 3000}]),
    CourseInfo(courseId=2, courseName="Dry Head Spa", courseType="main",
               durations=[{"duration": 15, "price": 1500}]),
    CourseInfo(courseId=3, courseName="Aromatherapy", courseType="main",
               durations=[{"duration": 30, "price": 7000}]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("reply,duration", [
    ("full body massage", None),
    ("full body massage 15m", 15),
    ("I'd like Full Body Massage for 30 minutes", 30),
    ("Course 1, 15min", 15),
    ("the first one", None),
])
async def test_course_reply_keeps_booking_flow(reply: str, duration: int | None) -> None:
    sessions: dict[str, SessionData] = {}
    endpoint, _ = make_endpoint(sessions, courses=COURSES)
    await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))
    await endpoint.process_message(ChatRequest(message="Shinjuku Store", session_id="s1"))

    response = await endpoint.process_message(ChatRequest(message=reply, session_id="s1"))

    state = ConversationState(**sessions["s1"].conversation_state)
    assert response.phase == ConversationPhase.COLLECTING_INFO
    assert state.booking_context.shop_id == 1
    assert state.booking_context.course_id == 1
    assert state.booking_context.course_name == "Full Body Massage"
    assert state.booking_context.duration == duration
    assert ("duration" if duration is None else "date") in response.message.lower()


@pytest.mark.asyncio
async def test_duration_reply_after_course_selection() -> None:
    sessions: dict[str, SessionData] = {}
    endpoint, _ = make_endpoint(sessions, courses=COURSES)
    await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))
    await endpoint.process_message(ChatRequest(message="Shinjuku Store", session_id="s1"))
    await endpoint.process_message(ChatRequest(message="Full Body Massage", session_id="s1"))

    response = await endpoint.process_message(ChatRequest(message="15m", session_id="s1"))

    state = ConversationState(**sessions["s1"].conversation_state)
    assert response.phase == ConversationPhase.COLLECTING_INFO
    assert state.booking_context.course_id == 1
    assert state.booking_context.duration == 15
    assert "date" in response.message.lower()


@pytest.mark.asyncio
async def test_invalid_course_does_not_select_or_lose_shop() -> None:
    sessions: dict[str, SessionData] = {}
    endpoint, _ = make_endpoint(sessions, courses=COURSES)
    await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))
    await endpoint.process_message(ChatRequest(message="Shinjuku Store", session_id="s1"))

    response = await endpoint.process_message(ChatRequest(message="Course 99", session_id="s1"))

    state = ConversationState(**sessions["s1"].conversation_state)
    assert response.phase == ConversationPhase.SEARCHING_COURSES
    assert state.booking_context.shop_id == 1
    assert state.booking_context.course_id is None
    assert "choose" in response.message.lower()


@pytest.mark.asyncio
async def test_course_selection_after_session_restore() -> None:
    sessions: dict[str, SessionData] = {}
    original, _ = make_endpoint(sessions, courses=COURSES)
    await original.process_message(ChatRequest(message="book a massage", session_id="s1"))
    await original.process_message(ChatRequest(message="Shinjuku Store", session_id="s1"))

    restored, _ = make_endpoint(sessions, courses=COURSES)
    response = await restored.process_message(
        ChatRequest(message="full body massage 15m", session_id="s1")
    )

    state = ConversationState(**sessions["s1"].conversation_state)
    assert response.phase == ConversationPhase.COLLECTING_INFO
    assert state.booking_context.course_id == 1
    assert state.booking_context.duration == 15


@pytest.mark.asyncio
async def test_unavailable_duration_is_rejected() -> None:
    sessions: dict[str, SessionData] = {}
    endpoint, _ = make_endpoint(sessions, courses=COURSES)
    await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))
    await endpoint.process_message(ChatRequest(message="Shinjuku Store", session_id="s1"))

    response = await endpoint.process_message(
        ChatRequest(message="Full Body Massage 20m", session_id="s1")
    )

    state = ConversationState(**sessions["s1"].conversation_state)
    assert response.phase == ConversationPhase.COLLECTING_INFO
    assert state.booking_context.course_id == 1
    assert state.booking_context.duration is None
    assert "isn't available" in response.message
    assert "15, 30 minutes" in response.message


@pytest.mark.asyncio
async def test_other_course_and_ambiguous_prefix() -> None:
    sessions: dict[str, SessionData] = {}
    similar = COURSES + [CourseInfo(
        courseId=4, courseName="Full Body Massage Deluxe", courseType="main",
        durations=[{"duration": 60, "price": 9000}],
    )]
    endpoint, _ = make_endpoint(sessions, courses=similar)
    await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))
    await endpoint.process_message(ChatRequest(message="Shinjuku Store", session_id="s1"))

    ambiguous = await endpoint.process_message(ChatRequest(message="Full Body", session_id="s1"))
    assert ambiguous.phase == ConversationPhase.SEARCHING_COURSES
    assert "more than one" in ambiguous.message.lower()
    assert ConversationState(**sessions["s1"].conversation_state).booking_context.course_id is None

    selected = await endpoint.process_message(ChatRequest(message="Dry Head Spa", session_id="s1"))
    state = ConversationState(**sessions["s1"].conversation_state)
    assert selected.phase == ConversationPhase.COLLECTING_INFO
    assert state.booking_context.course_id == 2
    assert state.booking_context.duration is None
    assert "15 minutes" in selected.message


@pytest.mark.asyncio
async def test_remaining_details_reach_slot_search() -> None:
    sessions: dict[str, SessionData] = {}
    endpoint, registry = make_endpoint(sessions, courses=COURSES)
    await endpoint.process_message(ChatRequest(message="book a massage", session_id="s1"))
    await endpoint.process_message(ChatRequest(message="Shinjuku Store", session_id="s1"))
    course = await endpoint.process_message(
        ChatRequest(message="full body massage 15m", session_id="s1")
    )
    assert "date" in course.message.lower()

    booking_date = await endpoint.process_message(ChatRequest(message="tomorrow", session_id="s1"))
    assert "start time" in booking_date.message.lower()
    booking_time = await endpoint.process_message(ChatRequest(message="3pm", session_id="s1"))
    assert "how many people" in booking_time.message.lower()
    await endpoint.process_message(ChatRequest(message="2", session_id="s1"))

    state = ConversationState(**sessions["s1"].conversation_state)
    assert state.phase == ConversationPhase.SEARCHING_SLOTS
    assert state.booking_context.shop_id == 1
    assert state.booking_context.course_id == 1
    assert state.booking_context.duration == 15
    assert state.booking_context.number_of_people == 2
    assert state.booking_context.start_time == "15:00"
    slot_request = registry.get("searchAvailableSlots").execute.await_args.args[0]
    assert slot_request.shopId == 1
    assert slot_request.courseIds == "1"
    assert slot_request.duration == 15
    assert slot_request.numberOfPeople == 2
    assert slot_request.date == date.today() + timedelta(days=1)


@pytest.mark.asyncio
async def test_five_pm_reply_fetches_full_day_for_preference_matching() -> None:
    sessions: dict[str, SessionData] = {}
    endpoint, registry = make_endpoint(sessions, courses=COURSES)
    shops_tool = registry.get("searchShops")
    courses_tool = registry.get("searchCourses")
    client = MagicMock()

    async def get_slots(path: str, params: dict) -> dict:
        assert path == "/shops/1/available-slots"
        assert "startTime" not in params
        return {"success": True, "data": [], "message": "Success"}

    client.get = AsyncMock(side_effect=get_slots)
    slots_tool = SearchAvailableSlotsTool(client)
    registry.get.side_effect = lambda name: {
        "searchShops": shops_tool,
        "searchCourses": courses_tool,
        "searchAvailableSlots": slots_tool,
    }.get(name)

    await endpoint.process_message(
        ChatRequest(message="book a massage for 2 people", session_id="s1")
    )
    await endpoint.process_message(ChatRequest(message="Shinjuku Store", session_id="s1"))
    await endpoint.process_message(ChatRequest(message="Full Body Massage 15m", session_id="s1"))
    await endpoint.process_message(ChatRequest(message="tomorrow", session_id="s1"))
    response = await endpoint.process_message(ChatRequest(message="5pm", session_id="s1"))

    assert response.success is True
    assert response.phase == ConversationPhase.SEARCHING_SLOTS
    assert response.error is None
    assert "startTime" not in client.get.await_args.kwargs["params"]
    state = ConversationState(**sessions["s1"].conversation_state)
    assert state.booking_context.start_time == "17:00"
