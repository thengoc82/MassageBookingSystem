# chatbot/tests/test_slot_manager.py
import pytest
from unittest.mock import MagicMock, AsyncMock

from chatbot.conversation.slot_filling import SlotFillingManager
from chatbot.conversation.state import ConversationState, BookingContext, RecentToolResults
from chatbot.nlu.nlu import NLU
from chatbot.nlu.models import NLUResult, Entity, EntityType, Intent
from chatbot.models import ShopInfo

@pytest.fixture
def nlu_mock():
    return MagicMock(spec=NLU)

@pytest.fixture
def conversation_manager_mock():
    return MagicMock()

@pytest.fixture
def slot_manager(conversation_manager_mock, nlu_mock):
    return SlotFillingManager(conversation_manager_mock, nlu_mock)

@pytest.fixture
def initial_state():
    return ConversationState()

@pytest.mark.asyncio
async def test_date_validation_in_past(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    """Test that a date in the past fails validation."""
    action = "search_slots"
    initial_state.booking_context.shop_id = 1
    initial_state.booking_context.course_id = 101
    initial_state.booking_context.duration = 60
    
    await slot_manager.start(initial_state, action)
    assert initial_state.pending_slot_to_fill == "date"

    # Provide a date that is in the past
    past_date = "2020-01-01"
    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[
        Entity(type=EntityType.DATE, value=past_date)
    ])
    
    complete, message, _ = await slot_manager.continue_filling(initial_state, past_date)
    
    assert complete is False
    assert "seems invalid" in message
    # The slot should not be filled
    assert initial_state.booking_context.date is None
    # We should still be waiting for the date
    assert initial_state.pending_slot_to_fill == "date"
    assert initial_state.slot_fill_retries == 1

@pytest.mark.asyncio
async def test_date_validation_in_future(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    """Test that a date in the future passes validation."""
    action = "search_slots"
    initial_state.booking_context.shop_id = 1
    initial_state.booking_context.course_id = 101
    initial_state.booking_context.duration = 60
    
    await slot_manager.start(initial_state, action)
    assert initial_state.pending_slot_to_fill == "date"

    # Provide a date that is in the future
    future_date = "2030-01-01"
    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[
        Entity(type=EntityType.DATE, value=future_date)
    ])
    
    complete, message, _ = await slot_manager.continue_filling(initial_state, future_date)
    
    assert complete is False
    assert initial_state.booking_context.date == future_date
    # Now we should be asking for the next slot
    assert initial_state.pending_slot_to_fill == "number_of_people"
    assert "how many guests" in message.lower()
    assert initial_state.slot_fill_retries == 0

@pytest.mark.asyncio
async def test_nlu_entities_are_applied(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    """Check if entities from NLU are correctly applied."""
    action = "search_slots"
    await slot_manager.start(initial_state, action)

    initial_state.recent_tool_results.last_shop_search = {"data": [
        ShopInfo(shopId=123, shopName="Shibuya", address="a", phoneNumber="p", status="s", openTime="10:00", closeTime="22:00"),
    ]}
    
    nlu_result = NLUResult(
        intent=Intent.CREATE_BOOKING,
        entities=[
            Entity(type=EntityType.SHOP_NAME, value="Shibuya"),
            Entity(type=EntityType.DATE, value="2030-01-01"),
        ]
    )
    
    nlu_mock.understand.return_value = nlu_result
    
    await slot_manager.continue_filling(initial_state, "Book at Shibuya for tomorrow")
    
    context = initial_state.booking_context
    assert context.shop_id == 123
    assert context.shop_name == "Shibuya"
    assert context.date == "2030-01-01"

@pytest.mark.asyncio
async def test_date_parsing_with_base_date(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    """Test that date parsing uses the base_date from the context."""
    action = "search_slots"
    initial_state.booking_context.date = "2030-01-10" # Set a base date in the future
    await slot_manager.start(initial_state, action)
    
    # "tomorrow" should be parsed relative to the base_date
    nlu_mock.understand.return_value = NLUResult(
        intent=Intent.PROVIDE_INFORMATION,
        entities=[Entity(type=EntityType.DATE, value="tomorrow")]
    )
    
    await slot_manager.continue_filling(initial_state, "tomorrow")
    
    assert initial_state.booking_context.date == "2030-01-11"
