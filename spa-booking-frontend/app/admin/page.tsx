'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import RequireAuth from '@/components/RequireAuth';
import AdminSidebar from '@/components/AdminSidebar';
import TherapistGantt from '@/components/TherapistGantt';
import { api } from '@/lib/api';

function getStatusColor(status: string) {
  switch (status) {
    case 'Booked': return 'bg-blue-100 text-blue-800';
    case 'CheckedIn': return 'bg-green-100 text-green-800';
    case 'CheckedOut': return 'bg-gray-100 text-gray-800';
    case 'Cancelled': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-800';
  }
}

function AdminDashboard() {
  const router = useRouter();
  const today = new Date().toISOString().slice(0, 10);
  const [shops, setShops] = useState<any[]>([]);
  const [shopId, setShopId] = useState<number | ''>('');
  const [date, setDate] = useState(today);
  const [bookings, setBookings] = useState<any[]>([]);

  useEffect(() => {
    api.admin.getShops().then(res => {
      const list = res.data?.data || res.data || [];
      setShops(list);
      if (list.length) setShopId(list[0].shopId || list[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!shopId) return;
    api.admin.getBookings({ shopId: Number(shopId), dateFrom: date, dateTo: date }).then(res => {
      setBookings(res.data?.data || res.data || []);
    }).catch(() => {});
  }, [shopId, date]);

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="flex-1 p-4 overflow-auto">
        <div className="flex items-center gap-4 mb-4 flex-wrap">
          <select
            value={shopId}
            onChange={e => setShopId(Number(e.target.value))}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white"
          >
            {shops.map((s: any) => (
              <option key={s.shopId || s.id} value={s.shopId || s.id}>{s.shopName}</option>
            ))}
          </select>
          <input
            type="date"
            value={date}
            onChange={e => setDate(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
          />
        </div>

        <div className="bg-white rounded-xl shadow border border-gray-200 p-4 mb-6 overflow-auto">
          {shopId && (
            <TherapistGantt
              shopId={Number(shopId)}
              date={date}
              duration={60}
              numberOfPeople={1}
              showDetails={true}
            />
          )}
        </div>

        <div className="space-y-2">
          <h2 className="text-lg font-semibold text-gray-900">Bookings on {date}</h2>
          {bookings.length === 0 ? (
            <div className="text-gray-500 text-sm">No bookings for this date.</div>
          ) : (
            bookings.map(b => (
              <div
                key={b.bookingId}
                onClick={() => router.push(`/bookings/${b.bookingId}`)}
                className="bg-white rounded-lg shadow border border-gray-200 p-3 cursor-pointer hover:shadow-md transition flex items-center justify-between"
              >
                <div>
                  <div className="font-semibold text-gray-900 text-sm">#{b.bookingCode}</div>
                  <div className="text-xs text-gray-600">{b.startTime}–{b.endTime} · {b.phoneNumber}</div>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs ${getStatusColor(b.status)}`}>{b.status}</span>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}

export default function AdminPage() {
  return (
    <RequireAuth allowedRoles={['admin']}>
      <AdminDashboard />
    </RequireAuth>
  );
}
