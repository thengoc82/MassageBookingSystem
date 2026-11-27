"""Chatbot requests exercised against the real Flask booking routes."""

import json
from datetime import datetime, timedelta

import httpx
import pytest

from app.extensions import db
from app.models import Booking, Course
from app.services import booking_access
from chatbot.app.chat_endpoint import ChatEndpoint, ChatRequest
from chatbot.app.config import Settings
from chatbot.conversation.state import ConversationPhase
from chatbot.gateway.client import HTTPClient
from chatbot.session.store import SessionData
from chatbot.tools.registry import ToolRegistry
from chatbot.tools.search_tools import (
    LookupBookingTool, SearchAvailableSlotsTool, SearchCoursesTool, SearchShopsTool,
)
from chatbot.tools.write_tools import CancelBookingTool, CreateBookingTool, ModifyBookingTool


class MemorySessions:
    def __init__(self):
        self.sessions = {}

    async def get_session(self, session_id):
        saved = self.sessions.get(session_id)
        return SessionData.model_validate_json(saved.model_dump_json()) if saved else None

    async def create_session(self, session_id, user_id=None):
        session = SessionData(session_id=session_id, user_id=user_id)
        await self.save_session(session)
        return session

    async def save_session(self, session):
        self.sessions[session.session_id] = SessionData.model_validate_json(session.model_dump_json())


def make_chat(app):
    calls = []

    def flask_transport(request):
        body = json.loads(request.content) if request.content else None
        response = app.test_client().open(
            request.url.path, method=request.method,
            query_string=request.url.query.decode(),
            json=body, headers=dict(request.headers),
        )
        calls.append((request.method, request.url.path, body, response.status_code))
        return httpx.Response(response.status_code, json=response.get_json())

    gateway = HTTPClient()
    gateway._client = httpx.AsyncClient(
        base_url="http://flask.test/api", transport=httpx.MockTransport(flask_transport),
    )
    registry = ToolRegistry()
    for name, tool in (
        ("searchShops", SearchShopsTool(gateway)),
        ("searchCourses", SearchCoursesTool(gateway)),
        ("searchAvailableSlots", SearchAvailableSlotsTool(gateway)),
        ("lookupBooking", LookupBookingTool(gateway)),
        ("createBooking", CreateBookingTool(gateway)),
        ("modifyBooking", ModifyBookingTool(gateway)),
        ("cancelBooking", CancelBookingTool(gateway)),
    ):
        registry.register(name, tool)
    sessions = MemorySessions()
    chat = ChatEndpoint(
        settings=Settings(openai_api_key=None), http_client=gateway,
        session_store=sessions, tool_registry=registry,
    )
    chat._initialized = True
    return chat, sessions, calls


async def send(chat, message, session="chat-contract"):
    return await chat.process_message(ChatRequest(message=message, session_id=session))


@pytest.mark.asyncio
async def test_named_therapist_booking_reaches_flask_after_confirmation(
    app, sample_shop, sample_courses, sample_therapists,
):
    chat, sessions, calls = make_chat(app)
    booking_date = (datetime.utcnow().date() + timedelta(days=7)).isoformat()

    await send(chat, f"Book a massage for 1 person on {booking_date} at 10am")
    await send(chat, "Test Spa")
    offered = await send(chat, "Full Body 60m")
    assert "10:00" in offered.message
    choice = await send(chat, "yes")
    assert "Therapist B" in choice.message
    await send(chat, "Therapist B")
    confirmation = await send(chat, "0901234567")
    assert confirmation.phase == ConversationPhase.CONFIRMING_ACTION
    assert "therapist" in confirmation.message.lower()
    rechoice = await send(chat, "change therapist")
    assert rechoice.phase == ConversationPhase.SELECTING_THERAPIST
    confirmation = await send(chat, "Therapist B")
    assert confirmation.phase == ConversationPhase.CONFIRMING_ACTION
    assert not [call for call in calls if call[:2] == ("POST", "/api/bookings")]

    booked = await send(chat, "yes")
    assert booked.phase == ConversationPhase.BOOKING_COMPLETE
    assert "Therapist B" in booked.message
    posts = [call for call in calls if call[:2] == ("POST", "/api/bookings")]
    assert len(posts) == 1 and posts[0][3] == 201
    payload = posts[0][2]
    assert payload["therapistPreferenceType"] == "specific"
    assert payload["therapistPreferenceValue"] == sample_therapists[1].id
    assert payload["selectedCourses"] == [
        {"courseId": sample_courses[0].id, "duration": 60, "price": 6000}
    ]
    assert Booking.query.one().therapist_id == sample_therapists[1].id


@pytest.mark.asyncio
async def test_verified_chat_edit_and_cancel_use_flask_ownership(
    app, sample_shop, sample_courses, sample_therapists, monkeypatch,
):
    from test_booking_access import FakeRedis

    redis = FakeRedis()
    sent_codes = []
    monkeypatch.setattr(booking_access, "_redis", lambda: redis)
    monkeypatch.setattr(booking_access, "_deliver_code", lambda phone, code: sent_codes.append(code) or "fake")
    chat, _, calls = make_chat(app)
    booking_date = (datetime.utcnow().date() + timedelta(days=7)).isoformat()
    created = app.test_client().post("/api/bookings", json={
        "phoneNumber": "0901234567", "shopId": sample_shop.id,
        "bookingDate": booking_date, "startTime": "10:00", "duration": 60,
        "numberOfPeople": 1, "courseId": sample_courses[0].id,
    }).get_json()["data"]
    code = created["bookingCode"]

    challenge = await send(chat, f"Modify my booking {code} 0901234567")
    assert "verification code" in challenge.message
    verified = await send(chat, sent_codes[-1])
    assert "new date or exact start time" in verified.message
    pending = await send(chat, "11:00")
    assert pending.booking_progress["requires_confirmation"] is True
    assert Booking.query.one().start_time.strftime("%H:%M") == "10:00"
    updated = await send(chat, "yes")
    assert updated.phase == ConversationPhase.ACTION_COMPLETE
    assert Booking.query.one().start_time.strftime("%H:%M") == "11:00"

    await send(chat, f"Cancel my booking {code} 0901234567")
    pending_cancel = await send(chat, "yes")
    assert pending_cancel.phase == ConversationPhase.ACTION_COMPLETE
    assert Booking.query.one().status == "Cancelled"
    writes = [(method, path) for method, path, _, _ in calls if method == "PATCH"]
    assert writes == [("PATCH", f"/api/bookings/{created['bookingId']}"),
                      ("PATCH", f"/api/bookings/{created['bookingId']}/cancel")]


@pytest.mark.asyncio
async def test_group_courses_and_addon_survive_chat_confirmation(
    app, sample_shop, sample_courses, sample_therapists,
):
    addon = Course(
        shop_id=sample_shop.id, name="Aroma Addon", duration=15, price=1500,
        course_type="addon", status="active",
    )
    db.session.add(addon)
    db.session.commit()
    chat, _, calls = make_chat(app)
    booking_date = (datetime.utcnow().date() + timedelta(days=7)).isoformat()

    await send(chat, f"Book a massage for 2 people on {booking_date} at 10am")
    await send(chat, "Test Spa")
    await send(chat, "Full Body 60m")
    await send(chat, "add Head Spa 30 min 3,000 VND")
    await send(chat, "add Aroma Addon 15 min 1,500 VND")
    await send(chat, "10am")
    await send(chat, "yes")
    confirmation = await send(chat, "0901234567")
    assert "105 minutes" in confirmation.message
    booked = await send(chat, "yes")
    assert booked.phase == ConversationPhase.BOOKING_COMPLETE
    payload = [call[2] for call in calls if call[:2] == ("POST", "/api/bookings")][0]
    assert payload["duration"] == 105
    assert payload["numberOfPeople"] == 2
    assert payload["services"] == [
        {"personIndex": 1, "courseId": sample_courses[0].id},
        {"personIndex": 1, "courseId": sample_courses[1].id},
        {"personIndex": 2, "courseId": sample_courses[0].id},
        {"personIndex": 2, "courseId": sample_courses[1].id},
    ]
    assert payload["addOns"] == [
        {"personIndex": 1, "courseId": addon.id},
        {"personIndex": 2, "courseId": addon.id},
    ]
    assert payload["selectedCourses"] == [
        {"courseId": sample_courses[0].id, "duration": 60, "price": 6000},
        {"courseId": sample_courses[1].id, "duration": 30, "price": 3000},
        {"courseId": addon.id, "duration": 15, "price": 1500},
    ]
    assert len(Booking.query.one().services) == 4
    assert len(Booking.query.one().addons) == 2


@pytest.mark.asyncio
async def test_flask_blocked_customer_rejection_keeps_chat_draft(
    app, sample_shop, sample_courses, sample_therapists, sample_customer,
):
    chat, sessions, calls = make_chat(app)
    booking_date = (datetime.utcnow().date() + timedelta(days=7)).isoformat()
    await send(chat, f"Book a massage for 2 people on {booking_date} at 10am")
    await send(chat, "Test Spa")
    await send(chat, "Full Body 60m")
    await send(chat, "yes")
    await send(chat, sample_customer.phone_number)
    sample_customer.is_blocked = True
    db.session.commit()

    rejected = await send(chat, "yes")
    assert rejected.phase != ConversationPhase.BOOKING_COMPLETE
    assert "not created" in rejected.message
    assert Booking.query.count() == 0
    assert sessions.sessions["chat-contract"].conversation_state["booking_context"]["shop_id"] == sample_shop.id
    assert [call[3] for call in calls if call[:2] == ("POST", "/api/bookings")] == [422]


@pytest.mark.asyncio
async def test_gender_choice_filters_slots_and_reaches_flask(
    app, sample_shop, sample_courses, sample_therapists,
):
    chat, _, calls = make_chat(app)
    booking_date = (datetime.utcnow().date() + timedelta(days=7)).isoformat()
    await send(chat, f"Book a massage for 1 person on {booking_date} at 10am")
    await send(chat, "Test Spa")
    await send(chat, "Full Body 60m")
    await send(chat, "yes")
    await send(chat, "Female")
    await send(chat, "0901234567")
    booked = await send(chat, "yes")
    assert booked.phase == ConversationPhase.BOOKING_COMPLETE
    slot_queries = [call for call in calls if call[:2] == ("GET", f"/api/shops/{sample_shop.id}/available-slots")]
    assert len(slot_queries) >= 3
    posts = [call for call in calls if call[:2] == ("POST", "/api/bookings")]
    assert posts[0][2]["therapistPreferenceType"] == "gender"
    assert posts[0][2]["therapistPreferenceValue"] == "Female"
    assert Booking.query.one().therapist.gender == "Female"


@pytest.mark.asyncio
async def test_verified_other_phone_cannot_cancel_booking(
    app, sample_shop, sample_courses, sample_therapists, monkeypatch,
):
    from test_booking_access import FakeRedis

    redis = FakeRedis()
    sent_codes = []
    monkeypatch.setattr(booking_access, "_redis", lambda: redis)
    monkeypatch.setattr(booking_access, "_deliver_code", lambda phone, code: sent_codes.append(code) or "fake")
    created = app.test_client().post("/api/bookings", json={
        "phoneNumber": "0901234567", "shopId": sample_shop.id,
        "bookingDate": (datetime.utcnow().date() + timedelta(days=7)).isoformat(),
        "startTime": "10:00", "duration": 60, "courseId": sample_courses[0].id,
    }).get_json()["data"]
    chat, _, calls = make_chat(app)

    await send(chat, f"Cancel my booking {created['bookingCode']} 0987654321")
    denied = await send(chat, sent_codes[-1])

    assert "couldn't find" in denied.message
    assert Booking.query.one().status == "Booked"
    assert not [call for call in calls if call[0] == "PATCH"]
