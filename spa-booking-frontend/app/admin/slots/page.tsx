'use client';

import { useState, useEffect } from 'react';
import RequireAuth from '@/components/RequireAuth';
import AdminSidebar from '@/components/AdminSidebar';
import TherapistGantt from '@/components/TherapistGantt';
import { api } from '@/lib/api';

function AdminSlots() {
  const [shops, setShops] = useState<any[]>([]);
  const [shopId, setShopId] = useState<number | ''>('');
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));

  useEffect(() => {
    api.admin.getShops().then(res => {
      const list = res.data?.data || res.data || [];
      setShops(list);
      if (list.length) setShopId(list[0].shopId || list[0].id);
    }).catch(() => {});
  }, []);

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Booked & Available Slots</h1>

        <div className="bg-white rounded-xl shadow border border-gray-200 p-6 mb-6 grid md:grid-cols-2 gap-4 items-end">
          <div>
            <label className="text-sm text-gray-600 block mb-1">Shop</label>
            <select value={shopId} onChange={e => setShopId(Number(e.target.value))} className="border rounded-lg px-3 py-2 text-sm w-full">
              {shops.map((s: any) => <option key={s.shopId || s.id} value={s.shopId || s.id}>{s.shopName}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm text-gray-600 block mb-1">Date</label>
            <input type="date" value={date} onChange={e => setDate(e.target.value)} className="border rounded-lg px-3 py-2 text-sm w-full" />
          </div>
        </div>

        {shopId && (
          <div className="bg-white rounded-xl shadow border border-gray-200 p-4">
            <TherapistGantt shopId={Number(shopId)} date={date} duration={60} numberOfPeople={1} />
          </div>
        )}
      </main>
    </div>
  );
}

export default function Page() {
  return (
    <RequireAuth allowedRoles={['admin']}>
      <AdminSlots />
    </RequireAuth>
  );
}
