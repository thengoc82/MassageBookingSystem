import pytest
from unittest.mock import AsyncMock, MagicMock

from chatbot.app.chat_endpoint import ChatEndpoint, ChatRequest
from chatbot.conversation.state import ConversationState, BookingContext
from chatbot.nlu.models import NLUResult, Intent, Entity, EntityType
from chatbot.session.store import SessionData
class MockStatefulSessionStore:
    def __init__(self):
        self.sessions: dict[str, SessionData] = {}

    async def get_session(self, session_id: str) -> SessionData | None:
        if session_id in self.sessions:
            return self.sessions[session_id]
        # To mimic real behavior, create a new session if one doesn't exist
        return await self.create_session(session_id)

    async def create_session(self, session_id: str, user_id: str | None = None) -> SessionData:
        session = SessionData(session_id=session_id, user_id=user_id, conversation_state=ConversationState())
        self.sessions[session_id] = session
        return session

    async def save_session(self, session: SessionData) -> None:
        self.sessions[session.session_id] = session

    def clear(self):
        self.sessions = {}


class MockNLU(AsyncMock):
    def __init__(self, result: NLUResult, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = result
        self.last_message = None
        self.last_state = None
        # Make the mock callable and return the desired result
        self.understand = AsyncMock(side_effect=self._real_understand)

    async def _real_understand(self, message: str, state: ConversationState, focused_slot: str | None = None) -> NLUResult:
        self.last_message = message
        self.last_state = state
        state.nlu_result = self.result
        return self.result


@pytest.fixture
def mock_store():
    return MockStatefulSessionStore()

@pytest.mark.asyncio
async def test_process_message_sets_nlu_result(mock_store: MockStatefulSessionStore):
    """Verify that the NLU result is correctly stored in the conversation state."""
    nlu_result = NLUResult(intent=Intent.GREETING, entities=[])
    mock_nlu = MockNLU(result=nlu_result)
    
    endpoint = ChatEndpoint()
    # Manually inject mocks
    endpoint._session_store = mock_store
    endpoint._nlu = mock_nlu
    endpoint._policy = MagicMock()
    endpoint._policy.decide.return_value = MagicMock(action="NO_ACTION")
    endpoint._tool_registry = MagicMock()

    request = ChatRequest(message="Hello", session_id="test_session")
    await endpoint.process_message(request)

    final_session = await mock_store.get_session("test_session")
    assert final_session is not None
    final_state = final_session.conversation_state
    
    assert final_state.nlu_result is not None
    assert final_state.nlu_result.intent == Intent.GREETING
    assert mock_nlu.last_message == "Hello"


@pytest.mark.asyncio
async def test_nlu_entities_populate_booking_context(mock_store: MockStatefulSessionStore):
    """Verify that NLU entities are correctly applied to the booking context."""
    nlu_entities = [
        Entity(type=EntityType.SHOP_ID, value="123", raw_text="Shibuya"),
        Entity(type=EntityType.DATE, value="2026-07-31", raw_text="tomorrow"),
    ]
    nlu_result = NLUResult(intent=Intent.CREATE_BOOKING, entities=nlu_entities)
    mock_nlu = MockNLU(result=nlu_result)
    
    # Pre-populate session with shop data that would have come from a tool call
    session = await mock_store.create_session("test_session")
    from chatbot.models import ShopInfo
    session.conversation_state.recent_tool_results.last_shop_search = [
        ShopInfo(shopId=1, shopName="Shinjuku", address="a", phoneNumber="p", status="s", openTime="10:00", closeTime="22:00"),
        ShopInfo(shopId=123, shopName="Shibuya", address="a", phoneNumber="p", status="s", openTime="10:00", closeTime="22:00"),
    ]
    await mock_store.save_session(session)

    endpoint = ChatEndpoint()
    endpoint._session_store = mock_store
    endpoint._nlu = mock_nlu
    endpoint._policy = MagicMock()
    # The policy needs to ask for a slot to trigger the slot filling logic where entities are applied
    endpoint._policy.decide.return_value = MagicMock(action="ASK_SLOT", slot="course_id")
    endpoint._tool_registry = MagicMock()

    request = ChatRequest(message="Book a massage at Shibuya tomorrow", session_id="test_session")
    await endpoint.process_message(request)

    final_session = await mock_store.get_session("test_session")
    assert final_session is not None
    context = final_session.conversation_state.booking_context

    assert context.shop_id == 123
    assert context.shop_name == "Shibuya"
    assert context.date == "2026-07-31"


@pytest.mark.asyncio
async def test_dialogue_policy_consumes_nlu_output(mock_store: MockStatefulSessionStore):
    """Verify that the dialogue policy manager receives the NLU result."""
    nlu_result = NLUResult(intent=Intent.CREATE_BOOKING, entities=[])
    mock_nlu = MockNLU(result=nlu_result)
    
    endpoint = ChatEndpoint()
    endpoint._session_store = mock_store
    endpoint._nlu = mock_nlu
    
    mock_policy = MagicMock()
    endpoint._policy = mock_policy
    mock_decision = MagicMock(action="NO_ACTION")
    mock_policy.decide.return_value = mock_decision

    request = ChatRequest(message="I want a massage", session_id="test_session")
    await endpoint.process_message(request)

    mock_policy.decide.assert_called_once()
    args, kwargs = mock_policy.decide.call_args
    
    called_state = args[0]
    called_intent = args[1]
    
    assert isinstance(called_state, ConversationState)
    assert called_state.nlu_result == nlu_result
    assert called_intent == Intent.CREATE_BOOKING
    assert 'nlu_result' in kwargs
    assert kwargs['nlu_result'] == nlu_result

