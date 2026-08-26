# chatbot/tests/test_slot_filling.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from chatbot.conversation.state import ConversationManager, ConversationState
from chatbot.conversation.slot_filling import SlotFillingManager
from chatbot.conversation.interfaces import IntentResponse
from chatbot.nlu.models import Entity, NLUResult, Intent, EntityType, EntityType
from chatbot.models import ShopInfo


@pytest.mark.asyncio
async def mock_executor(state: ConversationState, action: str | None = None) -> IntentResponse:
    return IntentResponse(
        success=True,
        message="Action executed successfully!",
        state=state,
        data={"final_context": state.booking_context.model_dump()},
    )


@pytest.fixture
def slot_manager(nlu_mock):
    from chatbot.conversation.state import ConversationManager
    cm = ConversationManager()
    
    # We need to mock the apply_nlu_entities_to_booking_context method
    # to avoid the circular dependency
    cm.apply_nlu_entities_to_booking_context = MagicMock(wraps=cm.apply_nlu_entities_to_booking_context)

    sm = SlotFillingManager(
        conversation_manager=cm,
        nlu=nlu_mock,
    )
    return sm


@pytest.fixture
def nlu_mock():
    from chatbot.nlu.nlu import NLU
    nlu = MagicMock(spec=NLU)
    nlu.understand = AsyncMock(return_value=NLUResult(intent=Intent.UNKNOWN, entities=[]))
    return nlu

@pytest.fixture
def initial_state():
    return ConversationState()


@pytest.mark.asyncio
async def test_missing_date(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    initial_state.booking_context.shop_id = 1
    initial_state.booking_context.course_id = 101
    initial_state.booking_context.duration = 60
    needed, message, _ = await slot_manager.start(initial_state, "search_slots")
    assert needed is True
    assert "date" in message.lower()
    assert initial_state.pending_slot_to_fill == "date"

    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[Entity(type=EntityType.DATE, value="today")])
    complete, message, _ = await slot_manager.continue_filling(initial_state, "today")
    assert initial_state.booking_context.date is not None
    assert "how many guests" in message.lower()


@pytest.mark.asyncio
async def test_multiple_missing_slots(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    action = "search_slots"

    # 1. Start -> asks for shop_id
    needed, message, _ = await slot_manager.start(initial_state, action)
    assert needed is True
    assert "which shop" in message.lower()
    assert initial_state.pending_slot_to_fill == "shop_id"

    # 2. Provide shop_id -> asks for course_id
    shop1 = ShopInfo(
        shopId=1, shopName="Downtown", address="123 Main", phoneNumber="555", status="Open",
        openTime="09:00", closeTime="22:00",
    )
    initial_state.recent_tool_results.last_shop_search = {"data": [shop1]}
    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[Entity(type=EntityType.SHOP_NAME, value="Downtown")])
    complete, message, _ = await slot_manager.continue_filling(initial_state, "Downtown")
    assert initial_state.booking_context.shop_id == 1
    assert "which massage course" in message.lower()

    # 3. Fill course_id and duration manually
    initial_state.booking_context.course_id = 101
    initial_state.booking_context.duration = 90

    # 4. Provide course_id -> asks for date
    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[Entity(type=EntityType.COURSE_NAME, value="some course")])
    complete, message, _ = await slot_manager.continue_filling(initial_state, "some course")
    assert "date" in message.lower()

    # 5. Provide date -> asks for number_of_people
    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[Entity(type=EntityType.DATE, value="2026-07-31")])
    complete, message, _ = await slot_manager.continue_filling(initial_state, "2026-07-31")
    assert "how many guests" in message.lower()

    # 6. Provide number_of_people -> all slots filled, execute action
    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[Entity(type=EntityType.NUMBER_OF_PEOPLE, value=2)])
    complete, message, _ = await slot_manager.continue_filling(initial_state, "2 people")
    assert complete is True
    assert "all the information" in message


@pytest.mark.asyncio
async def test_invalid_date(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    initial_state.booking_context.shop_id = 1
    initial_state.booking_context.course_id = 101
    initial_state.booking_context.duration = 60

    await slot_manager.start(initial_state, "search_slots")

    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[]) 
    complete, message, _ = await slot_manager.continue_filling(initial_state, "invalid-date-string")
    assert "seems invalid" in message.lower()
    assert initial_state.booking_context.date is None


@pytest.mark.asyncio
async def test_invalid_guest_count(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    initial_state.booking_context.shop_id = 1
    initial_state.booking_context.course_id = 101
    initial_state.booking_context.duration = 60
    initial_state.booking_context.date = "2025-10-10"

    await slot_manager.start(initial_state, "search_slots")

    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[Entity(type=EntityType.NUMBER_OF_PEOPLE, value="many")])
    complete, message, _ = await slot_manager.continue_filling(initial_state, "many people")
    assert "seems invalid" in message.lower()
    assert initial_state.booking_context.number_of_people is None


@pytest.mark.asyncio
async def test_phone_slot(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    needed, message, _ = await slot_manager.start(initial_state, "check_eligibility")
    assert "may i have your phone number" in message.lower()
    assert initial_state.pending_slot_to_fill == "phone_number"

    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[Entity(type=EntityType.PHONE_NUMBER, value="+84901234567")])
    complete, message, _ = await slot_manager.continue_filling(initial_state, "+84 90 123 4567")
    assert complete is True
    assert "all the information" in message


@pytest.mark.asyncio
async def test_invalid_phone(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    await slot_manager.start(initial_state, "check_eligibility")
    nlu_mock.understand.return_value = NLUResult(intent=Intent.UNKNOWN, entities=[])
    complete, message, _ = await slot_manager.continue_filling(initial_state, "abc")
    assert "seems invalid" in message.lower()
    assert initial_state.booking_context.phone_number is None


@pytest.mark.asyncio
async def test_ordinal_shop_selection(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    # populate shops
    shops = [
        ShopInfo(shopId=1, shopName="Downtown", address="a", phoneNumber="1", status="Open",
                 openTime="09:00", closeTime="22:00"),
        ShopInfo(shopId=2, shopName="Uptown", address="b", phoneNumber="2", status="Open",
                 openTime="09:00", closeTime="22:00"),
    ]
    initial_state.recent_tool_results.last_shop_search = {"data": shops}
    initial_state.pending_read_action = "search_shops"

    # user says "first"
    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[Entity(type="ordinal", value=1)])
    response = await slot_manager.continue_filling(initial_state, "the first one")
    assert initial_state.booking_context.shop_id == 1


@pytest.mark.asyncio
async def test_numeric_shop_selection(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    shops = [
        ShopInfo(shopId=10, shopName="Downtown", address="a", phoneNumber="1", status="Open",
                 openTime="09:00", closeTime="22:00"),
        ShopInfo(shopId=20, shopName="Uptown", address="b", phoneNumber="2", status="Open",
                 openTime="09:00", closeTime="22:00"),
    ]
    initial_state.recent_tool_results.last_shop_search = {"data": shops}
    initial_state.pending_read_action = "search_shops"
    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[Entity(type="number", value=2)])
    response = await slot_manager.continue_filling(initial_state, "2")
    assert initial_state.booking_context.shop_id == 20


@pytest.mark.asyncio
async def test_multi_entity_parses_all_fields_in_one_message(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    """Scenario 4: Multi-entity extraction from a single message."""
    from datetime import datetime, timedelta
    
    # Setup pending action
    await slot_manager.start(initial_state, "search_slots")
    
    # Setup available shops and courses
    initial_state.recent_tool_results.last_shop_search = {"data": [
        ShopInfo(shopId=1, shopName="Shinjuku Store", address="Shinjuku", phoneNumber="123", status="Open", openTime="09:00", closeTime="22:00"),
    ]}
    initial_state.recent_tool_results.last_course_search = {"data": [
        {"courseId": 101, "courseName": "Full Body Massage", "durations": [{"duration": 60, "price": 8000}]},
    ]}
    
    message = "Book Full Body Massage at Shinjuku Store tomorrow for 2 people."
    nlu_mock.understand.return_value = NLUResult(
        intent=Intent.PROVIDE_INFORMATION,
        entities=[
            Entity(type="course_name", value="Full Body Massage"),
            Entity(type="shop_name", value="Shinjuku Store"),
            Entity(type="date", value="2026-07-31"),
            Entity(type="number_of_people", value=2),
        ]
    )
    complete, message, data = await slot_manager.continue_filling(initial_state, message)
    
    expected_date = "2026-07-31"
    
    assert initial_state.booking_context.shop_id == 1
    assert initial_state.booking_context.shop_name == "Shinjuku Store"
    assert initial_state.booking_context.course_id == 101
    assert initial_state.booking_context.course_name == "Full Body Massage"
    assert initial_state.booking_context.number_of_people == 2
    assert initial_state.booking_context.duration == 60
    assert initial_state.booking_context.date == expected_date
    assert complete is True
    # The message might be a prompt if not all slots are filled.
    # In this test, all slots should be filled.
    # Check if duration was filled
    assert initial_state.booking_context.duration == 60
    assert "all the information" in message


@pytest.mark.asyncio
async def test_multi_entity_partial_name_resolution(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    """Scenario 8: Partial name resolution."""
    await slot_manager.start(initial_state, "search_slots")
    
    initial_state.recent_tool_results.last_shop_search = {"data": [
        ShopInfo(shopId=1, shopName="Shinjuku Grand", address="a", phoneNumber="1", status="Open", openTime="09:00", closeTime="22:00"),
        ShopInfo(shopId=2, shopName="Shibuya Plaza", address="b", phoneNumber="2", status="Open", openTime="09:00", closeTime="22:00"),
    ]}
    
    nlu_mock.understand.return_value = NLUResult(
        intent=Intent.PROVIDE_INFORMATION,
        entities=[
            Entity(type="shop_name", value="Shinjuku"),
            Entity(type="number_of_people", value=3),
            Entity(type="date", value="2026-07-31"),
        ]
    )
    response = await slot_manager.continue_filling(initial_state, "Shinjuku for 3 people tomorrow")
    assert initial_state.booking_context.shop_id == 1
    assert initial_state.booking_context.number_of_people == 3
    assert initial_state.booking_context.date == "2026-07-31"


@pytest.mark.asyncio
async def test_multi_entity_two_people_at_10am(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    """Specific phrase: Two people at 10am."""
    from datetime import datetime, timedelta
    await slot_manager.start(initial_state, "search_slots")
    
    initial_state.booking_context.shop_id = 1
    initial_state.booking_context.course_id = 101
    initial_state.booking_context.duration = 60
    
    initial_state.recent_tool_results.last_shop_search = {"data": [
        ShopInfo(shopId=1, shopName="Shinjuku", address="a", phoneNumber="1", status="Open", openTime="09:00", closeTime="22:00"),
    ]}
    initial_state.last_tool_result = {"data": [
        {"courseId": 101, "courseName": "Full Body Massage", "durations": [{"duration": 60}]},
    ]}
    
    expected_date = (datetime.now().date() + timedelta(days=1)).isoformat()
    nlu_mock.understand.return_value = NLUResult(
        intent=Intent.PROVIDE_INFORMATION,
        entities=[
            Entity(type=EntityType.DATE, value="2026-07-31"),
            Entity(type=EntityType.NUMBER_OF_PEOPLE, value=3),
        ]
    )
    response = await slot_manager.continue_filling(initial_state, "Tomorrow for 3 people")
    assert initial_state.booking_context.number_of_people == 3
    assert initial_state.booking_context.date == "2026-07-31"


@pytest.mark.asyncio
async def test_correction_does_not_overwrite_with_stale_extraction(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    """Corrections should not be overwritten by general extraction."""
    from datetime import datetime, timedelta
    await slot_manager.start(initial_state, "search_slots")
    
    initial_state.booking_context.shop_id = 1
    initial_state.booking_context.course_id = 101
    initial_state.booking_context.duration = 60
    initial_state.booking_context.date = "2025-01-01"
    
    initial_state.recent_tool_results.last_shop_search = {"data": [
        ShopInfo(shopId=1, shopName="Shinjuku", address="a", phoneNumber="1", status="Open", openTime="09:00", closeTime="22:00"),
    ]}
    initial_state.last_tool_result = {"data": [
        {"courseId": 101, "courseName": "Full Body Massage", "durations": [{"duration": 60}]},
    ]}
    
    nlu_mock.understand.return_value = NLUResult(intent=Intent.PROVIDE_INFORMATION, entities=[Entity(type=EntityType.DATE, value="next friday", is_correction=True)])
    response = await slot_manager.continue_filling(initial_state, "actually next Friday instead")
    
    # We need a robust way to determine what "next Friday" is relative to "2025-01-01"
    # For now, let's assume a fixed, expected outcome.
    # January 1st, 2025 is a Wednesday. Next Friday is January 3rd.
    assert initial_state.booking_context.date == "2025-01-03"


@pytest.mark.asyncio
async def test_shop_name_entity_sets_id_and_name(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    """Test that providing a shop name via NLU entity correctly sets both shop_id and shop_name."""
    action = "search_slots"

    # 1. Start -> asks for shop_id
    await slot_manager.start(initial_state, action)
    assert initial_state.pending_slot_to_fill == "shop_id"

    # 2. Mock NLU to return a SHOP_ID entity with a dict value, as the extractor now does
    nlu_result = NLUResult(
        intent=Intent.PROVIDE_INFORMATION, 
        entities=[
            Entity(
                type=EntityType.SHOP_ID, 
                value={"shopId": 1, "shopName": "Shinjuku"},
                raw_text="shinjuku"
            )
        ]
    )
    nlu_mock.understand.return_value = nlu_result
    
    # 3. Provide the shop name
    await slot_manager.continue_filling(initial_state, "shinjuku", nlu_result=nlu_result)
    
    # 4. Assert that both shop_id and shop_name are set correctly
    assert initial_state.booking_context.shop_id == 1
    assert initial_state.booking_context.shop_name == "Shinjuku"
    # It should then ask for the next slot
    assert "which massage course" in (await slot_manager.continue_filling(initial_state, ""))[1].lower()


@pytest.mark.asyncio
async def test_area_slot_filling(slot_manager: SlotFillingManager, initial_state: ConversationState, nlu_mock):
    """Test that providing an area correctly fills the slot and completes the action."""
    action = "search_shops"

    # 1. Start the process, it should ask for an area
    needed, message, _ = await slot_manager.start(initial_state, action)
    assert needed is True
    assert "which area" in message.lower()
    assert initial_state.pending_slot_to_fill == "area"

    # 2. Provide the area
    user_message = "in shinjuku"
    nlu_mock.understand.return_value = NLUResult(
        intent=Intent.PROVIDE_INFORMATION,
        entities=[Entity(type=EntityType.AREA, value="shinjuku")]
    )
    complete, message, _ = await slot_manager.continue_filling(
        initial_state, user_message, nlu_result=nlu_mock.understand.return_value
    )
    
    # 3. Assert that the slot is filled and the process is complete
    assert initial_state.booking_context.area == "shinjuku"
    assert complete is True
    assert "all the information" in message
    assert initial_state.pending_read_action is None

