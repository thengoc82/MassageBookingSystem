'use client';

import { useState } from 'react';
import RequireAuth from '@/components/RequireAuth';
import TherapistSidebar from '@/components/TherapistSidebar';
import { api } from '@/lib/api';

function TherapistSchedule() {
  const [dateFrom, setDateFrom] = useState(new Date().toISOString().slice(0, 10));
  const [dateTo, setDateTo] = useState(new Date().toISOString().slice(0, 10));
  const [schedule, setSchedule] = useState<any[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setError('');
    try {
      const res = await api.therapist.getSchedule(dateFrom, dateTo);
      setSchedule(res.data?.schedule || res.data || []);
    } catch (e: any) { setError(e.message); }
    setLoaded(true);
  };

  return (
    <div className="flex">
      <TherapistSidebar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">My Schedule</h1>

        <div className="bg-white rounded-xl shadow border border-gray-200 p-6 mb-6 grid md:grid-cols-3 gap-4 items-end">
          <div>
            <label className="text-sm text-gray-600 block mb-1">From</label>
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="border rounded-lg px-3 py-2 text-sm w-full" />
          </div>
          <div>
            <label className="text-sm text-gray-600 block mb-1">To</label>
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="border rounded-lg px-3 py-2 text-sm w-full" />
          </div>
          <button onClick={load} className="bg-[#031050] text-white py-2.5 rounded-lg hover:bg-[#1a2a6b]">View Schedule</button>
        </div>

        {error && <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded mb-4 text-sm">{error}</div>}

        {loaded && (
          schedule.length === 0 ? <div className="text-gray-500">No bookings in this range.</div> : (
            <div className="space-y-2">
              {schedule.map((b: any, i: number) => (
                <div key={i} className="bg-white rounded-lg shadow border border-gray-200 p-4">
                  <div className="font-semibold text-gray-900">{b.date} · {b.startTime}–{b.endTime}</div>
                  <div className="text-sm text-gray-600">#{b.bookingCode} · {b.customerPhone}</div>
                  <div className="text-xs text-gray-400">{b.status}</div>
                </div>
              ))}
            </div>
          )
        )}
      </main>
    </div>
  );
}

export default function Page() {
  return (
    <RequireAuth allowedRoles={['therapist']}>
      <TherapistSchedule />
    </RequireAuth>
  );
}
