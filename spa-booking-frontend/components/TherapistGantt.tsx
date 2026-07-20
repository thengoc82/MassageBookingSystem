'use client';

import { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';
import type { TimeSlot, TherapistInfo } from '@/types';

interface BookingDetail {
  bookingId: number;
  bookingCode: string;
  startTime: string;
  endTime: string;
  courseName: string | null;
}

interface Props {
  shopId: number;
  date: string;
  duration: number;
  numberOfPeople: number;
  startTime?: string;
  gender?: string;
  onSelectSlot?: (startTime: string, therapistId: number) => void;
  showDetails?: boolean;
}

function timeToMin(t: string) {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + m;
}

export default function TherapistGantt({ shopId, date, duration, numberOfPeople, startTime, gender, onSelectSlot, showDetails }: Props) {
  const [therapists, setTherapists] = useState<TherapistInfo[]>([]);
  const [slots, setSlots] = useState<TimeSlot[]>([]);
  const [bookingDetails, setBookingDetails] = useState<Record<number, BookingDetail[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const params: Record<string, string> = {
      date,
      duration: String(duration),
      numberOfPeople: String(numberOfPeople),
      show_therapists: 'true',
    };
    if (startTime) params.startTime = startTime;
    if (gender) params.gender = gender;

    api.shops.getAvailableSlots(shopId, params)
      .then((res: any) => {
        if (cancelled) return;
        const data = res?.data ?? res ?? [];
        const t = res?.therapists ?? [];
        setTherapists(t);
        setSlots(Array.isArray(data) ? data : []);
        if (res?.therapistBookingDetails) {
          setBookingDetails(res.therapistBookingDetails);
        } else {
          setBookingDetails({});
        }
      })
      .catch((err: any) => {
        if (cancelled) return;
        setError(err.message || 'Failed to load availability');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [shopId, date, duration, numberOfPeople, startTime, gender]);

  if (loading) {
    return <div className="text-center py-8 text-black">Loading therapist availability...</div>;
  }

  if (error) {
    return <div className="text-center py-8 text-red-600">{error}</div>;
  }

  if (!therapists.length) {
    return <div className="text-center py-8 text-black">No therapists found for this shop.</div>;
  }

  const cellW = 72;
  const rowH = 36;
  const nameColW = 140;
  const slotDuration = duration;

  const isAvailable = (therapistId: number, slot: TimeSlot) =>
    slot.availableTherapistIds?.includes(therapistId) ?? false;

  const getBookingForSlot = (therapistId: number, slot: TimeSlot): BookingDetail | null => {
    const details = bookingDetails[therapistId];
    if (!details) return null;
    const slotStart = timeToMin(slot.startTime);
    const slotEnd = slotStart + slotDuration;
    for (const b of details) {
      const bStart = timeToMin(b.startTime);
      const bEnd = timeToMin(b.endTime);
      if (slotStart < bEnd && slotEnd > bStart) return b;
    }
    return null;
  };

  const getBookingIdForSlot = (therapistId: number, slot: TimeSlot): number | null => {
    const b = getBookingForSlot(therapistId, slot);
    return b ? b.bookingId : null;
  };

  const handleCellClick = (startTime: string, therapistId: number) => {
    onSelectSlot?.(startTime, therapistId);
  };

  return (
    <div className="flex h-full min-h-0">
      {/* Therapist names column */}
      <div className="flex-shrink-0 border-r border-gray-200 bg-gray-50" style={{ width: nameColW }}>
        <div className="h-[40px] border-b border-gray-200 bg-gray-100 flex items-center px-3 text-xs font-semibold text-black sticky top-0 z-20">
          Therapist
        </div>
        {therapists.map(t => (
          <div
            key={t.therapistId}
            className="flex items-center px-3 border-b border-gray-100 text-sm font-medium text-black"
            style={{ height: rowH }}
          >
            {t.name}
          </div>
        ))}
      </div>

      {/* Scrollable grid */}
      <div ref={scrollRef} className="overflow-auto flex-1 min-w-0">
        <div style={{ width: slots.length * cellW, minWidth: '100%' }}>
          {/* Header row */}
          <div className="flex h-10 border-b border-gray-200 bg-gray-100 sticky top-0 z-10">
            {slots.map(slot => (
              <div
                key={slot.startTime}
                className="flex-shrink-0 flex items-center justify-center text-xs font-mono text-black border-r border-gray-200 last:border-r-0"
                style={{ width: cellW }}
              >
                {slot.startTime}
              </div>
            ))}
          </div>

          {/* Therapist rows */}
          {therapists.map(t => (
            <div key={t.therapistId} className="flex" style={{ height: rowH }}>
              {slots.map((slot, slotIdx) => {
                const avail = isAvailable(t.therapistId, slot);
                const booking = showDetails ? getBookingForSlot(t.therapistId, slot) : null;

                const prevBookingId = showDetails && slotIdx > 0
                  ? getBookingIdForSlot(t.therapistId, slots[slotIdx - 1])
                  : null;
                const currBookingId = booking?.bookingId ?? null;
                const separator = showDetails && prevBookingId !== null && currBookingId !== null && prevBookingId !== currBookingId;

                return (
                  <div
                    key={slot.startTime}
                    className="flex-shrink-0 relative group"
                    style={{ width: cellW }}
                  >
                    <button
                      disabled={!avail}
                      onClick={() => avail && handleCellClick(slot.startTime, t.therapistId)}
                      className={`w-full h-full border-r border-b border-gray-100 transition relative ${
                        avail
                          ? 'bg-green-100 hover:bg-green-200 cursor-pointer'
                          : 'bg-white cursor-default'
                      }`}
                    />
                    {separator && (
                      <div className="absolute top-0 right-0 w-0.5 bg-black z-10" style={{ height: rowH - 1 }} />
                    )}
                    {!avail && showDetails && booking && (
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-50 pointer-events-none">
                        <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg whitespace-nowrap">
                          <div className="font-mono font-semibold">{booking.bookingCode}</div>
                          <div>{booking.startTime} - {booking.endTime}</div>
                          <div>{booking.courseName || ''}</div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
