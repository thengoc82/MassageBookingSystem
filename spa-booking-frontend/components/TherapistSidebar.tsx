'use client';

import { CalendarDays, Clock, Columns3, UserRound } from 'lucide-react';
import SidebarNav from './SidebarNav';

const links = [
  { href: '/therapist', label: 'Today', icon: CalendarDays },
  { href: '/therapist/schedule', label: 'Schedule', icon: Clock },
  { href: '/therapist/bookings', label: 'My bookings', icon: Columns3 },
  { href: '/therapist/profile', label: 'Profile', icon: UserRound },
];

export default function TherapistSidebar() {
  return <SidebarNav links={links} label="Therapist" />;
}
