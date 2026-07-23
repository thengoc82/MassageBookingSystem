'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
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

function shortCode(code: string) {
  return code.slice(-6);
}

function buildBookingDetailsMap(bookings: any[]): Record<number, BookingDetail[]> {
  const map: Record<number, BookingDetail[]> = {};
  for (const b of bookings) {
    if (b.status !== 'Booked' && b.status !== 'CheckedIn') continue;

    const detail: BookingDetail = {
      bookingId: b.bookingId,
      bookingCode: b.bookingCode,
      startTime: b.startTime,
      endTime: b.endTime,
      courseName: null,
    };

        if (Array.isArray(b.therapistAssignments) && b.therapistAssignments.length > 0) {
      for (const ta of b.therapistAssignments) {
        if (!map[ta.therapistId]) map[ta.therapistId] = [];
        if (!map[ta.therapistId].some(x => x.bookingId === b.bookingId)) {
          map[ta.therapistId].push(detail);
        }
      }
    } else if (b.therapistId) {
      if (!map[b.therapistId]) map[b.therapistId] = [];
      if (!map[b.therapistId].some(x => x.bookingId === b.bookingId)) {
        map[b.therapistId].push(detail);
      }
    }
  }
  return map;
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

    const slotParams: Record<string, string> = {
      date,
      duration: String(duration),
      numberOfPeople: String(numberOfPeople),
      show_therapists: 'true',
    };
    if (startTime) slotParams.startTime = startTime;
    if (gender) slotParams.gender = gender;

    const bookingParams: Record<string, string> = {
      shopId: String(shopId),
      dateFrom: date,
      dateTo: date,
      size: '200',
    };

    Promise.all([
      api.shops.getAvailableSlots(shopId, slotParams),
      api.bookings.getAll(bookingParams),
    ])
      .then(([slotRes, bookingsRes]: any[]) => {
        if (cancelled) return;
        const slotsData = slotRes?.data ?? slotRes ?? [];
        const tList = slotRes?.therapists ?? [];
        setTherapists(tList);
        setSlots(Array.isArray(slotsData) ? slotsData : []);

        const bookings = bookingsRes?.data?.data || bookingsRes?.data || [];
        const list = Array.isArray(bookings) ? bookings : [];
        setBookingDetails(buildBookingDetailsMap(list));
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

  const getBookingForSlot = useCallback((therapistId: number, slot: TimeSlot): BookingDetail | null => {
    const details = bookingDetails[therapistId];
    if (!details) return null;
    const slotStart = timeToMin(slot.startTime);
    const slotEnd = slotStart + 15; // Use 15 min slot interval
    for (const b of details) {
      const bStart = timeToMin(b.startTime);
      const bEnd = timeToMin(b.endTime);
      if (slotStart < bEnd && slotEnd > bStart) return b;
    }
    return null;
  }, [bookingDetails]);

  const buildRowSegments = useCallback((therapistId: number) => {
    type SegItem = { type: 'avail'; slot: TimeSlot } | { type: 'booked'; booking: BookingDetail; count: number };
    const segs: SegItem[] = [];

    if (showDetails) {
      let i = 0;
      while (i < slots.length) {
        const booking = getBookingForSlot(therapistId, slots[i]);
        if (booking) {
          let count = 0;
          while (i + count < slots.length) {
            const b = getBookingForSlot(therapistId, slots[i + count]);
            if (!b || b.bookingId !== booking.bookingId) break;
            count++;
          }
          segs.push({ type: 'booked', booking, count });
          i += count;
        } else {
          segs.push({ type: 'avail', slot: slots[i] });
          i++;
        }
      }
    } else {
      for (const slot of slots) {
        segs.push({ type: 'avail', slot });
      }
    }

    return segs;
  }, [slots, getBookingForSlot, showDetails]);

  const getBookingCountForSlot = useCallback((therapistId: number, slot: TimeSlot): number => {
    const details = bookingDetails[therapistId];
    if (!details) return 0;
    const slotStart = timeToMin(slot.startTime);
    const slotEnd = slotStart + (showDetails ? 60 : 15);
    let count = 0;
    for (const b of details) {
      const bStart = timeToMin(b.startTime);
      const bEnd = timeToMin(b.endTime);
      if (slotStart < bEnd && slotEnd > bStart) count++;
    }
    return count;
  }, [bookingDetails, showDetails]);

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
  const rowH = showDetails ? 60 : 36;
  const nameColW = 140;

  const isAvailable = (therapistId: number, slot: TimeSlot) =>
    slot.availableTherapistIds?.includes(therapistId) ?? false;

  const handleCellClick = (startTime: string, therapistId: number) => {
    onSelectSlot?.(startTime, therapistId);
  };

  const capacityMode = numberOfPeople > 1;

  return (
    <div className="flex h-full min-h-0">
      {!capacityMode && (
        <div className="flex-shrink-0 border-r border-gray-200 bg-gray-50" style={{ width: nameColW }}>
          <div className="h-10 border-b border-gray-200 bg-gray-100 flex items-center px-3 text-xs font-semibold text-black sticky top-0 z-20">
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
      )}

      <div ref={scrollRef} className="overflow-auto flex-1 min-w-0">
        <div style={{ width: slots.length * cellW, minWidth: '100%' }}>
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

          {capacityMode ? (
            <div className="flex" style={{ height: rowH }}>
              {slots.map(slot => {
                const enough = slot.availableCapacity >= numberOfPeople;
                return (
                  <div key={slot.startTime} className="flex-shrink-0" style={{ width: cellW }}>
                    <button
                      disabled={!enough}
                      onClick={() => enough && handleCellClick(slot.startTime, 0)}
                      className={`w-full h-full border-r border-b border-gray-100 transition ${
                        enough
                          ? 'bg-green-100 hover:bg-green-200 cursor-pointer'
                          : 'bg-white cursor-default'
                      }`}
                    />
                  </div>
                );
              })}
            </div>
          ) : (
            therapists.map(t => {
              const segments = buildRowSegments(t.therapistId);
              return (
                <div key={t.therapistId} className="flex" style={{ height: rowH }}>
                  {segments.map((seg, segIdx) => {
                    if (seg.type === 'booked') {
                      const w = seg.count * cellW;
                      return (
                        <div
                          key={`b-${seg.booking.bookingId}`}
                          className={`flex-shrink-0 h-full bg-slate-800 text-white flex flex-col justify-center items-start px-1 overflow-hidden border-b border-gray-100 ${
                            segIdx < segments.length - 1 ? 'border-r border-black' : 'border-r border-gray-100'
                          }`}
                          style={{ width: w }}
                        >
                          <span className="text-[10px] leading-tight font-mono font-semibold">{shortCode(seg.booking.bookingCode)}</span>
                          <span className="text-[9px] leading-tight text-white/80">{seg.booking.startTime}-{seg.booking.endTime}</span>
                        </div>
                      );
                    }
                    return (
                      <div key={`a-${seg.slot.startTime}`} className="flex-shrink-0" style={{ width: cellW }}>
                        <button
                          disabled={!isAvailable(t.therapistId, seg.slot)}
                          onClick={() => isAvailable(t.therapistId, seg.slot) && handleCellClick(seg.slot.startTime, t.therapistId)}
                          className={`w-full h-full border-r border-b border-gray-100 transition ${
                            isAvailable(t.therapistId, seg.slot)
                              ? 'bg-green-100 hover:bg-green-200 cursor-pointer'
                              : 'bg-white cursor-default'
                          }`}
                        />
                      </div>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
