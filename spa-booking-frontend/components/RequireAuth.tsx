'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface UserInfo {
  id: number;
  username: string;
  role: string;
  type: string;
}

export default function RequireAuth({ allowedRoles, children }: { allowedRoles: string[]; children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [checked, setChecked] = useState(false);
  const [forbidden, setForbidden] = useState(false);

  useEffect(() => {
    const raw = localStorage.getItem('user');
    const token = localStorage.getItem('access_token');

    if (!token || !raw) {
      router.replace('/login');
      return;
    }

    try {
      const parsed: UserInfo = JSON.parse(raw);
      if (!allowedRoles.includes(parsed.role)) {
        setForbidden(true);
        setChecked(true);
        return;
      }
      setUser(parsed);
      setChecked(true);
    } catch {
      router.replace('/login');
    }
  }, [allowedRoles, router]);

  if (!checked) {
    return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading...</div>;
  }

  if (forbidden) {
    return (
      <div className="min-h-[80vh] flex flex-col items-center justify-center bg-gray-50 px-4">
        <div className="text-6xl mb-4">🚫</div>
        <h1 className="text-3xl font-bold text-gray-900">403 Forbidden</h1>
        <p className="text-gray-600 mt-2">You do not have permission to access this page.</p>
        <button
          onClick={() => router.push(user?.role === 'admin' ? '/admin' : '/therapist')}
          className="mt-6 bg-[#1F2B2A] text-white px-5 py-2.5 rounded-lg hover:bg-[#1a2a6b]"
        >
          Back to my dashboard
        </button>
      </div>
    );
  }

  return <>{children}</>;
}
