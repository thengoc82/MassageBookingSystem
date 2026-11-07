'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import RequireAuth from '@/components/RequireAuth';
import AdminSidebar from '@/components/AdminSidebar';
import TherapistGantt from '@/components/TherapistGantt';
import { api } from '@/lib/api';
import { localDateStr, timeToMin } from '@/lib/dates';

function therapistNames(b: any): string {
  if (Array.isArray(b.therapistAssignments) && b.therapistAssignments.length > 0) {
    return b.therapistAssignments
      .slice()
      .sort((a: any, c: any) => a.personIndex - c.personIndex)
      .map((t: any) => t.therapistName.split(' ')[0])
      .join(' and ');
  }
  return b.therapistName ? b.therapistName.split(' ')[0] : 'Therapist to be assigned';
}

function AdminDashboard() {
  const router = useRouter();
  const today = localDateStr();
  const [shops, setShops] = useState<any[]>([]);
  const [shopId, setShopId] = useState<number | ''>('');
  const [date, setDate] = useState(today);
  const [bookings, setBookings] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [boardKey, setBoardKey] = useState(0);
  const [nowMin, setNowMin] = useState(() => {
    const d = new Date();
    return d.getHours() * 60 + d.getMinutes();
  });

  useEffect(() => {
    const id = setInterval(() => {
      const d = new Date();
      setNowMin(d.getHours() * 60 + d.getMinutes());
    }, 60_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    api.admin.getShops().then(res => {
      const list = res.data?.data || res.data || [];
      setShops(list);
      if (list.length) setShopId(list[0].shopId || list[0].id);
    }).catch(() => {});
  }, []);

  const loadBookings = useCallback(() => {
    if (!shopId) return;
    api.admin.getBookings({ shopId: Number(shopId), dateFrom: date, dateTo: date }).then(res => {
      setBookings(res.data?.data || res.data || []);
    }).catch(() => {});
  }, [shopId, date]);

  useEffect(() => { loadBookings(); }, [loadBookings]);

  const shiftDay = (delta: number) => {
    const [y, m, d] = date.split('-').map(Number);
    setDate(localDateStr(new Date(y, m - 1, d + delta)));
  };

  const checkIn = async (id: number) => {
    setError('');
    try {
      await api.admin.checkinBooking(id);
      loadBookings();
      setBoardKey(k => k + 1);
    } catch (e: any) {
      setError(e.message || 'Could not check in this booking');
    }
  };

  const isToday = date === today;
  const inSession = useMemo(() => bookings.filter(b => b.status === 'CheckedIn').length, [bookings]);
  const waiting = useMemo(
    () => bookings
      .filter(b => b.status === 'Booked')
      .sort((a, b) => timeToMin(a.startTime) - timeToMin(b.startTime)),
    [bookings]
  );
  const arrivingSoon = isToday
    ? waiting.filter(b => timeToMin(b.startTime) <= nowMin + 60).length
    : 0;

  const dateLabel = useMemo(() => {
    const [y, m, d] = date.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short' });
  }, [date]);

  const headline = isToday
    ? `${inSession} in session, ${arrivingSoon} arriving in the next hour`
    : `${bookings.filter(b => b.status !== 'Cancelled').length} bookings on ${dateLabel}`;

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="min-w-0 flex-1 space-y-5 px-8 py-6">
        <div className="flex flex-wrap items-center gap-3">
          <label className="sr-only" htmlFor="shop">Shop</label>
          <select
            id="shop"
            value={shopId}
            onChange={e => setShopId(Number(e.target.value))}
            className="h-11 rounded-[10px] border border-[#C5D0CC] bg-linen px-3 text-sm font-medium"
          >
            {shops.map((s: any) => (
              <option key={s.shopId || s.id} value={s.shopId || s.id}>{s.shopName}</option>
            ))}
          </select>
          <div className="flex items-center gap-1">
            <button type="button" onClick={() => shiftDay(-1)} aria-label="Previous day"
              className="flex h-11 w-11 items-center justify-center rounded-[10px] border border-[#C5D0CC] bg-linen hover:bg-celadon-soft">
              <ChevronLeft size={16} aria-hidden="true" />
            </button>
            <label className="sr-only" htmlFor="date">Date</label>
            <input
              id="date"
              type="date"
              value={date}
              onChange={e => e.target.value && setDate(e.target.value)}
              className="h-11 rounded-[10px] border border-[#C5D0CC] bg-linen px-3 text-sm font-medium"
            />
            <button type="button" onClick={() => shiftDay(1)} aria-label="Next day"
              className="flex h-11 w-11 items-center justify-center rounded-[10px] border border-[#C5D0CC] bg-linen hover:bg-celadon-soft">
              <ChevronRight size={16} aria-hidden="true" />
            </button>
            {!isToday && (
              <button type="button" onClick={() => setDate(today)}
                className="h-11 rounded-[10px] px-3 text-sm font-semibold text-celadon-deep hover:bg-celadon-soft">
                Today
              </button>
            )}
          </div>
          <div className="flex-1" />
          <button
            type="button"
            onClick={() => router.push('/dashboard')}
            className="h-11 rounded-[10px] bg-celadon px-5 text-sm font-semibold text-white hover:bg-celadon-deep"
          >
            New booking
          </button>
        </div>

        <section className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-[34px] font-bold leading-[1.1] tracking-tight">{headline}</h1>
            <p className="mt-2 text-sm text-ink-soft">
              Green cells are free. Bars are bookings, coloured by course.
            </p>
          </div>
        </section>

        {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

        <div className="flex flex-wrap items-start gap-5">
          <section
            aria-label="Therapist schedule"
            className="min-w-0 flex-[999_1_560px] overflow-hidden rounded-[14px] border border-line bg-linen"
          >
            {shopId && (
              <TherapistGantt
                key={boardKey}
                shopId={Number(shopId)}
                date={date}
                duration={15}
                numberOfPeople={1}
                showDetails={true}
              />
            )}
          </section>

          <aside aria-label="Arriving next" className="min-w-[280px] max-w-[360px] flex-[1_1_300px]">
            <h2 className="mb-2 text-xl font-bold">Arriving next</h2>
            {waiting.length === 0 ? (
              <p className="border-t border-line py-4 text-sm text-ink-soft">
                No one is waiting to check in on {dateLabel}.
              </p>
            ) : (
              <ul>
                {waiting.slice(0, 6).map(b => {
                  const late = isToday && timeToMin(b.startTime) < nowMin;
                  return (
                    <li key={b.bookingId} className="flex items-center gap-3.5 border-b border-line py-3.5">
                      <div className="w-14 shrink-0 font-display text-[22px] font-bold tracking-tight">{b.startTime}</div>
                      <button
                        type="button"
                        onClick={() => router.push(`/bookings/${b.bookingId}`)}
                        className="min-w-0 flex-1 text-left text-sm leading-snug"
                      >
                        <span className="block truncate font-semibold">
                          {b.phoneNumber}{b.numberOfPeople > 1 ? `, ${b.numberOfPeople} guests` : ''}
                        </span>
                        <span className="block truncate text-ink-soft">
                          {therapistNames(b)}{late ? ', was due' : ''}
                        </span>
                      </button>
                      <button
                        type="button"
                        onClick={() => checkIn(b.bookingId)}
                        className="h-11 shrink-0 rounded-[10px] border border-celadon px-3.5 text-[13px] font-semibold text-celadon-deep hover:bg-celadon-soft"
                      >
                        Check in
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
            <p className="mt-3 text-[13px] leading-relaxed text-ink-soft">
              Guests are checked in when they reach the front desk. Group bookings get therapists assigned automatically.
            </p>
          </aside>
        </div>
      </main>
    </div>
  );
}

export default function AdminPage() {
  return (
    <RequireAuth allowedRoles={['admin']}>
      <AdminDashboard />
    </RequireAuth>
  );
}
