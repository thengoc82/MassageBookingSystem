export interface Shop {
  shopId: number;
  shopName: string;
  address: string;
  phoneNumber: string;
  status: string;
  openTime: string;
  closeTime: string;
}

export interface Course {
  courseId: number;
  courseName: string;
  duration: number;
  price: number;
  courseType: 'main' | 'addon';
  status?: string;
}

export interface TimeSlot {
  startTime: string;
  endTime: string;
  availableCapacity: number;
  availableTherapistIds?: number[];
}

export interface TherapistInfo {
  therapistId: number;
  name: string;
  gender: string;
}

export interface Therapist {
  therapistId: number;
  name: string;
  gender: string;
  isAvailable: boolean;
}

export interface BookingService {
  personIndex: number;
  courseId: number;
}

export interface Booking {
  bookingId: number;
  bookingCode: string;
  shopId: number;
  shopName?: string;
  phoneNumber: string;
  bookingDate: string;
  startTime: string;
  endTime: string;
  numberOfPeople: number;
  status: 'Booked' | 'CheckedIn' | 'CheckedOut' | 'Cancelled';
  therapistId?: number;
  therapistName?: string;
  services?: BookingServiceDetail[];
  addOns?: BookingServiceDetail[];
  preferences?: Record<string, unknown>;
}

export interface BookingServiceDetail {
  personIndex: number;
  courseId: number;
  courseName?: string;
}

export interface BookingFormData {
  shopId: number;
  bookingDate: string;
  startTime: string;
  endTime: string;
  duration: number;
  numberOfPeople: number;
  courseId: number;
  addOnCourseIds?: number[];
  services: BookingService[];
  addOns?: BookingService[];
}

export type TherapistPreferenceType = 'no_preference' | 'specific' | 'gender';
