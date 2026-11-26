'use client';

import { useCallback, useEffect, useState } from 'react';
import RequireAuth from '@/components/RequireAuth';
import AdminSidebar from '@/components/AdminSidebar';
import { api } from '@/lib/api';

type Customer = { customerId: number; phoneNumber: string; memberRank: string; visitCount: number; isBlocked: boolean };
type Restriction = {
  restrictionId: number; phoneNumber: string; reason: string; blockedAt: string | null;
  blockedBy: string; isActive: boolean;
};
type Pagination = { page: number; size: number; total: number; totalPages: number };

function AdminCustomers() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [restrictions, setRestrictions] = useState<Restriction[]>([]);
  const [pagination, setPagination] = useState<Pagination>({ page: 1, size: 20, total: 0, totalPages: 0 });
  const [status, setStatus] = useState<'active' | 'inactive'>('active');
  const [phoneSearch, setPhoneSearch] = useState('');
  const [appliedPhone, setAppliedPhone] = useState('');
  const [page, setPage] = useState(1);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [reason, setReason] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editReason, setEditReason] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const [customerResult, restrictionResult] = await Promise.all([
      api.admin.getCustomers(),
      api.admin.getCustomerRestrictions({ phone: appliedPhone, status, page, size: 20 }),
    ]);
    setCustomers(customerResult.data || []);
    setRestrictions(restrictionResult.data || []);
    setPagination(restrictionResult.pagination);
  }, [appliedPhone, status, page]);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.admin.getCustomers(),
      api.admin.getCustomerRestrictions({ phone: appliedPhone, status, page, size: 20 }),
    ]).then(([customerResult, restrictionResult]) => {
      if (!active) return;
      setCustomers(customerResult.data || []);
      setRestrictions(restrictionResult.data || []);
      setPagination(restrictionResult.pagination);
    }).catch((failure: Error) => {
      if (active) setError(failure.message);
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [appliedPhone, status, page]);

  const addRestriction = async (event: React.FormEvent) => {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setError('');
    try {
      await api.admin.createCustomerRestriction({ phoneNumber: phoneNumber.trim(), reason: reason.trim() });
      setPhoneNumber('');
      setReason('');
      setPhoneSearch('');
      setAppliedPhone('');
      setStatus('active');
      setPage(1);
      if (appliedPhone === '' && status === 'active' && page === 1) await load();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Could not block customer');
    } finally { setSaving(false); }
  };

  const saveReason = async (event: React.FormEvent) => {
    event.preventDefault();
    if (editingId === null || saving) return;
    setSaving(true);
    setError('');
    try {
      await api.admin.updateCustomerRestriction(editingId, { reason: editReason.trim() });
      setEditingId(null);
      await load();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Could not update reason');
    } finally { setSaving(false); }
  };

  const removeRestriction = async (restriction: Restriction) => {
    if (saving || !window.confirm(`Remove ${restriction.phoneNumber} from the NG List?`)) return;
    setSaving(true);
    setError('');
    try {
      await api.admin.deleteCustomerRestriction(restriction.restrictionId);
      await load();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Could not remove restriction');
    } finally { setSaving(false); }
  };

  return (
    <div className="flex">
      <AdminSidebar />
      <main className="flex-1 p-8 space-y-8">
        <h1 className="text-3xl font-bold text-gray-900">Customers and NG List</h1>
        {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">{error}</div>}

        <section aria-label="Add NG List entry" className="bg-white rounded-xl shadow border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Block a customer</h2>
          <form onSubmit={addRestriction} className="grid gap-4 md:grid-cols-[minmax(12rem,1fr)_minmax(16rem,2fr)_auto] items-end">
            <label className="text-sm text-gray-700">Customer phone
              <input className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2" value={phoneNumber} onChange={e => setPhoneNumber(e.target.value)} required />
            </label>
            <label className="text-sm text-gray-700">Reason
              <input className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2" value={reason} onChange={e => setReason(e.target.value)} required />
            </label>
            <button type="submit" disabled={saving} className="rounded-lg bg-[#1F2B2A] px-5 py-2 text-white disabled:opacity-50">Add to NG List</button>
          </form>
          <p className="mt-2 text-sm text-gray-500">The customer must already exist.</p>
        </section>

        <section aria-label="NG List entries" className="bg-white rounded-xl shadow border border-gray-200 p-6">
          <div className="flex flex-wrap items-end justify-between gap-4 mb-5">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">NG List entries</h2>
              <p className="text-sm text-gray-500">Active entries prevent new bookings. Removed entries remain in history.</p>
            </div>
            <form onSubmit={event => { event.preventDefault(); setPage(1); setAppliedPhone(phoneSearch.trim()); if (appliedPhone === phoneSearch.trim() && page === 1) void load().catch((failure: Error) => setError(failure.message)); }} className="flex gap-2 items-end">
              <label className="text-sm text-gray-700">Search phone
                <input className="mt-1 block rounded-lg border border-gray-300 px-3 py-2" value={phoneSearch} onChange={e => setPhoneSearch(e.target.value)} />
              </label>
              <button type="submit" className="rounded-lg border border-gray-300 px-4 py-2">Search</button>
            </form>
          </div>
          <div className="flex gap-2 mb-4" role="group" aria-label="Restriction status">
            <button type="button" aria-pressed={status === 'active'} onClick={() => { setStatus('active'); setPage(1); }} className={`rounded-lg px-4 py-2 ${status === 'active' ? 'bg-[#1F2B2A] text-white' : 'bg-gray-100 text-gray-700'}`}>Active</button>
            <button type="button" aria-pressed={status === 'inactive'} onClick={() => { setStatus('inactive'); setPage(1); }} className={`rounded-lg px-4 py-2 ${status === 'inactive' ? 'bg-[#1F2B2A] text-white' : 'bg-gray-100 text-gray-700'}`}>History</button>
          </div>
          {loading ? <p className="text-gray-500">Loading...</p> : restrictions.length === 0 ?
            <p className="text-gray-500">No {status} NG List entries.</p> :
            <div className="space-y-3">
              {restrictions.map(item => <div key={item.restrictionId} className="rounded-lg border border-gray-200 p-4">
                <div className="flex flex-wrap justify-between gap-3">
                  <div>
                    <div className="font-semibold text-gray-900">{item.phoneNumber}</div>
                    <div className="text-sm text-gray-700 mt-1">{item.reason}</div>
                    <div className="text-xs text-gray-500 mt-2">By {item.blockedBy} · {item.blockedAt ? new Date(item.blockedAt).toLocaleString() : 'Date unavailable'}</div>
                  </div>
                  <div className="flex gap-2 items-start">
                    <button type="button" onClick={() => { setEditingId(item.restrictionId); setEditReason(item.reason); }} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm">Edit reason</button>
                    {item.isActive && <button type="button" onClick={() => removeRestriction(item)} disabled={saving} className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-700 disabled:opacity-50">Remove</button>}
                  </div>
                </div>
                {editingId === item.restrictionId && <form onSubmit={saveReason} className="flex gap-2 mt-4">
                  <label className="flex-1 text-sm text-gray-700">Updated reason
                    <input className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2" value={editReason} onChange={e => setEditReason(e.target.value)} required />
                  </label>
                  <button type="submit" disabled={saving} className="self-end rounded-lg bg-[#1F2B2A] px-4 py-2 text-white disabled:opacity-50">Save</button>
                  <button type="button" onClick={() => setEditingId(null)} className="self-end rounded-lg border border-gray-300 px-4 py-2">Cancel</button>
                </form>}
              </div>)}
            </div>}
          <div className="flex items-center justify-between mt-5 text-sm text-gray-600">
            <span>{pagination.total} entries · Page {pagination.page} of {Math.max(1, pagination.totalPages)}</span>
            <div className="flex gap-2">
              <button type="button" disabled={page <= 1} onClick={() => { setLoading(true); setPage(page - 1); }} className="rounded border px-3 py-1 disabled:opacity-40">Previous</button>
              <button type="button" disabled={page >= pagination.totalPages} onClick={() => { setLoading(true); setPage(page + 1); }} className="rounded border px-3 py-1 disabled:opacity-40">Next</button>
            </div>
          </div>
        </section>

        <section aria-label="Customers">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Customers</h2>
          <div className="space-y-3">
            {customers.map(customer => <div key={customer.customerId} className="bg-white rounded-lg shadow border border-gray-200 p-4 flex justify-between items-center">
              <div>
                <div className="font-semibold text-gray-900">{customer.phoneNumber}</div>
                <div className="text-xs text-gray-500">Rank: {customer.memberRank} · Visits: {customer.visitCount}</div>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs ${customer.isBlocked ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                {customer.isBlocked ? 'Blocked' : 'Active'}
              </span>
            </div>)}
          </div>
        </section>
      </main>
    </div>
  );
}

export default function Page() {
  return <RequireAuth allowedRoles={['admin']}><AdminCustomers /></RequireAuth>;
}
