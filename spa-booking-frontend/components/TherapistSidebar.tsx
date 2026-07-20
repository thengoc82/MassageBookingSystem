'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { href: '/therapist', label: 'Dashboard' },
  { href: '/therapist/schedule', label: 'Schedule' },
  { href: '/therapist/bookings', label: 'My Bookings' },
  { href: '/therapist/profile', label: 'Profile' },
];

export default function TherapistSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 shrink-0 bg-[#031050] text-white min-h-[calc(100vh-65px)] p-4">
      <nav className="flex flex-col gap-1">
        {links.map(link => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`px-3 py-2 rounded-lg text-sm transition ${
                active ? 'bg-white/20 font-semibold' : 'hover:bg-white/10'
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
