'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function AuthNav() {
  const { user, logout, isLoading } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  if (isLoading) {
    return <div className="h-8 w-24 rounded bg-gray-700 animate-pulse"></div>;
  }

  return (
    <div className="flex items-center gap-6">
      {user ? (
        <>
          {user.role === 'admin' && (
            <Link href="/admin" className="text-white/80 hover:text-white">Admin</Link>
          )}
          {user.role === 'therapist' && (
            <Link href="/therapist" className="text-white/80 hover:text-white">Therapist</Link>
          )}
          {user.role === 'customer' && (
            <>
              <Link href="/dashboard" className="text-white/80 hover:text-white">Book</Link>
              <Link href="/my-bookings" className="text-white/80 hover:text-white">My Bookings</Link>
            </>
          )}
          <div className="flex items-center gap-3">
            <span className="text-white/80 text-sm hidden sm:inline">
              {user.name}
              <span className="text-white/40 ml-1">({user.role})</span>
            </span>
            <button
              onClick={handleLogout}
              className="text-white/80 hover:text-white text-sm border border-white/20 rounded px-3 py-1"
            >
              Logout
            </button>
          </div>
        </>
      ) : (
        <>
          <Link href="/dashboard" className="text-white/80 hover:text-white">Book</Link>
          <Link href="/my-bookings" className="text-white/80 hover:text-white">My Bookings</Link>
          <Link
            href="/login"
            className="text-white/80 hover:text-white text-sm border border-white/20 rounded px-3 py-1"
          >
            Login
          </Link>
        </>
      )}
    </div>
  );
}
