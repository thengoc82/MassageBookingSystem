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
    };
    if (numberOfPeople === 1) {
      params.show_therapists = 'true';
    }
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

  const getBookingForSlot = useCallback((therapistId: number, slot: TimeSlot): BookingDetail | null => {
    const details = bookingDetails[therapistId];
    if (!details) return null;
    const slotStart = timeToMin(slot.startTime);
    const slotEnd = slotStart + duration;
    for (const b of details) {
      const bStart = timeToMin(b.startTime);
      const bEnd = timeToMin(b.endTime);
      if (slotStart < bEnd && slotEnd > bStart) return b;
    }
    return null;
  }, [bookingDetails, duration]);

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

  if (loading) {
    return <div className="text-center py-8 text-black">Loading therapist availability...</div>;
  }

  if (error) {
    return <div className="text-center py-8 text-red-600">{error}</div>;
  }

  if (!therapists.length && numberOfPeople === 1) {
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
      <div className="flex-shrink-0 border-r border-gray-200 bg-gray-50" style={{ width: nameColW }}>
        <div className="h-10 border-b border-gray-200 bg-gray-100 flex items-center px-3 text-xs font-semibold text-black sticky top-0 z-20">
          {capacityMode ? 'Capacity' : 'Therapist'}
        </div>
        {capacityMode ? (
          <div
            className="flex items-center px-3 border-b border-gray-100 text-sm font-medium text-black"
            style={{ height: rowH }}
          >
            {numberOfPeople} {numberOfPeople > 1 ? 'people' : 'person'}
          </div>
        ) : (
          therapists.map(t => (
            <div
              key={t.therapistId}
              className="flex items-center px-3 border-b border-gray-100 text-sm font-medium text-black"
              style={{ height: rowH }}
            >
              {t.name}
            </div>
          ))
        )}
      </div>

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
                          className={`flex-shrink-0 h-full bg-slate-800 text-white flex flex-col justify-center items-center px-1 overflow-hidden border-b border-gray-100 ${
                            segIdx < segments.length - 1 ? 'border-r border-black' : 'border-r border-gray-100'
                          }`}
                          style={{ width: w }}
                        >
                          <span className="text-[10px] leading-tight font-mono font-semibold">{shortCode(seg.booking.bookingCode)}</span>
                          <span className="text-[9px] leading-tight text-white/80">{seg.booking.startTime}-{seg.booking.endTime}</span>
                          <span className="text-[9px] leading-tight text-white/60 truncate w-full text-center">{seg.booking.courseName || ''}</span>
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
