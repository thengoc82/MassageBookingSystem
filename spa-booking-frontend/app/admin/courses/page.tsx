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
  const [form, setForm] = useState({
    courseName: '',
    courseType: 'main' as 'main' | 'addon',
    durations: [{ duration: 15, price: 0 }] as { duration: number; price: number }[],
  });

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
      await api.admin.createCourse(Number(shopId), {
        courseName: form.courseName,
        courseType: form.courseType,
        durations: form.durations.filter(d => d.duration > 0),
      });
      setForm({ courseName: '', courseType: 'main', durations: [{ duration: 15, price: 0 }] });
      load();
    } catch (e: any) { alert(e.message); }
  };

  const addDurationRow = () => {
    setForm(f => ({ ...f, durations: [...f.durations, { duration: 15, price: 0 }] }));
  };

  const removeDurationRow = (i: number) => {
    setForm(f => ({ ...f, durations: f.durations.filter((_, idx) => idx !== i) }));
  };

  const updateDuration = (i: number, field: 'duration' | 'price', value: number) => {
    setForm(f => {
      const d = [...f.durations];
      d[i] = { ...d[i], [field]: value };
      return { ...f, durations: d };
    });
  };

  const presetDurations = (type: 'fullbody' | 'other') => {
    if (type === 'fullbody') {
      setForm(f => ({ ...f, durations: [15, 30, 45, 60].map(d => ({ duration: d, price: d * 100 })) }));
    } else {
      setForm(f => ({ ...f, durations: [15, 30].map(d => ({ duration: d, price: d * 100 })) }));
    }
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

        <form onSubmit={handleCreate} className="bg-white rounded-xl shadow border border-gray-200 p-6 mb-6 space-y-4">
          <div className="grid md:grid-cols-3 gap-4">
            <input placeholder="Course Name" value={form.courseName} onChange={e => setForm({ ...form, courseName: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" required />
            <select value={form.courseType} onChange={e => setForm({ ...form, courseType: e.target.value as 'main' | 'addon' })} className="border rounded-lg px-3 py-2 text-sm">
              <option value="main">Main</option>
              <option value="addon">Addon</option>
            </select>
            <div className="flex gap-2">
              <button type="button" onClick={() => presetDurations('fullbody')} className="text-xs bg-gray-100 px-3 py-2 rounded hover:bg-gray-200">Full Body (15-60)</button>
              <button type="button" onClick={() => presetDurations('other')} className="text-xs bg-gray-100 px-3 py-2 rounded hover:bg-gray-200">Other (15-30)</button>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Durations & Prices</span>
              <button type="button" onClick={addDurationRow} className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700">+ Add</button>
            </div>
            {form.durations.map((d, i) => (
              <div key={i} className="flex items-center gap-2">
                <input type="number" placeholder="Min" value={d.duration} onChange={e => updateDuration(i, 'duration', Number(e.target.value))} className="border rounded-lg px-3 py-2 text-sm w-24" min={0} required />
                <span className="text-sm text-gray-500">min</span>
                <input type="number" placeholder="Price" value={d.price} onChange={e => updateDuration(i, 'price', Number(e.target.value))} className="border rounded-lg px-3 py-2 text-sm w-32" min={0} required />
                {form.durations.length > 1 && (
                  <button type="button" onClick={() => removeDurationRow(i)} className="text-xs text-red-600 hover:underline">Remove</button>
                )}
              </div>
            ))}
          </div>

          <button type="submit" className="bg-[#031050] text-white py-2.5 rounded-lg hover:bg-[#1a2a6b] w-full">Create Course</button>
        </form>

        {loading ? <div className="text-gray-400">Loading...</div> : (
          <div className="space-y-4">
            {courses.map((c: any) => (
              <div key={c.courseId} className="bg-white rounded-lg shadow border border-gray-200 p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-semibold text-gray-900">{c.courseName}</div>
                    <div className="text-xs text-gray-400 uppercase">{c.courseType} · {c.status || 'active'}</div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 mt-2">
                  {(c.durations || []).map((d: any, i: number) => (
                    <span key={i} className="bg-gray-100 text-gray-700 text-xs px-2.5 py-1 rounded-full">
                      {d.duration}min · {d.price.toLocaleString()} VND
                    </span>
                  ))}
                </div>
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
