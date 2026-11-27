from datetime import date
from unittest.mock import AsyncMock

import pytest

from chatbot.app.chat_endpoint import ChatRequest
from chatbot.conversation.state import ConversationPhase, ConversationState
from chatbot.models import CourseInfo, CreateBookingRequest
from chatbot.models.conversation import Conversation
from chatbot.gateway.client import HTTPClient
from chatbot.tests.test_shop_selection_flow import make_endpoint
from chatbot.tools.write_tools import CreateBookingTool


CATALOG = [
    CourseInfo(courseId=1, courseName='Main Massage', courseType='main',
               durations=[{'duration': 30, 'price': 3000}]),
    CourseInfo(courseId=2, courseName='Second Massage', courseType='main',
               durations=[{'duration': 15, 'price': 1500}]),
    CourseInfo(courseId=3, courseName='Head Extra', courseType='addon',
               durations=[{'duration': 15, 'price': 500}]),
    CourseInfo(courseId=4, courseName='Invalid Extra', courseType='addon',
               durations=[{'duration': 0, 'price': 100}]),
]


@pytest.mark.asyncio
async def test_chat_catalog_rejects_addon_as_main_and_preserves_group_options():
    sessions = {}
    endpoint, _ = make_endpoint(sessions, courses=CATALOG)
    async def send(message):
        return await endpoint.process_message(ChatRequest(message=message, session_id='s1'))

    await send('book a massage')
    listed = await send('Shinjuku Store')
    assert 'optional add-on' in listed.message
    assert 'Invalid Extra' not in listed.message
    rejected = await send('Head Extra')
    assert 'add-on' in rejected.message
    assert ConversationState(**sessions['s1'].conversation_state).booking_context.course_id is None

    await send('Main Massage 30m')
    await send('add Second Massage 15 min 1,500 VND')
    await send('add Head Extra 15 min 500 VND')
    state = ConversationState(**sessions['s1'].conversation_state)
    assert state.booking_context.duration == 60
    assert [item['courseId'] for item in state.booking_context.selected_course_options] == [1, 2, 3]
    state.booking_context.date = date.today().isoformat()
    state.booking_context.start_time = '10:00'
    state.booking_context.number_of_people = 2
    state.booking_context.phone_number = '0901234567'
    state.phase = ConversationPhase.COLLECTING_PHONE
    endpoint._prepare_booking_confirmation(state, Conversation())
    payload = CreateBookingRequest.model_validate(state.pending_action.arguments)
    assert payload.duration == 60
    assert [(item.personIndex, item.courseId) for item in payload.services] == [(1, 1), (1, 2), (2, 1), (2, 2)]
    assert [(item.personIndex, item.courseId) for item in payload.addOns] == [(1, 3), (2, 3)]
    assert [(item.courseId, item.duration, item.price) for item in payload.selectedCourses] == [(1, 30, 3000), (2, 15, 1500), (3, 15, 500)]

    client = AsyncMock(spec=HTTPClient)
    client.post.return_value = {'success': True, 'data': {'bookingId': 9, 'bookingCode': 'BK202611270001'}}
    await CreateBookingTool(client).execute(payload)
    sent = client.post.await_args.kwargs['json']
    assert sent['duration'] == 60
    assert sent['selectedCourses'] == [
        {'courseId': 1, 'duration': 30, 'price': 3000},
        {'courseId': 2, 'duration': 15, 'price': 1500},
        {'courseId': 3, 'duration': 15, 'price': 500},
    ]
    assert sent['addOns'] == [{'personIndex': 1, 'courseId': 3}, {'personIndex': 2, 'courseId': 3}]


@pytest.mark.asyncio
async def test_chat_asks_for_price_when_duration_has_two_catalog_prices():
    sessions = {}
    endpoint, _ = make_endpoint(sessions, courses=[CourseInfo(
        courseId=1, courseName='Main Massage', courseType='main',
        durations=[{'duration': 30, 'price': 3000}, {'duration': 30, 'price': 3500}],
    )])
    async def send(message):
        return await endpoint.process_message(ChatRequest(message=message, session_id='s1'))

    await send('book a massage')
    await send('Shinjuku Store')
    ambiguous = await send('Main Massage 30m')
    assert 'exact option' in ambiguous.message
    chosen = await send('3500 VND')
    assert 'date' in chosen.message.lower()
    state = ConversationState(**sessions['s1'].conversation_state)
    assert state.booking_context.selected_course_options[0]['price'] == 3500


@pytest.mark.asyncio
async def test_duration_correction_cannot_confirm_stale_multi_course_draft():
    sessions = {}
    endpoint, _ = make_endpoint(sessions, courses=CATALOG)

    async def send(message):
        return await endpoint.process_message(ChatRequest(message=message, session_id='s1'))

    await send('book a massage')
    await send('Shinjuku Store')
    await send('Main Massage 30m')
    await send('add Second Massage 15 min 1,500 VND')
    await send('add Head Extra 15 min 500 VND')
    state = ConversationState(**sessions['s1'].conversation_state)
    state.booking_context.date = date.today().isoformat()
    state.booking_context.start_time = '10:00'
    state.booking_context.number_of_people = 2
    state.booking_context.phone_number = '0901234567'
    state.phase = ConversationPhase.COLLECTING_PHONE
    endpoint._prepare_booking_confirmation(state, Conversation())
    sessions['s1'].conversation_state = state.model_dump()

    reply = await send('Actually make it 90 minutes for 3 people')

    revised = ConversationState(**sessions['s1'].conversation_state)
    assert 'change the course selection' in reply.message
    assert revised.pending_action is None
    assert revised.booking_context.duration == 60
    assert revised.booking_context.number_of_people == 2
    assert len(revised.booking_context.selected_course_options) == 3
