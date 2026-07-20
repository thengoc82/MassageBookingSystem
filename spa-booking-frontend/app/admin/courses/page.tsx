'use client';

import { useState, useEffect } from 'react';
import RequireAuth from '@/components/RequireAuth';
import AdminSidebar from '@/components/AdminSidebar';
import { api } from '@/lib/api';

function AdminCourses() {
  const [shops, setShops] = useState<any[]>([]);
  const [shopId, setShopId] = useState<number | ''>('');
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ courseName: '', duration: 60, price: 0, courseType: 'main' });

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
      const res = await api.admin.getCourses(Number(shopId));
      setCourses(res.data?.data || res.data || []);
    } catch (e) { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [shopId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.admin.createCourse(Number(shopId), form);
      setForm({ courseName: '', duration: 60, price: 0, courseType: 'main' });
      load();
    } catch (e: any) { alert(e.message); }
  };

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Courses</h1>

        <div className="mb-4">
          <label className="text-sm text-gray-600 mr-2">Shop:</label>
          <select value={shopId} onChange={e => setShopId(Number(e.target.value))} className="border rounded-lg px-3 py-2 text-sm">
            {shops.map((s: any) => <option key={s.shopId || s.id} value={s.shopId || s.id}>{s.shopName}</option>)}
          </select>
        </div>

        <form onSubmit={handleCreate} className="bg-white rounded-xl shadow border border-gray-200 p-6 mb-6 grid md:grid-cols-2 gap-4">
          <input placeholder="Course Name" value={form.courseName} onChange={e => setForm({ ...form, courseName: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" required />
          <select value={form.courseType} onChange={e => setForm({ ...form, courseType: e.target.value })} className="border rounded-lg px-3 py-2 text-sm">
            <option value="main">Main</option>
            <option value="addon">Addon</option>
          </select>
          <input type="number" placeholder="Duration (min)" value={form.duration} onChange={e => setForm({ ...form, duration: Number(e.target.value) })} className="border rounded-lg px-3 py-2 text-sm" required />
          <input type="number" placeholder="Price" value={form.price} onChange={e => setForm({ ...form, price: Number(e.target.value) })} className="border rounded-lg px-3 py-2 text-sm" required />
          <button type="submit" className="md:col-span-2 bg-[#031050] text-white py-2.5 rounded-lg hover:bg-[#1a2a6b]">Create Course</button>
        </form>

        {loading ? <div className="text-gray-400">Loading...</div> : (
          <div className="space-y-3">
            {courses.map((c: any) => (
              <div key={c.courseId || c.id} className="bg-white rounded-lg shadow border border-gray-200 p-4 flex justify-between">
                <div>
                  <div className="font-semibold text-gray-900">{c.courseName}</div>
                  <div className="text-xs text-gray-400">{c.courseType} · {c.duration} min</div>
                </div>
                <div className="font-medium text-gray-700">{c.price}</div>
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
      <AdminCourses />
    </RequireAuth>
  );
}
