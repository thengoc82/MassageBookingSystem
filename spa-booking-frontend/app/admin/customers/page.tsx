'use client';

import { useState, useEffect } from 'react';
import RequireAuth from '@/components/RequireAuth';
import AdminSidebar from '@/components/AdminSidebar';
import { api } from '@/lib/api';

function AdminCustomers() {
  const [customers, setCustomers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.admin.getCustomers().then(res => {
      setCustomers(res.data?.data || res.data || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Customers</h1>
        {loading ? <div className="text-gray-400">Loading...</div> : (
          <div className="space-y-3">
            {customers.map((c: any) => (
              <div key={c.customerId || c.id} className="bg-white rounded-lg shadow border border-gray-200 p-4 flex justify-between items-center">
                <div>
                  <div className="font-semibold text-gray-900">{c.phoneNumber}</div>
                  <div className="text-xs text-gray-400">Rank: {c.memberRank} · Visits: {c.visitCount}</div>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs ${c.isBlocked ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                  {c.isBlocked ? 'Blocked' : 'Active'}
                </span>
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
      <AdminCustomers />
    </RequireAuth>
  );
}
