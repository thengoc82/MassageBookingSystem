'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '@/lib/api';
import { localDateStr, timeToMin } from '@/lib/dates';
import type { TimeSlot, TherapistInfo } from '@/types';

interface BookingDetail {
  bookingId: number;
  bookingCode: string;
  startTime: string;
  endTime: string;
  courseName: string | null;
  status: string;
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

const SLOT_MIN = 15;
const CELL_W = 72;

function shortCode(code: string) {
  return code.slice(-6);
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(p => p[0]?.toUpperCase())
    .join('');
}

const COURSE_PALETTE = ['#3E7F72', '#4A6585', '#1F2B2A', '#7A4E6D'];

/**
 * Course colours differ in lightness as well as hue, and the course name is always printed on the bar.
 * Known names keep a fixed colour; any other course gets a stable colour from its name.
 */
export function courseColor(name: string | null): string {
  const n = (name || '').toLowerCase();
  if (n.includes('thai')) return COURSE_PALETTE[0];
  if (n.includes('swedish')) return COURSE_PALETTE[1];
  if (n.includes('deep')) return COURSE_PALETTE[2];
  if (n.includes('hot')) return COURSE_PALETTE[3];
  if (!n) return '#4F615E';
  let h = 0;
  for (let i = 0; i < n.length; i++) h = (h * 31 + n.charCodeAt(i)) >>> 0;
  return COURSE_PALETTE[h % COURSE_PALETTE.length];
}

function buildBookingDetailsMap(
  bookings: any[],
  courseById: Record<number, string>
): Record<number, BookingDetail[]> {
  const map: Record<number, BookingDetail[]> = {};
  for (const b of bookings) {
    if (b.status !== 'Booked' && b.status !== 'CheckedIn') continue;

    const detail: BookingDetail = {
      bookingId: b.bookingId,
      bookingCode: b.bookingCode,
      startTime: b.startTime,
      endTime: b.endTime,
      courseName: courseById[b.bookingId] ?? null,
      status: b.status,
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
  const [nowMin, setNowMin] = useState<number>(() => {
    const d = new Date();
    return d.getHours() * 60 + d.getMinutes();
  });
  const scrollRef = useRef<HTMLDivElement>(null);
  const scrolledFor = useRef<string>('');

  useEffect(() => {
    const id = setInterval(() => {
      const d = new Date();
      setNowMin(d.getHours() * 60 + d.getMinutes());
    }, 60_000);
    return () => clearInterval(id);
  }, []);

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

        const courseById: Record<number, string> = {};
        const details = slotRes?.therapistBookingDetails ?? {};
        for (const arr of Object.values(details) as any[][]) {
          for (const d of arr || []) {
            if (d?.courseName) courseById[d.bookingId] = d.courseName;
          }
        }

        const bookings = bookingsRes?.data?.data || bookingsRes?.data || [];
        const list = Array.isArray(bookings) ? bookings : [];
        setBookingDetails(buildBookingDetailsMap(list, courseById));
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

  const isToday = date === localDateStr();
  const firstMin = slots.length ? timeToMin(slots[0].startTime) : 0;
  const lastMin = slots.length ? timeToMin(slots[slots.length - 1].startTime) + SLOT_MIN : 0;
  const showNow = isToday && slots.length > 0 && nowMin >= firstMin && nowMin <= lastMin;
  const nowLeft = ((nowMin - firstMin) / SLOT_MIN) * CELL_W;

  // Bring the current time into view once per day/shop when the board first loads.
  useEffect(() => {
    if (loading || !showNow || !scrollRef.current) return;
    const key = `${shopId}-${date}`;
    if (scrolledFor.current === key) return;
    scrolledFor.current = key;
    scrollRef.current.scrollLeft = Math.max(0, nowLeft - 240);
  }, [loading, showNow, nowLeft, shopId, date]);

  const getBookingForSlot = useCallback((therapistId: number, slot: TimeSlot): BookingDetail | null => {
    const details = bookingDetails[therapistId];
    if (!details) return null;
    const slotStart = timeToMin(slot.startTime);
    const slotEnd = slotStart + SLOT_MIN;
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

  if (loading) {
    return <div className="py-8 text-center text-ink-soft">Loading therapist availability…</div>;
  }

  if (error) {
    return <div role="alert" className="py-8 text-center text-red-700">{error}</div>;
  }

  if (!therapists.length) {
    return <div className="py-8 text-center text-ink-soft">No therapists found for this shop.</div>;
  }

  const rowH = showDetails ? 64 : 40;
  const nameColW = showDetails ? 176 : 148;

  const isAvailable = (therapistId: number, slot: TimeSlot) =>
    slot.availableTherapistIds?.includes(therapistId) ?? false;

  const handleCellClick = (startTime: string, therapistId: number) => {
    onSelectSlot?.(startTime, therapistId);
  };

  const capacityMode = numberOfPeople > 1;

  const nowLine = showNow ? (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute top-0 bottom-0 z-[5] w-0.5 bg-amber"
      style={{ left: nowLeft }}
    />
  ) : null;

  return (
    <div className="flex h-full min-h-0">
      {!capacityMode && (
        <div className="shrink-0 border-r border-line bg-linen" style={{ width: nameColW }}>
          <div className="sticky top-0 z-20 flex h-10 items-center border-b border-line bg-linen px-4 text-xs font-semibold text-ink-soft">
            Therapist
          </div>
          {therapists.map(t => (
            <div
              key={t.therapistId}
              className="flex items-center gap-2.5 border-b border-line/60 px-4 text-sm font-medium text-basalt"
              style={{ height: rowH }}
            >
              <span aria-hidden="true" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-celadon-soft text-xs font-semibold">
                {initials(t.name)}
              </span>
              <span className="truncate">{t.name}</span>
            </div>
          ))}
        </div>
      )}

      <div ref={scrollRef} className="min-w-0 flex-1 overflow-auto bg-linen">
        <div className="relative" style={{ width: slots.length * CELL_W, minWidth: '100%' }}>
          <div className="sticky top-0 z-10 flex h-10 border-b border-line bg-linen">
            {slots.map(slot => {
              const onHour = slot.startTime.endsWith(':00');
              return (
                <div
                  key={slot.startTime}
                  className={`flex shrink-0 items-center border-r border-line/60 pl-2 text-xs last:border-r-0 ${
                    onHour ? 'font-semibold text-basalt' : 'text-ink-soft'
                  }`}
                  style={{ width: CELL_W }}
                >
                  {slot.startTime}
                </div>
              );
            })}
            {showNow && (
              <div
                className="absolute top-1.5 z-[6] -translate-x-1/2 rounded-full bg-amber px-2 py-0.5 text-xs font-semibold text-basalt"
                style={{ left: nowLeft }}
              >
                {String(Math.floor(nowMin / 60)).padStart(2, '0')}:{String(nowMin % 60).padStart(2, '0')}
              </div>
            )}
          </div>

          {nowLine}

          {capacityMode ? (
            <div className="flex" style={{ height: rowH }}>
              {slots.map(slot => {
                const enough = slot.availableCapacity >= numberOfPeople;
                return (
                  <div key={slot.startTime} className="shrink-0" style={{ width: CELL_W }}>
                    <button
                      disabled={!enough}
                      onClick={() => enough && handleCellClick(slot.startTime, 0)}
                      aria-label={enough ? `Book ${slot.startTime}` : `${slot.startTime} unavailable`}
                      className={`h-full w-full border-b border-r border-line/60 transition-colors ${
                        enough
                          ? 'cursor-pointer bg-celadon-soft hover:bg-[#BFDBD3]'
                          : 'cursor-default bg-linen'
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
                  {segments.map(seg => {
                    if (seg.type === 'booked') {
                      const { booking } = seg;
                      const w = seg.count * CELL_W;
                      const past = isToday && timeToMin(booking.endTime) <= nowMin;
                      const live = booking.status === 'CheckedIn';
                      return (
                        <div
                          key={`b-${booking.bookingId}`}
                          className="h-full shrink-0 border-b border-line/60 p-1"
                          style={{ width: w }}
                        >
                          <div
                            className="flex h-full flex-col justify-center overflow-hidden rounded-[10px] px-2.5 text-white"
                            style={{ background: courseColor(booking.courseName), opacity: past ? 0.55 : 1 }}
                          >
                            <span className="flex items-center gap-1.5 truncate text-[13px] font-semibold leading-tight">
                              {live && <span aria-label="In session" className="h-2 w-2 shrink-0 rounded-full bg-[#F2B94F]" />}
                              {booking.courseName || `#${shortCode(booking.bookingCode)}`}
                            </span>
                            <span className="truncate text-xs leading-tight text-[#E8F0EE]">
                              {booking.startTime} to {booking.endTime}, #{shortCode(booking.bookingCode)}
                            </span>
                          </div>
                        </div>
                      );
                    }
                    const free = isAvailable(t.therapistId, seg.slot);
                    return (
                      <div key={`a-${seg.slot.startTime}`} className="shrink-0" style={{ width: CELL_W }}>
                        <button
                          disabled={!free}
                          onClick={() => free && handleCellClick(seg.slot.startTime, t.therapistId)}
                          aria-label={free ? `Book ${t.name} at ${seg.slot.startTime}` : `${t.name} unavailable at ${seg.slot.startTime}`}
                          className={`h-full w-full border-b border-r border-line/60 transition-colors ${
                            free
                              ? 'cursor-pointer bg-celadon-soft hover:bg-[#BFDBD3]'
                              : 'cursor-default bg-linen'
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
