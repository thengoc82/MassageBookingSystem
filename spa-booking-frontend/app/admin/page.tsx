'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import RequireAuth from '@/components/RequireAuth';
import AdminSidebar from '@/components/AdminSidebar';
import { api } from '@/lib/api';

function AdminDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState({ shops: 0, therapists: 0, bookingsToday: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.admin.getShops().catch(() => ({ data: [] })),
      api.admin.getBookings({ dateFrom: new Date().toISOString().slice(0, 10), dateTo: new Date().toISOString().slice(0, 10) }).catch(() => ({ data: [] }))
    ]).then(([shops, bookings]) => {
      const shopList = shops.data?.data || shops.data || [];
      const bookingList = bookings.data?.data || bookings.data || [];
      setStats({
        shops: shopList.length,
        therapists: 0,
        bookingsToday: bookingList.length
      });
      setLoading(false);
    });
  }, []);

  const cards = [
    { label: 'Shops', value: stats.shops, onClick: () => router.push('/admin/shops') },
    { label: "Today's Bookings", value: stats.bookingsToday, onClick: () => router.push('/admin/bookings') },
    { label: 'Therapists', value: stats.therapists, onClick: () => router.push('/admin/therapists') },
  ];

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Admin Dashboard</h1>
        <p className="text-gray-600 mb-8">Welcome to the management console.</p>
        <div className="grid md:grid-cols-3 gap-4">
          {cards.map(c => (
            <button
              key={c.label}
              onClick={c.onClick}
              className="bg-white rounded-xl shadow border border-gray-200 p-6 text-left hover:shadow-lg transition"
            >
              <div className="text-sm text-gray-500">{c.label}</div>
              <div className="text-4xl font-bold text-[#031050] mt-2">{loading ? '—' : c.value}</div>
            </button>
          ))}
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
