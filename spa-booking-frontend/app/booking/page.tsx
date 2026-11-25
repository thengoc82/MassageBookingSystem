'use client';

import { useEffect, useState } from 'react';
import BookingForm, { type BookingContext } from '@/components/booking/BookingForm';

export default function BookingPage() {
  const [context, setContext] = useState<BookingContext | null>(null);

  useEffect(() => {
    try {
      const pending = localStorage.getItem('pending_booking');
      if (pending) {
        const parsed = JSON.parse(pending) as BookingContext;
        queueMicrotask(() => setContext(parsed));
      }
    } catch { /* BookingForm reports missing context. */ }
  }, []);

  return <BookingForm context={context} onConfirmed={() => localStorage.removeItem('pending_booking')} />;
}
