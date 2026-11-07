'use client';

import { useState, useEffect } from 'react';
import RequireAuth from '@/components/RequireAuth';
import AdminSidebar from '@/components/AdminSidebar';
import { api } from '@/lib/api';

function AdminSchedules() {
  const [shops, setShops] = useState<any[]>([]);
  const [shopId, setShopId] = useState<number | ''>('');
  const [therapists, setTherapists] = useState<any[]>([]);
  const [therapistId, setTherapistId] = useState<number | ''>('');
  const [dateFrom, setDateFrom] = useState(new Date().toISOString().slice(0, 10));
  const [dateTo, setDateTo] = useState(new Date().toISOString().slice(0, 10));
  const [schedule, setSchedule] = useState<any[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api.admin.getShops().then(res => {
      const list = res.data?.data || res.data || [];
      setShops(list);
      if (list.length) setShopId(list[0].shopId || list[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!shopId) return;
    api.admin.getTherapists(Number(shopId)).then(res => {
      const list = res.data?.data || res.data || [];
      setTherapists(list);
      if (list.length) setTherapistId(list[0].therapistId || list[0].id);
    }).catch(() => {});
  }, [shopId]);

  const loadSchedule = async () => {
    if (!therapistId) return;
    try {
      const res = await api.admin.getTherapistSchedule(Number(therapistId), dateFrom, dateTo);
      setSchedule(res.data?.schedule || []);
    } catch (e: any) { alert(e.message); }
    setLoaded(true);
  };

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Therapist Schedules</h1>

        <div className="bg-white rounded-xl shadow border border-gray-200 p-6 mb-6 grid md:grid-cols-4 gap-4 items-end">
          <div>
            <label className="text-sm text-gray-600 block mb-1">Shop</label>
            <select value={shopId} onChange={e => setShopId(Number(e.target.value))} className="border rounded-lg px-3 py-2 text-sm w-full">
              {shops.map((s: any) => <option key={s.shopId || s.id} value={s.shopId || s.id}>{s.shopName}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm text-gray-600 block mb-1">Therapist</label>
            <select value={therapistId} onChange={e => setTherapistId(Number(e.target.value))} className="border rounded-lg px-3 py-2 text-sm w-full">
              {therapists.map((t: any) => <option key={t.therapistId || t.id} value={t.therapistId || t.id}>{t.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm text-gray-600 block mb-1">From</label>
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="border rounded-lg px-3 py-2 text-sm w-full" />
          </div>
          <div>
            <label className="text-sm text-gray-600 block mb-1">To</label>
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="border rounded-lg px-3 py-2 text-sm w-full" />
          </div>
          <button onClick={loadSchedule} className="md:col-span-4 bg-[#1F2B2A] text-white py-2.5 rounded-lg hover:bg-[#1a2a6b]">View Schedule</button>
        </div>

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
    <RequireAuth allowedRoles={['admin']}>
      <AdminSchedules />
    </RequireAuth>
  );
}
