'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import type { Shop } from '@/types';
import TherapistGantt from '@/components/TherapistGantt';

interface RecentBooking {
  shopId: number;
  date: string;
  startTime: string;
  duration: number;
}

function readRecent(): RecentBooking[] {
  if (typeof window === 'undefined') return [];
  try { return JSON.parse(localStorage.getItem('recentBookings') || '[]'); }
  catch { return []; }
}

function fmtDate(d: Date): string {
  return d.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
}

function daysInMonth(y: number, m: number): number {
  return new Date(y, m + 1, 0).getDate();
}

export default function DashboardPage() {
  const router = useRouter();
  const [date, setDate] = useState(new Date());
  const [shops, setShops] = useState<Shop[]>([]);
  const [shopId, setShopId] = useState<number | null>(null);
  const [showCal, setShowCal] = useState(false);
  const [calMonth, setCalMonth] = useState(date.getMonth());
  const [calYear, setCalYear] = useState(date.getFullYear());
  const [recentBookings] = useState<RecentBooking[]>(() => readRecent());
  const [duration, setDuration] = useState(60);
  const [people, setPeople] = useState(1);

  useEffect(() => {
    api.shops.getAll().then(d => {
      const list = Array.isArray(d) ? d : d.data || [];
      setShops(list);
      if (list.length > 0) setShopId(prev => prev ?? list[0].shopId);
    }).catch(() => {});
  }, []);

  const prevDay = useCallback(() => { setDate(d => { const n = new Date(d); n.setDate(n.getDate() - 1); return n; }); setShowCal(false); }, []);
  const nextDay = useCallback(() => { setDate(d => { const n = new Date(d); n.setDate(n.getDate() + 1); return n; }); setShowCal(false); }, []);

  const handleSlotClick = useCallback((time: string, therapistId: number) => {
    const dateStr = date.toISOString().split('T')[0];
    const params = new URLSearchParams({
      shopId: String(shopId),
      date: dateStr,
      time,
      duration: String(duration),
      people: String(people),
    });
    if (therapistId) params.set('therapistId', String(therapistId));
    router.push(`/reservation?${params.toString()}`);
  }, [date, duration, people, shopId, router]);

  const calDays = useCallback(() => {
    const dim = daysInMonth(calYear, calMonth);
    const firstDay = new Date(calYear, calMonth, 1).getDay();
    const cells: (number | null)[] = Array(firstDay).fill(null);
    for (let d = 1; d <= dim; d++) cells.push(d);
    return cells;
  }, [calMonth, calYear]);

  const todayStr = `${new Date().getFullYear()}-${new Date().getMonth()}-${new Date().getDate()}`;
  const dateStr = date.toISOString().split('T')[0];

  return (
    <div className="h-screen bg-[#F5F7FA] flex flex-col overflow-hidden">
      <div className="bg-white border-b border-gray-200 shrink-0">
        <div className="flex items-center px-4 py-2 gap-4">
          <div className="flex items-center gap-1.5 shrink-0">
            <button onClick={prevDay} className="w-7 h-7 flex items-center justify-center rounded border border-gray-300 hover:bg-gray-100 text-sm text-gray-700">&larr;</button>
            <div className="relative">
              <button onClick={() => setShowCal(p => !p)}
                className="text-sm font-semibold text-gray-900 whitespace-nowrap min-w-[240px] text-center px-2 py-1 rounded hover:bg-gray-100">
                {fmtDate(date)}
              </button>
              {showCal && (
                <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-3 w-64">
                  <div className="flex items-center justify-between mb-2">
                    <button onClick={() => { if (calMonth === 0) { setCalMonth(11); setCalYear(y => y - 1); } else setCalMonth(m => m - 1); }}
                      className="p-1 hover:bg-gray-100 rounded text-xs text-gray-600">&larr;</button>
                    <span className="text-xs font-semibold text-gray-800">{new Date(calYear, calMonth).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</span>
                    <button onClick={() => { if (calMonth === 11) { setCalMonth(0); setCalYear(y => y + 1); } else setCalMonth(m => m + 1); }}
                      className="p-1 hover:bg-gray-100 rounded text-xs text-gray-600">&rarr;</button>
                  </div>
                  <div className="grid grid-cols-7 gap-0 text-center text-[10px] mb-1">
                    {['Su','Mo','Tu','We','Th','Fr','Sa'].map(d => <span key={d} className="text-gray-500 py-1">{d}</span>)}
                  </div>
                  <div className="grid grid-cols-7 gap-0 text-center text-[10px]">
                    {calDays().map((day, i) => {
                      const sel = day === date.getDate() && calMonth === date.getMonth() && calYear === date.getFullYear();
                      return (
                        <button key={i} onClick={() => { if (day) { setDate(new Date(calYear, calMonth, day)); setShowCal(false); } }}
                          className={`py-1 rounded ${day ? (sel ? 'bg-[#031050] text-white' : day && `${calYear}-${calMonth}-${day}` === todayStr ? 'bg-gray-200 text-gray-900 font-bold' : 'text-gray-700 hover:bg-gray-100') : ''}`}
                          disabled={!day}>{day || ''}</button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
            <button onClick={nextDay} className="w-7 h-7 flex items-center justify-center rounded border border-gray-300 hover:bg-gray-100 text-sm text-gray-700">&rarr;</button>
          </div>
          <div className="w-px h-5 bg-gray-300" />
          <select value={shopId ?? ''} onChange={e => setShopId(Number(e.target.value))}
            className="text-xs border border-gray-300 rounded px-2 py-1 bg-white text-gray-700 cursor-pointer">
            {shops.map(s => <option key={s.shopId} value={s.shopId}>{s.shopName}</option>)}
          </select>
          <div className="w-px h-5 bg-gray-300" />
          <select value={duration} onChange={e => setDuration(Number(e.target.value))}
            className="text-xs border border-gray-300 rounded px-2 py-1 bg-white text-gray-700 cursor-pointer">
            {[15, 30, 45, 60, 75, 90].map(d => <option key={d} value={d}>{d} min</option>)}
          </select>
          <select value={people} onChange={e => setPeople(Number(e.target.value))}
            className="text-xs border border-gray-300 rounded px-2 py-1 bg-white text-gray-700 cursor-pointer">
            {[1, 2, 3].map(n => <option key={n} value={n}>{n} {n > 1 ? 'people' : 'person'}</option>)}
          </select>
        </div>
      </div>

      <div className="h-[3px] bg-[#031050] shrink-0" />

      <div className="flex items-center gap-4 px-4 py-1 bg-white border-b border-gray-200 text-[11px] text-gray-700 shrink-0">
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-green-100 border border-green-300" /> Available</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-white border border-gray-300" /> Unavailable</span>
        <span className="ml-auto text-gray-500">Click a green cell to book</span>
      </div>

      <div className="flex-1 min-h-0">
        {shopId ? (
          <TherapistGantt
            shopId={shopId}
            date={dateStr}
            duration={duration}
            numberOfPeople={people}
            onSelectSlot={handleSlotClick}
          />
        ) : (
          <div className="text-center py-8 text-gray-500">Loading shop...</div>
        )}
      </div>
    </div>
  );
}
