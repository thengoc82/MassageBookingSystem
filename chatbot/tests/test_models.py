"""Tests for typed request/response models"""
from datetime import date, time

import pytest
from chatbot.models import (
    CheckEligibilityRequest,
    EligibilityInfo,
    FAQCitation,
    FAQItem,
    FAQSearchRequest,
    FAQSearchResponse,
    GetTherapistsRequest,
    LookupBookingRequest,
    LookupBookingResponse,
    SearchAvailableSlotsRequest,
    SearchCoursesRequest,
    SearchCoursesResponse,
    SearchShopsRequest,
    SearchShopsResponse,
)
from pydantic import ValidationError


def test_search_shops_request():
    req = SearchShopsRequest()
    assert req.model_extra is None or req.model_extra == {}


def test_search_shops_response():
    data = {
        "success": True,
        "data": [
            {
                "shopId": 1,
                "shopName": "Spa A",
                "address": "123 Main",
                "phoneNumber": "0123456789",
                "status": "Open",
                "openTime": time(8, 0),
                "closeTime": time(21, 0),
            }
        ],
        "message": "Success",
    }
    resp = SearchShopsResponse(**data)
    assert resp.success is True
    assert len(resp.data) == 1
    assert resp.data[0].shopName == "Spa A"


def test_search_courses_request_valid_type():
    req = SearchCoursesRequest(shopId=1, type="main")
    assert req.type == "main"


def test_search_courses_request_invalid_type():
    with pytest.raises(ValidationError):
        SearchCoursesRequest(shopId=1, type="invalid")


def test_search_courses_response():
    data = {
        "success": True,
        "data": [
            {
                "courseId": 1,
                "courseName": "Thai",
                "durations": [
                    {
                        "duration": 60,
                        "price": 500000
                    }
                ],
                "courseType": "main",
                "status": "Active",
            }
        ],
        "message": "Success",
    }
    resp = SearchCoursesResponse(**data)
    assert resp.data[0].courseName == "Thai"


def test_search_available_slots_request_required_fields():
    with pytest.raises(ValidationError):
        SearchAvailableSlotsRequest()


def test_search_available_slots_request_min_values():
    with pytest.raises(ValidationError):
        SearchAvailableSlotsRequest(shopId=1, date=date.today(), duration=0, numberOfPeople=1)


def test_search_available_slots_request_with_gender():
    with pytest.raises(ValidationError):
        SearchAvailableSlotsRequest(
            shopId=1, date=date.today(), duration=60, numberOfPeople=1, gender="Other"
        )


def test_search_available_slots_request_valid_gender():
    req = SearchAvailableSlotsRequest(
        shopId=1, date=date.today(), duration=60, numberOfPeople=1, gender="Male"
    )
    assert req.gender == "Male"


def test_get_therapists_request_required():
    with pytest.raises(ValidationError):
        GetTherapistsRequest()


def test_get_therapists_request_default_duration():
    req = GetTherapistsRequest(shopId=1, date=date.today(), startTime=time(9, 0))
    assert req.duration == 60


def test_check_eligibility_request_valid():
    req = CheckEligibilityRequest(phoneNumber="0123456789")
    assert req.phoneNumber == "0123456789"


def test_check_eligibility_request_invalid_phone():
    with pytest.raises(ValidationError):
        CheckEligibilityRequest(phoneNumber="abc")


def test_check_eligibility_request_short_phone():
    with pytest.raises(ValidationError):
        CheckEligibilityRequest(phoneNumber="12345")


def test_eligibility_info_eligible():
    info = EligibilityInfo(isEligible=True, memberRank="Gold", visitCount=5)
    assert info.isEligible is True
    assert info.memberRank == "Gold"


def test_eligibility_info_blocked():
    info = EligibilityInfo(isEligible=False, isBlocked=True, blockReason="NG List")
    assert info.isEligible is False
    assert info.isBlocked is True


def test_faq_search_request_min_query_length():
    with pytest.raises(ValidationError):
        FAQSearchRequest(query="")


def test_faq_search_request_top_k_limit():
    with pytest.raises(ValidationError):
        FAQSearchRequest(query="test", topK=100)


def test_faq_search_response():
    resp = FAQSearchResponse(
        success=True,
        data=[
            FAQItem(
                content="A.",
                score=0.9,
                citation=FAQCitation(
                    source_file="/faq.md",
                    document_title="FAQ",
                    heading="General",
                ),
            )
        ],
        message="Found",
    )
    assert resp.data[0].content == "A."


def test_lookup_booking_request_optional():
    req = LookupBookingRequest()
    assert req.bookingCode is None
    assert req.phoneNumber is None


def test_lookup_booking_response_with_pagination():
    data = {
        "success": True,
        "data": [],
        "message": "Success",
        "pagination": {"page": 1, "size": 20, "total": 0, "totalPages": 0},
    }
    resp = LookupBookingResponse(**data)
    assert resp.pagination is not None
    assert resp.pagination["page"] == 1
