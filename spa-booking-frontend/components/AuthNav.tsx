'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

interface UserInfo {
  id: number;
  username: string;
  role: string;
  type: string;
}

export default function AuthNav() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    if (!mounted) return;
    const raw = localStorage.getItem('user');
    if (raw) {
      try { setUser(JSON.parse(raw)); } catch { setUser(null); }
    }
  }, [mounted]);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
    router.push('/');
  };

  return (
    <div className="flex items-center gap-3">
      {user ? (
        <>
          <span className="text-white/80 text-sm hidden sm:inline">
            {user.username}
            <span className="text-white/40 ml-1">({user.type})</span>
          </span>
          <button
            onClick={handleLogout}
            className="text-white/80 hover:text-white text-sm border border-white/20 rounded px-3 py-1"
          >
            Logout
          </button>
        </>
      ) : (
        <Link
          href="/login"
          className="text-white/80 hover:text-white text-sm border border-white/20 rounded px-3 py-1"
        >
          Login
        </Link>
      )}
    </div>
  );
}
