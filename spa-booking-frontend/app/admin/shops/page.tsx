'use client';

import { useState, useEffect } from 'react';
import RequireAuth from '@/components/RequireAuth';
import AdminSidebar from '@/components/AdminSidebar';
import { api } from '@/lib/api';

function AdminShops() {
  const [shops, setShops] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ shopName: '', address: '', phoneNumber: '', openTime: '08:00', closeTime: '21:00' });

  const load = async () => {
    try {
      const res = await api.admin.getShops();
      setShops(res.data?.data || res.data || []);
    } catch (e) { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.admin.createShop(form);
      setForm({ shopName: '', address: '', phoneNumber: '', openTime: '08:00', closeTime: '21:00' });
      load();
    } catch (e: any) { alert(e.message); }
  };

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Shops</h1>

        <form onSubmit={handleCreate} className="bg-white rounded-xl shadow border border-gray-200 p-6 mb-6 grid md:grid-cols-2 gap-4">
          <input placeholder="Shop Name" value={form.shopName} onChange={e => setForm({ ...form, shopName: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" required />
          <input placeholder="Address" value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" required />
          <input placeholder="Phone Number" value={form.phoneNumber} onChange={e => setForm({ ...form, phoneNumber: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" required />
          <div className="flex gap-2">
            <input type="time" value={form.openTime} onChange={e => setForm({ ...form, openTime: e.target.value })} className="border rounded-lg px-3 py-2 text-sm flex-1" />
            <input type="time" value={form.closeTime} onChange={e => setForm({ ...form, closeTime: e.target.value })} className="border rounded-lg px-3 py-2 text-sm flex-1" />
          </div>
          <button type="submit" className="md:col-span-2 bg-[#031050] text-white py-2.5 rounded-lg hover:bg-[#1a2a6b]">Create Shop</button>
        </form>

        {loading ? <div className="text-gray-400">Loading...</div> : (
          <div className="space-y-3">
            {shops.map((s: any) => (
              <div key={s.shopId || s.id} className="bg-white rounded-lg shadow border border-gray-200 p-4">
                <div className="font-semibold text-gray-900">{s.shopName}</div>
                <div className="text-sm text-gray-600">{s.address} · {s.phoneNumber}</div>
                <div className="text-xs text-gray-400 mt-1">{s.status} · {s.openTime}–{s.closeTime}</div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

export default function Page() {
  return (
    <RequireAuth allowedRoles={['admin']}>
      <AdminShops />
    </RequireAuth>
  );
}
