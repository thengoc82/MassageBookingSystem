'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { LucideIcon } from 'lucide-react';

export interface SidebarLink {
  href: string;
  label: string;
  icon: LucideIcon;
}

export default function SidebarNav({ links, label }: { links: SidebarLink[]; label: string }) {
  const pathname = usePathname();

  return (
    <aside className="w-60 shrink-0 bg-basalt text-white min-h-[calc(100vh-57px)] px-3 py-5">
      <nav aria-label={label} className="flex flex-col gap-0.5">
        {links.map(({ href, label: text, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? 'page' : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                active ? 'bg-basalt-2 text-white' : 'text-[#C9D6D3] hover:bg-basalt-2 hover:text-white'
              }`}
            >
              <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
              {text}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
