'use client';

import { useState, useEffect } from 'react';
import RequireAuth from '@/components/RequireAuth';
import AdminSidebar from '@/components/AdminSidebar';
import { api } from '@/lib/api';
import { localDateStr } from '@/lib/dates';

type Shift = { shiftId: number; therapistId: number; dayOfWeek: string; startTime: string; endTime: string; effectiveFrom: string };
type Shop = { shopId?: number; id?: number; shopName: string };
type Therapist = { therapistId?: number; id?: number; name: string };
type ScheduleBooking = { bookingId: number; date: string; startTime: string; endTime: string; bookingCode: string; customerPhone: string; status: string };
const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const emptyForm = () => ({ dayOfWeek: 'Monday', startTime: '09:00', endTime: '17:00', effectiveFrom: localDateStr() });

function AdminSchedules() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [shopId, setShopId] = useState<number | ''>('');
  const [therapists, setTherapists] = useState<Therapist[]>([]);
  const [therapistId, setTherapistId] = useState<number | ''>('');
  const [dateFrom, setDateFrom] = useState(localDateStr);
  const [dateTo, setDateTo] = useState(localDateStr);
  const [schedule, setSchedule] = useState<ScheduleBooking[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [shiftForm, setShiftForm] = useState(emptyForm);
  const [editingShiftId, setEditingShiftId] = useState<number | null>(null);
  const [shiftError, setShiftError] = useState('');
  const [shiftLoading, setShiftLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.admin.getShops().then(res => {
      const list = (res.data?.data || res.data || []) as Shop[];
      setShops(list);
      if (list.length) setShopId(list[0].shopId ?? list[0].id ?? '');
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!shopId) return;
    let active = true;
    api.admin.getTherapists(Number(shopId)).then(res => {
      if (!active) return;
      const list = (res.data?.data || res.data || []) as Therapist[];
      setTherapists(list);
      if (list.length) {
        setShiftLoading(true);
        setTherapistId(list[0].therapistId ?? list[0].id ?? '');
      }
    }).catch(() => { if (active) setTherapists([]); });
    return () => { active = false; };
  }, [shopId]);

  useEffect(() => {
    if (!shopId || !therapistId) return;
    let active = true;
    api.admin.getTherapistShifts(Number(shopId), { therapistId: Number(therapistId) }).then(res => {
      if (active) setShifts(res.data || []);
    }).catch((e: Error) => { if (active) setShiftError(e.message); }).finally(() => {
      if (active) setShiftLoading(false);
    });
    return () => { active = false; };
  }, [shopId, therapistId]);

  const reloadShifts = async () => {
    if (!shopId || !therapistId) return;
    const res = await api.admin.getTherapistShifts(Number(shopId), { therapistId: Number(therapistId) });
    setShifts(res.data || []);
  };

  const saveShift = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!therapistId || saving) return;
    setSaving(true);
    setShiftError('');
    try {
      if (editingShiftId === null) {
        await api.admin.createTherapistShift({ therapistId: Number(therapistId), ...shiftForm });
      } else {
        await api.admin.updateTherapistShift(editingShiftId, shiftForm);
      }
      await reloadShifts();
      setEditingShiftId(null);
      setShiftForm(emptyForm());
    } catch (e) { setShiftError(e instanceof Error ? e.message : 'Could not save shift'); }
    finally { setSaving(false); }
  };

  const deleteShift = async (shift: Shift) => {
    if (saving || !window.confirm(`Delete ${shift.dayOfWeek} ${shift.startTime}–${shift.endTime} shift?`)) return;
    setSaving(true);
    setShiftError('');
    try {
      await api.admin.deleteTherapistShift(shift.shiftId);
      await reloadShifts();
      if (editingShiftId === shift.shiftId) { setEditingShiftId(null); setShiftForm(emptyForm()); }
    } catch (e) { setShiftError(e instanceof Error ? e.message : 'Could not delete shift'); }
    finally { setSaving(false); }
  };

  const loadSchedule = async () => {
    if (!therapistId) return;
    try {
      const res = await api.admin.getTherapistSchedule(Number(therapistId), dateFrom, dateTo);
      setSchedule(res.data?.schedule || []);
    } catch (e) { alert(e instanceof Error ? e.message : 'Could not load schedule'); }
    setLoaded(true);
  };

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Therapist Schedules</h1>

        <div className="bg-white rounded-xl shadow border border-gray-200 p-6 mb-6 grid md:grid-cols-4 gap-4 items-end">
          <div>
            <label htmlFor="schedule-shop" className="text-sm text-gray-600 block mb-1">Shop</label>
            <select id="schedule-shop" value={shopId} onChange={e => { setShopId(Number(e.target.value)); setTherapists([]); setTherapistId(''); setShifts([]); setShiftLoading(false); setLoaded(false); setEditingShiftId(null); setShiftForm(emptyForm()); }} className="border rounded-lg px-3 py-2 text-sm w-full">
              {shops.map(s => <option key={s.shopId ?? s.id} value={s.shopId ?? s.id}>{s.shopName}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="schedule-therapist" className="text-sm text-gray-600 block mb-1">Therapist</label>
            <select id="schedule-therapist" value={therapistId} onChange={e => { setTherapistId(Number(e.target.value)); setShifts([]); setShiftLoading(true); setShiftError(''); setLoaded(false); setEditingShiftId(null); setShiftForm(emptyForm()); }} className="border rounded-lg px-3 py-2 text-sm w-full">
              {therapists.map(t => <option key={t.therapistId ?? t.id} value={t.therapistId ?? t.id}>{t.name}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="schedule-from" className="text-sm text-gray-600 block mb-1">From</label>
            <input id="schedule-from" type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="border rounded-lg px-3 py-2 text-sm w-full" />
          </div>
          <div>
            <label htmlFor="schedule-to" className="text-sm text-gray-600 block mb-1">To</label>
            <input id="schedule-to" type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="border rounded-lg px-3 py-2 text-sm w-full" />
          </div>
          <button onClick={loadSchedule} disabled={!therapistId} className="md:col-span-4 bg-[#1F2B2A] text-white py-2.5 rounded-lg disabled:opacity-50">View Schedule</button>
        </div>

        <section aria-label="Weekly shifts" className="bg-white rounded-xl shadow border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Weekly shifts</h2>
          {shiftError && <div role="alert" className="text-red-700 mb-4">{shiftError}</div>}
          <form onSubmit={saveShift} className="grid md:grid-cols-4 gap-4 items-end mb-6">
            <div>
              <label htmlFor="shift-day" className="text-sm text-gray-600 block mb-1">Day</label>
              <select id="shift-day" value={shiftForm.dayOfWeek} onChange={e => setShiftForm({ ...shiftForm, dayOfWeek: e.target.value })} className="border rounded-lg px-3 py-2 text-sm w-full">
                {days.map(day => <option key={day} value={day}>{day}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="shift-start" className="text-sm text-gray-600 block mb-1">Shift start</label>
              <input id="shift-start" type="time" required value={shiftForm.startTime} onChange={e => setShiftForm({ ...shiftForm, startTime: e.target.value })} className="border rounded-lg px-3 py-2 text-sm w-full" />
            </div>
            <div>
              <label htmlFor="shift-end" className="text-sm text-gray-600 block mb-1">Shift end</label>
              <input id="shift-end" type="time" required value={shiftForm.endTime} onChange={e => setShiftForm({ ...shiftForm, endTime: e.target.value })} className="border rounded-lg px-3 py-2 text-sm w-full" />
            </div>
            <div>
              <label htmlFor="shift-effective" className="text-sm text-gray-600 block mb-1">Effective from</label>
              <input id="shift-effective" type="date" required value={shiftForm.effectiveFrom} onChange={e => setShiftForm({ ...shiftForm, effectiveFrom: e.target.value })} className="border rounded-lg px-3 py-2 text-sm w-full" />
            </div>
            <button type="submit" disabled={!therapistId || saving} className="bg-[#1F2B2A] text-white py-2.5 rounded-lg disabled:opacity-50">{editingShiftId === null ? 'Add shift' : 'Save shift'}</button>
            {editingShiftId !== null && <button type="button" onClick={() => { setEditingShiftId(null); setShiftForm(emptyForm()); }} className="border rounded-lg py-2.5">Cancel edit</button>}
          </form>
          {shiftLoading ? <p className="text-gray-500">Loading shifts...</p> : !therapistId ? <p className="text-gray-500">Select a therapist to manage shifts.</p> : shifts.length === 0 ? <p className="text-gray-500">No weekly shifts.</p> : (
            <div className="space-y-2">
              {[...shifts].sort((a, b) => days.indexOf(a.dayOfWeek) - days.indexOf(b.dayOfWeek) || a.startTime.localeCompare(b.startTime)).map(shift => (
                <div key={shift.shiftId} className="border rounded-lg p-3 flex flex-wrap gap-3 items-center justify-between">
                  <div><strong>{shift.dayOfWeek}</strong> · {shift.startTime}–{shift.endTime}<span className="text-gray-500 ml-2">from {shift.effectiveFrom}</span></div>
                  <div className="flex gap-2">
                    <button type="button" disabled={saving} onClick={() => { setEditingShiftId(shift.shiftId); setShiftForm({ dayOfWeek: shift.dayOfWeek, startTime: shift.startTime, endTime: shift.endTime, effectiveFrom: shift.effectiveFrom }); setShiftError(''); }} className="border rounded-lg px-3 py-1 disabled:opacity-50">Edit</button>
                    <button type="button" disabled={saving} onClick={() => deleteShift(shift)} className="border rounded-lg px-3 py-1 text-red-700 disabled:opacity-50">Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section aria-label="Bookings">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Bookings</h2>

        {loaded && (
          schedule.length === 0 ? <div className="text-gray-500">No bookings in this range.</div> : (
            <div className="space-y-2">
              {schedule.map((b, i) => (
                <div key={b.bookingId || i} className="bg-white rounded-lg shadow border border-gray-200 p-4">
                  <div className="font-semibold text-gray-900">{b.date} · {b.startTime}–{b.endTime}</div>
                  <div className="text-sm text-gray-600">#{b.bookingCode} · {b.customerPhone}</div>
                  <div className="text-xs text-gray-400">{b.status}</div>
                </div>
              ))}
            </div>
          )
        )}
        </section>
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
