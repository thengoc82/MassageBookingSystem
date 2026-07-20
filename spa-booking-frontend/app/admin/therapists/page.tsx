'use client';

import { useState, useEffect } from 'react';
import RequireAuth from '@/components/RequireAuth';
import AdminSidebar from '@/components/AdminSidebar';
import { api } from '@/lib/api';

function AdminTherapists() {
  const [shops, setShops] = useState<any[]>([]);
  const [shopId, setShopId] = useState<number | ''>('');
  const [therapists, setTherapists] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: '', gender: 'Female', phoneNumber: '', username: '', password: '' });

  useEffect(() => {
    api.admin.getShops().then(res => {
      const list = res.data?.data || res.data || [];
      setShops(list);
      if (list.length) setShopId(list[0].shopId || list[0].id);
    }).catch(() => {});
  }, []);

  const load = async () => {
    if (!shopId) return;
    try {
      const res = await api.admin.getTherapists(Number(shopId));
      setTherapists(res.data?.data || res.data || []);
    } catch (e) { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [shopId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.admin.createTherapist(Number(shopId), form);
      setForm({ name: '', gender: 'Female', phoneNumber: '', username: '', password: '' });
      load();
    } catch (e: any) { alert(e.message); }
  };

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Therapists</h1>

        <div className="mb-4">
          <label className="text-sm text-gray-600 mr-2">Shop:</label>
          <select value={shopId} onChange={e => setShopId(Number(e.target.value))} className="border rounded-lg px-3 py-2 text-sm">
            {shops.map((s: any) => <option key={s.shopId || s.id} value={s.shopId || s.id}>{s.shopName}</option>)}
          </select>
        </div>

        <form onSubmit={handleCreate} className="bg-white rounded-xl shadow border border-gray-200 p-6 mb-6 grid md:grid-cols-2 gap-4">
          <input placeholder="Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" required />
          <select value={form.gender} onChange={e => setForm({ ...form, gender: e.target.value })} className="border rounded-lg px-3 py-2 text-sm">
            <option value="Female">Female</option>
            <option value="Male">Male</option>
          </select>
          <input placeholder="Phone Number" value={form.phoneNumber} onChange={e => setForm({ ...form, phoneNumber: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
          <input placeholder="Username (login)" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" required />
          <input placeholder="Password" type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" required />
          <button type="submit" className="md:col-span-2 bg-[#031050] text-white py-2.5 rounded-lg hover:bg-[#1a2a6b]">Create Therapist</button>
        </form>

        {loading ? <div className="text-gray-400">Loading...</div> : (
          <div className="space-y-3">
            {therapists.map((t: any) => (
              <div key={t.therapistId || t.id} className="bg-white rounded-lg shadow border border-gray-200 p-4">
                <div className="font-semibold text-gray-900">{t.name}</div>
                <div className="text-sm text-gray-600">{t.gender} · {t.phoneNumber || '—'}</div>
                <div className="text-xs text-gray-400 mt-1">{t.status} · @{t.username || 'no login'}</div>
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
      <AdminTherapists />
    </RequireAuth>
  );
}
