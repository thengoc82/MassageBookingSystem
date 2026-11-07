'use client';

import { CalendarDays, Columns3, Store, UsersRound, Tags, Clock, UserRound } from 'lucide-react';
import SidebarNav from './SidebarNav';

const links = [
  { href: '/admin', label: 'Schedule', icon: CalendarDays },
  { href: '/admin/bookings', label: 'Bookings', icon: Columns3 },
  { href: '/admin/shops', label: 'Shops', icon: Store },
  { href: '/admin/therapists', label: 'Therapists', icon: UsersRound },
  { href: '/admin/courses', label: 'Courses', icon: Tags },
  { href: '/admin/schedules', label: 'Therapist schedules', icon: Clock },
  { href: '/admin/customers', label: 'Customers', icon: UserRound },
];

export default function AdminSidebar() {
  return <SidebarNav links={links} label="Admin" />;
}
