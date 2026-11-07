'use client';

import { useState, useEffect } from 'react';
import RequireAuth from '@/components/RequireAuth';
import TherapistSidebar from '@/components/TherapistSidebar';
import { api } from '@/lib/api';

function TherapistProfile() {
  const [profile, setProfile] = useState<any>(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    api.therapist.getProfile().then(res => {
      setProfile(res.data);
      setPhoneNumber(res.data.phoneNumber || '');
    }).catch((e: any) => setError(e.message));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setMessage('');
    try {
      const payload: any = { phoneNumber };
      if (password) payload.password = password;
      const res = await api.therapist.updateProfile(payload);
      setProfile(res.data);
      setPassword('');
      setMessage('Profile updated');
    } catch (e: any) { setError(e.message); }
  };

  return (
    <div className="flex">
      <TherapistSidebar />
      <main className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">My Profile</h1>

        {profile && (
          <div className="bg-white rounded-xl shadow border border-gray-200 p-6 mb-6">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-gray-500">Name:</span> {profile.name}</div>
              <div><span className="text-gray-500">Gender:</span> {profile.gender}</div>
              <div><span className="text-gray-500">Username:</span> {profile.username}</div>
              <div><span className="text-gray-500">Status:</span> {profile.status}</div>
            </div>
          </div>
        )}

        {error && <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded mb-4 text-sm">{error}</div>}
        {message && <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded mb-4 text-sm">{message}</div>}

        <form onSubmit={handleSave} className="bg-white rounded-xl shadow border border-gray-200 p-6 max-w-md space-y-4">
          <div>
            <label className="text-sm text-gray-600 block mb-1">Phone Number</label>
            <input value={phoneNumber} onChange={e => setPhoneNumber(e.target.value)} className="border rounded-lg px-3 py-2 text-sm w-full" />
          </div>
          <div>
            <label className="text-sm text-gray-600 block mb-1">New Password (leave blank to keep)</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="border rounded-lg px-3 py-2 text-sm w-full" />
          </div>
          <button type="submit" className="bg-[#1F2B2A] text-white py-2.5 rounded-lg hover:bg-[#1a2a6b] w-full">Save</button>
        </form>
      </main>
    </div>
  );
}

export default function Page() {
  return (
    <RequireAuth allowedRoles={['therapist']}>
      <TherapistProfile />
    </RequireAuth>
  );
}
