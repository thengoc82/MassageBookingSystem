'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import RequireAuth from '@/components/RequireAuth';
import TherapistSidebar from '@/components/TherapistSidebar';
import { api } from '@/lib/api';

function TherapistDashboard() {
  const router = useRouter();
  const today = new Date().toISOString().slice(0, 10);

  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.therapist.getBookings({ dateFrom: today, dateTo: today }).then(res => {
      setAppointments(res.data?.data || res.data || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex">
      <TherapistSidebar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Today's Appointments</h1>
        <p className="text-gray-600 mb-6">{today}</p>

        {loading ? <div className="text-gray-400">Loading...</div> : appointments.length === 0 ? (
          <div className="text-gray-500">No appointments today.</div>
        ) : (
          <div className="space-y-3">
            {appointments.map(b => (
              <div key={b.bookingId} className="bg-white rounded-lg shadow border border-gray-200 p-4">
                <div className="font-semibold text-gray-900">{b.startTime}–{b.endTime} · #{b.bookingCode}</div>
                <div className="text-sm text-gray-600">Phone: {b.phoneNumber}</div>
                <div className="text-xs text-gray-400">{b.status}</div>
                <button
                  onClick={() => router.push(`/bookings/${b.bookingId}`)}
                  className="mt-2 text-sm text-blue-600 hover:underline"
                >
                  View details
                </button>
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
      <TherapistDashboard />
    </RequireAuth>
  );
}
