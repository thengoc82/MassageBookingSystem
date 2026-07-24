"""Tests for tools — read-only HTTP wrapper tools"""
from datetime import date, time
from unittest.mock import AsyncMock, patch

import pytest

from gateway.client import HTTPClient
from tools.search_tools import (
    CheckEligibilityTool,
    FAQSearchTool,
    GetTherapistsTool,
    LookupBookingTool,
    SearchAvailableSlotsTool,
    SearchCoursesTool,
    SearchShopsTool,
)
from models import (
    CheckEligibilityRequest,
    FAQSearchRequest,
    GetTherapistsRequest,
    LookupBookingRequest,
    SearchAvailableSlotsRequest,
    SearchCoursesRequest,
    SearchShopsRequest,
)


def make_client_mock(response_data: dict) -> HTTPClient:
    client = HTTPClient()
    client.get = AsyncMock(return_value=response_data)
    client.post = AsyncMock(return_value=response_data)
    return client


@pytest.mark.asyncio
async def test_search_shops_tool() -> None:
    client = make_client_mock({
        "success": True,
        "data": [
            {
                "shopId": 1,
                "shopName": "Spa A",
                "address": "123 Main",
                "phoneNumber": "0123456789",
                "status": "Open",
                "openTime": "08:00:00",
                "closeTime": "21:00:00",
            }
        ],
        "message": "Success",
    })
    tool = SearchShopsTool(client)
    result = await tool.execute(SearchShopsRequest())
    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0].shopName == "Spa A"
    client.get.assert_called_once_with("/shops")


@pytest.mark.asyncio
async def test_search_courses_tool() -> None:
    client = make_client_mock({
        "success": True,
        "data": [
            {
                "courseId": 1,
                "courseName": "Thai Massage",
                "duration": 60,
                "price": 500000,
                "courseType": "main",
                "status": "Active",
            }
        ],
        "message": "Success",
    })
    tool = SearchCoursesTool(client)
    result = await tool.execute(SearchCoursesRequest(shopId=1))
    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0].courseName == "Thai Massage"
    client.get.assert_called_once_with("/shops/1/courses", params={})


@pytest.mark.asyncio
async def test_search_courses_with_type_filter() -> None:
    client = make_client_mock({"success": True, "data": [], "message": "Success"})
    tool = SearchCoursesTool(client)
    await tool.execute(SearchCoursesRequest(shopId=1, type="main"))
    client.get.assert_called_once_with("/shops/1/courses", params={"type": "main"})


@pytest.mark.asyncio
async def test_search_available_slots_tool() -> None:
    client = make_client_mock({
        "success": True,
        "data": [
            {
                "startTime": "09:00:00",
                "endTime": "10:00:00",
                "availableCapacity": 2,
            }
        ],
        "message": "Success",
    })
    tool = SearchAvailableSlotsTool(client)
    request = SearchAvailableSlotsRequest(
        shopId=1,
        date=date(2026, 7, 15),
        duration=60,
        numberOfPeople=2,
    )
    result = await tool.execute(request)
    assert result.success is True
    assert len(result.data) == 1
    client.get.assert_called_once()


@pytest.mark.asyncio
async def test_search_available_slots_with_therapists() -> None:
    client = make_client_mock({"success": True, "data": [], "message": "Success"})
    tool = SearchAvailableSlotsTool(client)
    request = SearchAvailableSlotsRequest(
        shopId=1,
        date=date(2026, 7, 15),
        duration=60,
        numberOfPeople=2,
        showTherapists=True,
    )
    await tool.execute(request)
    call_args = client.get.call_args
    assert call_args[1]["params"]["show_therapists"] == "true"


@pytest.mark.asyncio
async def test_get_therapists_tool() -> None:
    client = make_client_mock({
        "success": True,
        "data": [
            {"therapistId": 1, "name": "Anna", "gender": "Female", "isAvailable": True}
        ],
        "message": "Success",
    })
    tool = GetTherapistsTool(client)
    request = GetTherapistsRequest(
        shopId=1,
        date=date(2026, 7, 15),
        startTime=time(9, 0),
    )
    result = await tool.execute(request)
    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0].name == "Anna"
    client.get.assert_called_once_with(
        "/shops/1/available-therapists",
        params={"date": "2026-07-15", "startTime": "09:00:00", "duration": 60},
    )


@pytest.mark.asyncio
async def test_get_therapists_with_gender() -> None:
    client = make_client_mock({"success": True, "data": [], "message": "Success"})
    tool = GetTherapistsTool(client)
    request = GetTherapistsRequest(
        shopId=1,
        date=date(2026, 7, 15),
        startTime=time(9, 0),
        gender="Female",
    )
    await tool.execute(request)
    call_args = client.get.call_args
    assert call_args[1]["params"]["gender"] == "Female"


@pytest.mark.asyncio
async def test_lookup_booking_by_code() -> None:
    client = HTTPClient()
    client.get = AsyncMock(side_effect=[
        {
            "success": True,
            "data": {
                "bookingId": 120,
                "bookingCode": "BK20260715001",
                "shopId": 1,
                "shopName": "Spa A",
                "phoneNumber": "0123456789",
                "bookingDate": "2026-07-15",
                "startTime": "10:00:00",
                "numberOfPeople": 1,
                "status": "Booked",
                "services": [
                    {"personIndex": 1, "courseId": 1, "courseName": "Thai"}
                ],
                "addOns": [],
            }
        }
    ])
    tool = LookupBookingTool(client)
    request = LookupBookingRequest(bookingCode="BK20260715001")
    result = await tool.execute(request)
    assert result.success is True
    assert len(result.data) == 1


@pytest.mark.asyncio
async def test_lookup_booking_by_phone() -> None:
    client = make_client_mock({
        "success": True,
        "data": [],
        "message": "Success",
        "pagination": {"page": 1, "size": 20, "total": 0, "totalPages": 0},
    })
    tool = LookupBookingTool(client)
    request = LookupBookingRequest(phoneNumber="0123456789")
    result = await tool.execute(request)
    assert result.success is True
    client.get.assert_called_once_with("/bookings", params={"phone": "0123456789"})


@pytest.mark.asyncio
async def test_check_eligibility_tool() -> None:
    client = make_client_mock({
        "success": True,
        "data": {
            "customerId": 5,
            "isEligible": True,
            "memberRank": "Gold",
            "visitCount": 10,
            "isBlocked": False,
        },
        "message": "Success",
    })
    tool = CheckEligibilityTool(client)
    request = CheckEligibilityRequest(phoneNumber="0123456789")
    result = await tool.execute(request)
    assert result.success is True
    assert result.data.isEligible is True
    assert result.data.memberRank == "Gold"
    client.post.assert_called_once_with(
        "/booking-eligibility-checks", json={"phoneNumber": "0123456789"}
    )


@pytest.mark.asyncio
async def test_faq_search_tool() -> None:
    client = make_client_mock({"success": True, "data": [], "message": "Success"})
    tool = FAQSearchTool(client)
    request = FAQSearchRequest(query="How to book?")
    result = await tool.execute(request)
    assert result.success is True
    assert result.message is not None


def test_search_shops_tool_name() -> None:
    client = make_client_mock({"success": True, "data": [], "message": "Success"})
    tool = SearchShopsTool(client)
    assert tool.name == "searchShops"


def test_search_courses_tool_name() -> None:
    client = make_client_mock({"success": True, "data": [], "message": "Success"})
    tool = SearchCoursesTool(client)
    assert tool.name == "searchCourses"


def test_search_available_slots_tool_name() -> None:
    client = make_client_mock({"success": True, "data": [], "message": "Success"})
    tool = SearchAvailableSlotsTool(client)
    assert tool.name == "searchAvailableSlots"


def test_get_therapists_tool_name() -> None:
    client = make_client_mock({"success": True, "data": [], "message": "Success"})
    tool = GetTherapistsTool(client)
    assert tool.name == "getTherapists"


def test_lookup_booking_tool_name() -> None:
    client = make_client_mock({"success": True, "data": [], "message": "Success"})
    tool = LookupBookingTool(client)
    assert tool.name == "lookupBooking"


def test_check_eligibility_tool_name() -> None:
    client = make_client_mock({"success": True, "data": [], "message": "Success"})
    tool = CheckEligibilityTool(client)
    assert tool.name == "checkEligibility"


def test_faq_search_tool_name() -> None:
    client = make_client_mock({"success": True, "data": [], "message": "Success"})
    tool = FAQSearchTool(client)
    assert tool.name == "faqSearch"