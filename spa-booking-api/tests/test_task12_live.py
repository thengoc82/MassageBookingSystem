"""Opt-in HTTP scenarios against the isolated Task 12 local services.

Set TASK12_BASE_URL and TASK12_FLASK_LOG before running. This module never uses
the development database selected by the normal Flask test fixture.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import re
import time
from uuid import uuid4

import httpx
import pytest
import jwt
from dotenv import dotenv_values


pytestmark = pytest.mark.skipif(
    not os.getenv("TASK12_BASE_URL"), reason="requires isolated Task 12 HTTP services"
)
BASE = os.getenv("TASK12_BASE_URL", "")
CHAT = os.getenv("TASK12_CHAT_URL", "")
LOG = Path(os.getenv("TASK12_FLASK_LOG", "/private/tmp/task12_flask.log"))


def day(offset):
    return (datetime.now(timezone.utc).date() + timedelta(days=offset)).isoformat()


def request(method, path, *, token=None, expected=200, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(base_url=BASE, timeout=15) as client:
        response = client.request(method, path, headers=headers, **kwargs)
    assert response.status_code == expected, (path, response.status_code, response.text)
    return response.json()


def admin_token():
    return request("POST", "/auth/login", json={
        "username": "admin", "password": "admin123"
    })["data"]["access_token"]


def therapist_token(username, password):
    return request("POST", "/auth/login", json={
        "username": username, "password": password
    })["data"]["access_token"]


def course(shop_id=1):
    entries = request("GET", f"/shops/{shop_id}/courses")["data"]
    return next(item for item in entries if item["courseType"] == "main")


def booking(phone, offset, *, guests=1, start="10:00", therapist=None):
    selected = course()
    option = next(item for item in selected["durations"] if item["duration"] == 60)
    payload = {
        "phoneNumber": phone, "shopId": 1, "bookingDate": day(offset),
        "startTime": start, "duration": 60, "numberOfPeople": guests,
        "services": [
            {"personIndex": index, "courseId": selected["courseId"]}
            for index in range(1, guests + 1)
        ],
        "selectedCourses": [{"courseId": selected["courseId"], **option}],
    }
    if therapist is not None:
        payload.update(therapistPreferenceType="specific", therapistPreferenceValue=therapist)
    return payload


def verify_phone(phone):
    previous = LOG.stat().st_size if LOG.exists() else 0
    request("POST", "/booking-access/challenges", json={"phoneNumber": phone})
    pattern = re.compile(rf"Booking access code for {re.escape(phone)}: (\d{{6}})")
    for _ in range(30):
        content = LOG.read_text(errors="replace")[previous:]
        match = pattern.search(content)
        if match:
            wrong = "000000" if match.group(1) != "000000" else "000001"
            request("POST", "/booking-access/verifications", json={
                "phoneNumber": phone, "code": wrong
            }, expected=401)
            return request("POST", "/booking-access/verifications", json={
                "phoneNumber": phone, "code": match.group(1)
            })["data"]["accessToken"]
        time.sleep(0.1)
    pytest.fail(f"terminal verification code was not logged for {phone}")


def test_live_customer_journey_and_access_control():
    phone = "0908881201"
    other_phone = "0908881202"
    created = request("POST", "/bookings", json=booking(phone, 12), expected=201)["data"]
    booking_id = created["bookingId"]
    assert created["status"] == "Booked" and created["bookingCode"].startswith("BK")

    request("GET", f"/bookings/{booking_id}", expected=401)
    request("GET", f"/bookings?phone={phone}", expected=401)
    request("GET", f"/bookings/{booking_id}", token="invalid.token", expected=401)
    secret = os.getenv("JWT_SECRET_KEY") or dotenv_values(Path(__file__).parents[1] / ".env").get("JWT_SECRET_KEY")
    assert secret
    expired = jwt.encode({
        "identity": {"role": "customer", "type": "customer_access", "phone": phone},
        "iat": int(time.time()) - 120, "nbf": int(time.time()) - 120,
        "exp": int(time.time()) - 30,
    }, secret, algorithm="HS256")
    request("GET", f"/bookings/{booking_id}", token=expired, expected=401)
    customer = verify_phone(phone)
    other = verify_phone(other_phone)
    listed = request("GET", f"/bookings?phone={phone}", token=customer)["data"]["data"]
    assert any(item["bookingId"] == booking_id for item in listed)
    assert request("GET", f"/bookings/{booking_id}", token=customer)["data"]["bookingCode"] == created["bookingCode"]
    request("GET", f"/bookings/{booking_id}", token=other, expected=404)
    request("PATCH", f"/bookings/{booking_id}", token=other,
            json={"startTime": "11:00"}, expected=404)
    request("PATCH", f"/bookings/{booking_id}/cancel", token=other, expected=404)
    request("GET", f"/bookings?phone={phone}", token=other, expected=403)
    request("GET", "/bookings/all", token=customer, expected=404)

    request("PATCH", f"/bookings/{booking_id}", token=customer, json={"startTime": "11:00"})
    assert request("GET", f"/bookings/{booking_id}", token=customer)["data"]["startTime"] == "11:00"
    request("PATCH", f"/bookings/{booking_id}/cancel", token=customer)
    assert request("GET", f"/bookings/{booking_id}", token=customer)["data"]["status"] == "Cancelled"
    request("PATCH", f"/bookings/{booking_id}", token=customer,
            json={"startTime": "12:00"}, expected=422)

    slots = request("GET", f"/shops/1/available-slots?date={day(12)}&duration=60&numberOfPeople=1&show_therapists=true")
    assert "therapistBookingDetails" not in slots["data"]
    request("POST", "/setup-demo-data", expected=404)


def test_live_group_restriction_and_invalid_data():
    admin = admin_token()
    payload = booking("0908881203", 13, guests=2, therapist=1)
    request("POST", "/bookings", json=payload, expected=400)
    payload.pop("therapistPreferenceType")
    payload.pop("therapistPreferenceValue")
    group = request("POST", "/bookings", json=payload, expected=201)["data"]
    assignments = group["therapistAssignments"]
    assert len(assignments) == 2 and len({entry["therapistId"] for entry in assignments}) == 2

    blocked_phone = "0908881204"
    created = request("POST", "/bookings", json=booking(blocked_phone, 14), expected=201)["data"]
    restriction = request("POST", "/admin/customer-restrictions", token=admin,
                          json={"phoneNumber": blocked_phone, "reason": "Task 12 private reason"},
                          expected=201)["data"]
    denied = request("POST", "/bookings", json=booking(blocked_phone, 15), expected=422)
    assert denied["error"]["code"] == "CUSTOMER_BLOCKED"
    assert "Task 12 private reason" not in str(denied)
    eligibility = request("POST", "/booking-eligibility-checks", json={"phoneNumber": blocked_phone})
    assert "Task 12 private reason" not in str(eligibility)
    request("GET", "/admin/customer-restrictions", expected=401)
    request("GET", "/admin/customer-restrictions", token=therapist_token("tanaka", "tanaka123"), expected=403)
    assert request("GET", f"/admin/customer-restrictions/{restriction['restrictionId']}", token=admin)["data"]["reason"] == "Task 12 private reason"
    request("DELETE", f"/admin/customer-restrictions/{restriction['restrictionId']}", token=admin)
    request("POST", "/bookings", json=booking(blocked_phone, 15), expected=201)

    invalid = booking("0908881205", 16)
    invalid["duration"] = -1
    request("POST", "/bookings", json=invalid, expected=400)
    assert request("GET", f"/bookings/{created['bookingId']}", token=admin)["data"]["status"] == "Booked"


def test_live_staff_shifts_and_status_transitions():
    admin = admin_token()
    tanaka = therapist_token("tanaka", "tanaka123")
    suzuki = therapist_token("suzuki", "suzuki123")
    new_therapist = request("POST", "/admin/shops/2/therapists", token=admin,
                            json={"name": "Task 12 Therapist", "gender": "Female",
                                  "username": "task12staff", "password": "test-password"},
                            expected=201)["data"]["therapistId"]
    shift_day = datetime.fromisoformat(day(17)).strftime("%A")
    before = request("GET", f"/shops/2/available-slots?date={day(17)}&duration=60&numberOfPeople=1")["data"]
    assert not before
    shift = request("POST", "/admin/therapist-shifts", token=admin, json={
        "therapistId": new_therapist, "dayOfWeek": shift_day,
        "startTime": "10:00", "endTime": "18:00", "effectiveFrom": day(1)
    }, expected=201)["data"]
    after = request("GET", f"/shops/2/available-slots?date={day(17)}&duration=60&numberOfPeople=1")["data"]
    assert any(item["startTime"] == "10:00" for item in after)
    request("POST", "/admin/therapist-shifts", token=admin, json={
        "therapistId": new_therapist, "dayOfWeek": shift_day,
        "startTime": "11:00", "endTime": "17:00", "effectiveFrom": day(1)
    }, expected=409)
    request("PATCH", f"/admin/therapist-shifts/{shift['shiftId']}", token=admin,
            json={"startTime": "11:00"})
    request("DELETE", f"/admin/therapist-shifts/{shift['shiftId']}", token=admin)
    request("GET", "/admin/shops/2/therapist-shifts", token=tanaka, expected=403)

    created = request("POST", "/bookings", json=booking("0908881206", 18, therapist=1), expected=201)["data"]
    booking_id = created["bookingId"]
    assert any(item["bookingId"] == booking_id for item in request("GET", "/therapists/bookings", token=tanaka)["data"])
    assert all(item["bookingId"] != booking_id for item in request("GET", "/therapists/bookings", token=suzuki)["data"])
    request("GET", f"/bookings/{booking_id}", token=suzuki, expected=404)
    request("PATCH", f"/therapists/bookings/{booking_id}/checkin", token=suzuki, expected=403)
    request("PATCH", f"/bookings/{booking_id}/checkin", token=tanaka, expected=403)
    request("PATCH", f"/therapists/bookings/{booking_id}/checkin", token=tanaka)
    assert request("GET", f"/bookings/{booking_id}", token=tanaka)["data"]["status"] == "CheckedIn"
    request("PATCH", f"/admin/bookings/{booking_id}/checkout", token=admin)
    assert request("GET", f"/bookings/{booking_id}", token=admin)["data"]["status"] == "CheckedOut"
    request("PATCH", f"/admin/bookings/{booking_id}/checkout", token=admin, expected=422)


def test_live_concurrent_final_capacity_and_changed_availability():
    payload = booking("0908881207", 19, therapist=2)
    competitor = {**payload, "phoneNumber": "0908881208"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda body: httpx.post(f"{BASE}/bookings", json=body, timeout=15),
                                (payload, competitor)))
    assert sorted(response.status_code for response in results) == [201, 422]
    winner = next(response.json()["data"] for response in results if response.status_code == 201)
    admin = admin_token()
    assert request("GET", f"/bookings/{winner['bookingId']}", token=admin)["data"]["status"] == "Booked"
    request("POST", "/bookings", json=booking("0908881209", 20, therapist=3), expected=201)
    occupied = booking("0908881210", 20, therapist=3)
    request("POST", "/bookings", json=occupied, expected=422)


def test_live_modification_rolls_back_when_slot_changes():
    admin = admin_token()
    editable = request("POST", "/bookings", json=booking("0908881217", 24, therapist=4), expected=201)["data"]
    for therapist_id in range(1, 6):
        request("POST", "/bookings", json=booking(
            f"09088812{17 + therapist_id:02d}", 24, start="11:00", therapist=therapist_id
        ), expected=201)
    request("PATCH", f"/bookings/{editable['bookingId']}", token=admin,
            json={"startTime": "11:00"}, expected=422)
    assert request("GET", f"/bookings/{editable['bookingId']}", token=admin)["data"]["startTime"] == "10:00"


def test_live_chat_rag_and_confirmed_booking():
    if not CHAT:
        pytest.skip("TASK12_CHAT_URL is unset")
    session = f"task12-{uuid4().hex}"

    def say(message):
        response = httpx.post(f"{CHAT}/chat", json={"session_id": session, "message": message}, timeout=25)
        assert response.status_code == 200, response.text
        return response.json()

    faq = say("How do I cancel a booking?")
    assert "Source:" in faq["message"] and "knowledge base" in faq["message"]
    say(f"Book a massage for 1 person on {day(21)} at 10am")
    say("Shinjuku Store")
    offered = say("Full Body Massage 60m")
    assert "10:00" in offered["message"]
    say("yes")
    say("no preference")
    pending = say("0908881211")
    assert pending["booking_progress"]["requires_confirmation"] is True
    admin = admin_token()
    before = request("GET", "/admin/bookings", token=admin)["data"]
    assert not any(item["phoneNumber"] == "0908881211" for item in before)
    confirmed = say("yes")
    assert confirmed["phase"] == "booking_complete"
    assert "BK" in confirmed["message"]
    listed = request("GET", "/admin/bookings", token=admin)["data"]
    assert any(item["phoneNumber"] == "0908881211" and item["status"] == "Booked" for item in listed)


def test_live_chat_rechecks_lost_therapist_before_write():
    if not CHAT:
        pytest.skip("TASK12_CHAT_URL is unset")
    session = f"task12-loss-{uuid4().hex}"

    def say(message):
        response = httpx.post(f"{CHAT}/chat", json={"session_id": session, "message": message}, timeout=25)
        assert response.status_code == 200, response.text
        return response.json()

    say(f"Book a massage for 1 person on {day(22)} at 10am")
    say("Shinjuku Store")
    say("Full Body Massage 60m")
    say("yes")
    say("Tanaka Yuki")
    pending = say("0908881213")
    assert pending["booking_progress"]["requires_confirmation"] is True
    request("POST", "/bookings", json=booking("0908881214", 22, therapist=1), expected=201)
    rejected = say("yes")
    assert rejected["phase"] != "booking_complete"
    assert any(word in rejected["message"].lower() for word in ("time", "slot", "unavailable", "therapist"))
    listed = request("GET", "/admin/bookings", token=admin_token())["data"]
    assert not any(item["phoneNumber"] == "0908881213" for item in listed)
