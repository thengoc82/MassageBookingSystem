'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import RequireAuth from '@/components/RequireAuth';
import TherapistSidebar from '@/components/TherapistSidebar';
import { api } from '@/lib/api';

function getStatusColor(status: string) {
  switch (status) {
    case 'Booked': return 'bg-celadon-soft text-[#1F4A41]';
    case 'CheckedIn': return 'bg-green-100 text-green-800';
    case 'CheckedOut': return 'bg-gray-100 text-gray-800';
    case 'Cancelled': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-800';
  }
}

function TherapistBookings() {
  const router = useRouter();
  const [bookings, setBookings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const res = await api.therapist.getBookings();
      setBookings(res.data?.data || res.data || []);
    } catch (e: any) { setError(e.message); } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleAction = async (id: number, action: 'checkin' | 'checkout') => {
    try {
      if (action === 'checkin') await api.therapist.checkinBooking(id);
      if (action === 'checkout') await api.therapist.checkoutBooking(id);
      load();
    } catch (e: any) { setError(e.message); }
  };

  return (
    <div className="flex">
      <TherapistSidebar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">My Bookings</h1>
        {error && <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded mb-4 text-sm">{error}</div>}

        {loading ? <div className="text-gray-400">Loading...</div> : bookings.length === 0 ? (
          <div className="text-gray-500">No bookings assigned.</div>
        ) : (
          <div className="space-y-3">
            {bookings.map(b => (
              <div key={b.bookingId} className="bg-white rounded-lg shadow border border-gray-200 p-4 flex items-center justify-between">
                <div className="flex-1 cursor-pointer" onClick={() => router.push(`/bookings/${b.bookingId}`)}>
                  <div className="font-semibold text-gray-900">#{b.bookingCode}</div>
                  <div className="text-sm text-gray-600">{b.bookingDate} · {b.startTime}–{b.endTime} · {b.phoneNumber}</div>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs mr-3 ${getStatusColor(b.status)}`}>{b.status}</span>
                <div className="flex gap-2">
                  {b.status === 'Booked' && (
                    <button onClick={() => handleAction(b.bookingId, 'checkin')} className="px-3 py-1.5 text-xs bg-celadon text-white rounded hover:bg-celadon-deep">Start</button>
                  )}
                  {b.status === 'CheckedIn' && (
                    <button onClick={() => handleAction(b.bookingId, 'checkout')} className="px-3 py-1.5 text-xs bg-celadon text-white rounded hover:bg-celadon-deep">Complete</button>
                  )}
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
    <RequireAuth allowedRoles={['therapist']}>
      <TherapistBookings />
    </RequireAuth>
  );
}
