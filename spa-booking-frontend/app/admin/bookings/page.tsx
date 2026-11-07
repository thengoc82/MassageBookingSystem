'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Search } from 'lucide-react';
import RequireAuth from '@/components/RequireAuth';
import AdminSidebar from '@/components/AdminSidebar';
import { api } from '@/lib/api';
import { localDateStr } from '@/lib/dates';

type Action = 'cancel' | 'checkin' | 'checkout';

const COLUMNS = [
  { status: 'Booked', title: 'Booked', hint: 'Waiting to arrive', tint: 'bg-[#E2E9E6]' },
  { status: 'CheckedIn', title: 'Checked in', hint: 'In a session now', tint: 'bg-[#F4E7CC]' },
  { status: 'CheckedOut', title: 'Checked out', hint: 'Finished', tint: 'bg-[#E2E9E6]' },
] as const;

function therapistLine(b: any): { initials: string; text: string } {
  if (Array.isArray(b.therapistAssignments) && b.therapistAssignments.length > 0) {
    const list = b.therapistAssignments
      .slice()
      .sort((a: any, c: any) => a.personIndex - c.personIndex);
    const first = list[0].therapistName as string;
    const initials = first.split(/\s+/).slice(0, 2).map(p => p[0]).join('').toUpperCase();
    return {
      initials,
      text: list.length > 1
        ? list.map((t: any) => `P${t.personIndex} ${t.therapistName}`).join(', ')
        : first,
    };
  }
  if (b.therapistName) {
    return {
      initials: b.therapistName.split(/\s+/).slice(0, 2).map((p: string) => p[0]).join('').toUpperCase(),
      text: b.therapistName,
    };
  }
  return { initials: '?', text: 'Assigned at check-in' };
}

function BookingCard({ b, onAction, onOpen }: { b: any; onAction: (id: number, a: Action) => void; onOpen: (id: number) => void }) {
  const t = therapistLine(b);
  const done = b.status === 'CheckedOut';
  return (
    <article
      className={`flex flex-col gap-2.5 rounded-[10px] bg-linen ring-1 ring-line ${done ? 'p-3 opacity-80' : 'p-3.5'}`}
    >
      <div className="flex items-baseline gap-2.5">
        <button
          type="button"
          onClick={() => onOpen(b.bookingId)}
          className="font-display text-xl font-bold tracking-tight hover:underline"
        >
          {b.startTime} to {b.endTime}
        </button>
        <span className="flex-1" />
        {b.status === 'CheckedIn' && (
          <span className="flex items-center gap-1.5 text-[13px] font-semibold text-[#7A4F0B]">
            <span aria-hidden="true" className="h-2 w-2 rounded-full bg-amber" />
            In session
          </span>
        )}
        {b.numberOfPeople > 1 && (
          <span className="rounded-full bg-celadon-soft px-2 py-0.5 text-xs font-semibold text-[#1F4A41]">
            {b.numberOfPeople} guests
          </span>
        )}
      </div>
      <div className="text-sm leading-snug">
        <div className="font-semibold">{b.phoneNumber}</div>
        <div className="text-ink-soft">#{b.bookingCode}{b.bookingDate ? `, ${b.bookingDate}` : ''}</div>
      </div>
      <div className="flex items-center gap-2">
        <span aria-hidden="true" className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full bg-celadon-soft text-[11px] font-semibold">
          {t.initials}
        </span>
        <span className="min-w-0 flex-1 truncate text-[13px] text-ink-soft">{t.text}</span>
        {b.status === 'Booked' && (
          <>
            <button
              type="button"
              onClick={() => onAction(b.bookingId, 'cancel')}
              className="h-11 rounded-[10px] px-3 text-[13px] font-semibold text-red-700 hover:bg-red-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => onAction(b.bookingId, 'checkin')}
              className="h-11 rounded-[10px] bg-celadon px-4 text-[13px] font-semibold text-white hover:bg-celadon-deep"
            >
              Check in
            </button>
          </>
        )}
        {b.status === 'CheckedIn' && (
          <button
            type="button"
            onClick={() => onAction(b.bookingId, 'checkout')}
            className="h-11 rounded-[10px] bg-celadon px-4 text-[13px] font-semibold text-white hover:bg-celadon-deep"
          >
            Check out
          </button>
        )}
      </div>
    </article>
  );
}

function AdminBookings() {
  const router = useRouter();
  const today = localDateStr();
  const [bookings, setBookings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [date, setDate] = useState(today); // '' means every date
  const [query, setQuery] = useState('');
  const [showCancelled, setShowCancelled] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = { size: '200' };
      if (date) {
        params.dateFrom = date;
        params.dateTo = date;
      }
      const res = await api.admin.getBookings(params);
      setBookings(res.data?.data || res.data || []);
      setError('');
    } catch (e: any) {
      setError(e.message || 'Failed to load bookings');
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => { load(); }, [load]);

  const handleAction = async (id: number, action: Action) => {
    try {
      if (action === 'cancel') await api.admin.cancelBooking(id);
      if (action === 'checkin') await api.admin.checkinBooking(id);
      if (action === 'checkout') await api.admin.checkoutBooking(id);
      load();
    } catch (e: any) {
      setError(e.message || 'Action failed');
    }
  };

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = q
      ? bookings.filter(b => `${b.phoneNumber} ${b.bookingCode}`.toLowerCase().includes(q))
      : bookings;
    return list.slice().sort((a, b) => `${a.bookingDate}${a.startTime}`.localeCompare(`${b.bookingDate}${b.startTime}`));
  }, [bookings, query]);

  const cancelled = visible.filter(b => b.status === 'Cancelled');
  const active = bookings.filter(b => b.status !== 'Cancelled').length;

  const subtitle = date
    ? `${new Date(date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'short' })}. ${active} bookings, ${bookings.length - active} cancelled.`
    : `All dates. ${active} bookings, ${bookings.length - active} cancelled.`;

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="min-w-0 flex-1 space-y-5 px-8 py-6">
        <header className="flex flex-wrap items-end gap-4">
          <div className="flex-1">
            <h1 className="text-[34px] font-bold leading-[1.1] tracking-tight">Bookings</h1>
            <p className="mt-2 text-sm text-ink-soft">{subtitle}</p>
          </div>
          <div className="flex h-11 min-w-[240px] items-center gap-2 rounded-[10px] border border-[#C5D0CC] bg-linen px-3.5 text-sm">
            <Search size={16} aria-hidden="true" className="text-ink-soft" />
            <label htmlFor="q" className="sr-only">Search bookings</label>
            <input
              id="q"
              type="search"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Find by phone or code"
              className="w-full bg-transparent outline-none"
            />
          </div>
          <div className="flex items-center gap-1">
            <label htmlFor="date" className="sr-only">Date</label>
            <input
              id="date"
              type="date"
              value={date}
              onChange={e => setDate(e.target.value)}
              className="h-11 rounded-[10px] border border-[#C5D0CC] bg-linen px-3 text-sm font-medium"
            />
            <button
              type="button"
              onClick={() => setDate(date ? '' : today)}
              className="h-11 rounded-[10px] px-3 text-sm font-semibold text-celadon-deep hover:bg-celadon-soft"
            >
              {date ? 'All dates' : 'Today'}
            </button>
          </div>
        </header>

        {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

        {loading ? (
          <div className="text-ink-soft">Loading bookings…</div>
        ) : (
          <>
            <div className="flex flex-wrap items-start gap-5">
              {COLUMNS.map(col => {
                const cards = visible.filter(b => b.status === col.status);
                return (
                  <section
                    key={col.status}
                    aria-label={col.title}
                    className={`flex min-w-[280px] flex-[1_1_300px] flex-col gap-3 rounded-[14px] p-4 ${col.tint}`}
                  >
                    <div className="flex items-baseline gap-2.5">
                      <h2 className="text-xl font-bold">{col.title}</h2>
                      <span className="text-sm font-semibold text-ink-soft">{cards.length}</span>
                      <span className="flex-1" />
                      <span className="text-[13px] text-ink-soft">{col.hint}</span>
                    </div>
                    {cards.length === 0 ? (
                      <p className="py-6 text-center text-sm text-ink-soft">Nothing here.</p>
                    ) : (
                      cards.map(b => (
                        <BookingCard
                          key={b.bookingId}
                          b={b}
                          onAction={handleAction}
                          onOpen={id => router.push(`/bookings/${id}`)}
                        />
                      ))
                    )}
                  </section>
                );
              })}
            </div>

            {cancelled.length > 0 && (
              <div>
                <button
                  type="button"
                  aria-expanded={showCancelled}
                  onClick={() => setShowCancelled(v => !v)}
                  className="h-11 rounded-[10px] px-3 text-sm font-semibold text-celadon-deep hover:bg-celadon-soft"
                >
                  {showCancelled ? 'Hide' : 'Show'} {cancelled.length} cancelled
                </button>
                {showCancelled && (
                  <ul className="mt-2 divide-y divide-line rounded-[10px] bg-linen ring-1 ring-line">
                    {cancelled.map(b => (
                      <li key={b.bookingId} className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm text-ink-soft">
                        <span className="font-semibold text-basalt">{b.startTime} to {b.endTime}</span>
                        <span>{b.phoneNumber}</span>
                        <span>#{b.bookingCode}</span>
                        <button
                          type="button"
                          onClick={() => router.push(`/bookings/${b.bookingId}`)}
                          className="ml-auto font-semibold text-celadon-deep hover:underline"
                        >
                          View details
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default function Page() {
  return (
    <RequireAuth allowedRoles={['admin']}>
      <AdminBookings />
    </RequireAuth>
  );
}
