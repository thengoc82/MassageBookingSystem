from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field


# SearchShops
class SearchShopsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShopInfo(BaseModel):
    shopId: int
    shopName: str
    address: str
    phoneNumber: str
    status: str
    openTime: time
    closeTime: time


class SearchShopsResponse(BaseModel):
    success: bool
    data: list[ShopInfo]
    message: str


# SearchCourses
class SearchCoursesRequest(BaseModel):
    shopId: int
    type: str | None = Field(default=None, pattern="^(main|addon)$")


class CourseDurationInfo(BaseModel):
    duration: int
    price: int


class CourseInfo(BaseModel):
    courseId: int
    courseName: str
    courseType: str
    durations: list[CourseDurationInfo]


class SearchCoursesResponse(BaseModel):
    success: bool
    data: list[CourseInfo]
    message: str


# SearchAvailableSlots
class SearchAvailableSlotsRequest(BaseModel):
    shopId: int
    date: date
    duration: int = Field(ge=1)
    numberOfPeople: int = Field(ge=1)
    startTime: time | None = None
    courseIds: str | None = None
    gender: str | None = Field(default=None, pattern="^(Male|Female)$")
    showTherapists: bool = False


class SlotInfo(BaseModel):
    startTime: time
    endTime: time
    availableCapacity: int
    availableTherapistIds: list[int] | None = None


class TherapistInfo(BaseModel):
    therapistId: int
    name: str
    gender: str
    isAvailable: bool


class SearchAvailableSlotsResponse(BaseModel):
    success: bool
    data: list[SlotInfo]
    message: str
    therapists: list[TherapistInfo] | None = None


# GetTherapists
class GetTherapistsRequest(BaseModel):
    shopId: int
    date: date
    startTime: time
    duration: int = Field(default=60, ge=1)
    gender: str | None = Field(default=None, pattern="^(Male|Female)$")


class GetTherapistsResponse(BaseModel):
    success: bool
    data: list[TherapistInfo]
    message: str


# LookupBooking
class LookupBookingRequest(BaseModel):
    bookingCode: str | None = None
    phoneNumber: str | None = None


class BookingService(BaseModel):
    personIndex: int
    courseId: int
    courseName: str | None = None


class BookingAddOn(BaseModel):
    personIndex: int
    courseId: int
    courseName: str | None = None


class BookingInfo(BaseModel):
    bookingId: int
    bookingCode: str
    shopId: int
    shopName: str
    phoneNumber: str
    bookingDate: date
    startTime: time
    numberOfPeople: int
    status: str
    services: list[BookingService]
    addOns: list[BookingAddOn]
    therapistId: int | None = None
    therapistName: str | None = None


class LookupBookingResponse(BaseModel):
    success: bool
    data: list[BookingInfo]
    message: str
    pagination: dict | None = None


# CheckEligibility
class CheckEligibilityRequest(BaseModel):
    phoneNumber: str = Field(pattern=r"^\d{9,11}$")


class EligibilityInfo(BaseModel):
    customerId: int | None = None
    isEligible: bool
    memberRank: str | None = None
    visitCount: int = 0
    isBlocked: bool = False
    blockReason: str | None = None


class CheckEligibilityResponse(BaseModel):
    success: bool
    data: EligibilityInfo
    message: str


# FAQ Search
class FAQSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    topK: int = Field(default=3, ge=1, le=10)


class FAQCitation(BaseModel):
    """Citation for an FAQ answer."""

    source_file: str
    document_title: str
    heading: str | None = None


class FAQItem(BaseModel):
    """A single FAQ answer with citation."""

    content: str
    score: float
    citation: FAQCitation


class FAQSearchResponse(BaseModel):
    success: bool
    data: list[FAQItem]
    message: str


# CreateBooking
class CreateBookingService(BaseModel):
    personIndex: int
    courseId: int


class CreateBookingAddOn(BaseModel):
    personIndex: int
    courseId: int


class CreateBookingRequest(BaseModel):
    shopId: int
    userName: str | None = None
    phoneNumber: str
    bookingDate: date
    startTime: time
    duration: int = Field(ge=1)
    numberOfPeople: int
    services: list[CreateBookingService]
    addOns: list[CreateBookingAddOn] | None = None
    therapistId: int | None = None
    therapistGender: str | None = Field(default=None, pattern="^(Male|Female)$")


class CreateBookingResponse(BaseModel):
    success: bool
    bookingId: int | None = None
    bookingCode: str | None = None
    message: str | None = None


# ModifyBooking
class ModifyBookingService(BaseModel):
    personIndex: int
    courseId: int


class ModifyBookingAddOn(BaseModel):
    personIndex: int
    courseId: int


class ModifyBookingRequest(BaseModel):
    bookingId: int
    shopId: int | None = None
    bookingDate: date | None = None
    startTime: time | None = None
    numberOfPeople: int | None = None
    services: list[ModifyBookingService] | None = None
    addOns: list[ModifyBookingAddOn] | None = None
    therapistId: int | None = None
    therapistGender: str | None = Field(default=None, pattern="^(Male|Female)$")


class ModifyBookingResponse(BaseModel):
    success: bool
    bookingId: int | None = None
    message: str | None = None


# CancelBooking
class CancelBookingRequest(BaseModel):
    bookingId: int
    reason: str | None = None


class CancelBookingResponse(BaseModel):
    success: bool
    bookingId: int | None = None
    message: str | None = None
