'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import BookingForm from '@/components/booking/BookingForm';

function ReservationForm() {
  const params = useSearchParams();
  const context = {
    shopId: Number(params.get('shopId')),
    bookingDate: params.get('date') || '',
    startTime: params.get('time') || '',
    duration: Number(params.get('duration')),
    numberOfPeople: Number(params.get('people')),
    therapistId: Number(params.get('people')) === 1 && params.get('therapistId') ? Number(params.get('therapistId')) : undefined,
    therapistGender: Number(params.get('people')) === 1 && ['Male', 'Female'].includes(params.get('therapistGender') || '')
      ? params.get('therapistGender') as 'Male' | 'Female' : undefined,
  };

  function rememberBooking(startTime: string) {
    try {
      const recent = JSON.parse(localStorage.getItem('recentBookings') || '[]');
      if (!Array.isArray(recent)) return;
      recent.push({ shopId: context.shopId, date: context.bookingDate, startTime, duration: context.duration });
      localStorage.setItem('recentBookings', JSON.stringify(recent.slice(-20)));
    } catch { /* Recent bookings are optional. */ }
  }

  return <BookingForm context={context} onConfirmed={rememberBooking} />;
}

export default function ReservationPage() {
  return <Suspense fallback={<div className="min-h-screen bg-mist p-8 text-ink-soft">Loading booking...</div>}><ReservationForm /></Suspense>;
}
