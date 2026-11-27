'use client';

import { use, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, clearCustomerBookingAccess } from '@/lib/api';
import BookingEditForm from '@/components/booking/BookingEditForm';
import type { Booking, BookingServiceDetail } from '@/types';

function formatTime(t: string) {
  const [h, m] = t.split(':').map(Number);
  const ampm = h >= 12 ? 'PM' : 'AM';
  const hour = h % 12 || 12;
  return `${hour}:${String(m).padStart(2, '0')} ${ampm}`;
}

function getStatusColor(status: string) {
  switch (status) {
    case 'Booked': return 'bg-celadon-soft text-[#1F4A41]';
    case 'CheckedIn': return 'bg-green-100 text-green-800';
    case 'CheckedOut': return 'bg-gray-100 text-gray-800';
    case 'Cancelled': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-800';
  }
}

function DetailRow({ label, value }: { label: string; value: string | string[] | number | null | undefined }) {
  if (!value) return null;
  return (
    <div className="flex gap-4 py-1.5">
      <span className="w-36 shrink-0 text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium text-gray-900">{Array.isArray(value) ? value.join(', ') : value}</span>
    </div>
  );
}

function SectionHeader({ title }: { title: string }) {
  return <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{title}</h3>;
}

export default function BookingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [notice, setNotice] = useState('');
  const customerView = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('customer') === '1';

  async function refresh(customer = customerView) {
    try {
      const response = await api.bookings.getById(Number(id), customer);
      setBooking(response.data || response);
      setError(null);
    } catch (cause) {
      if ((cause as { status?: number })?.status === 401 && customer) {
        clearCustomerBookingAccess();
        setError('Your booking access expired. Verify your phone again to continue.');
      } else {
        setError(cause instanceof Error ? cause.message : 'Failed to load booking');
      }
    }
  }

  useEffect(() => {
    const search = new URLSearchParams(window.location.search);
    const customerView = search.get('customer') === '1';
    let active = true;
    api.bookings.getById(Number(id), customerView)
      .then(response => {
        if (!active) return;
        setBooking(response.data || response);
        setEditing(customerView && search.get('edit') === '1');
      })
      .catch(cause => {
        if (!active) return;
        if ((cause as { status?: number })?.status === 401 && customerView) {
          clearCustomerBookingAccess();
          setError('Your booking access expired. Verify your phone again to continue.');
        } else setError(cause instanceof Error ? cause.message : 'Failed to load booking');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  async function cancelBooking() {
    if (!booking || !confirm('Are you sure you want to cancel this booking?')) return;
    setCancelling(true);
    setNotice('');
    try {
      await api.bookings.cancel(booking.bookingId);
      setEditing(false);
      setNotice('Booking cancelled.');
      await refresh(true);
    } catch (cause) {
      const response = cause as { status?: number; code?: string; message?: string };
      if (response.status === 401) {
        clearCustomerBookingAccess();
        setError('Your booking access expired. Verify your phone again to continue.');
      } else if (response.code === 'INVALID_CANCEL_STATUS') {
        setNotice('This booking can no longer be cancelled. Its current status has been refreshed.');
        await refresh(true);
      } else {
        setNotice(response.message || 'Could not cancel this booking. Please try again.');
      }
    } finally {
      setCancelling(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error || !booking) {
    return (
      <div className="min-h-screen bg-white py-8">
        <div className="container mx-auto px-4 max-w-2xl">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">{error || 'Booking not found'}</div>
          <button onClick={() => customerView ? router.push('/my-bookings') : router.back()} className="mt-4 text-sm text-celadon-deep hover:underline">{customerView ? 'Verify phone or return to My Bookings' : 'Go back'}</button>
        </div>
      </div>
    );
  }

  const prefs = booking.preferences as Record<string, string | string[] | number | undefined> | undefined;
  const services = booking.services as BookingServiceDetail[] | undefined;
  const addons = booking.addOns as BookingServiceDetail[] | undefined;

  return (
    <div className="min-h-screen bg-[#F5F7FA] py-8">
      <div className="container mx-auto px-4 max-w-2xl space-y-4">

        <button onClick={() => customerView ? router.push('/my-bookings') : router.back()} className="text-sm text-celadon-deep hover:underline flex items-center gap-1">
          &larr; Back
        </button>

        {notice && <p role="status" className="rounded-lg bg-celadon-soft p-3 text-sm text-gray-900">{notice}</p>}

        {/* Header */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h1 className="text-xl font-bold text-gray-900">{booking.bookingCode}</h1>
              <p className="text-sm text-gray-500 mt-0.5">{booking.shopName}</p>
            </div>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(booking.status)}`}>
              {booking.status}
            </span>
          </div>
          {customerView && booking.status === 'Booked' && <div className="flex gap-3 border-t border-gray-200 pt-4">
            <button type="button" onClick={() => { setEditing(true); setNotice(''); }} className="rounded-lg bg-celadon px-4 py-2 text-sm font-semibold text-white">Edit booking</button>
            <button type="button" onClick={() => void cancelBooking()} disabled={cancelling} className="rounded-lg border border-red-600 px-4 py-2 text-sm font-semibold text-red-700 disabled:opacity-50">{cancelling ? 'Cancelling...' : 'Cancel booking'}</button>
          </div>}
        </div>

        {customerView && editing && booking.status === 'Booked' && <BookingEditForm booking={booking}
          onSaved={async () => { setEditing(false); setNotice('Booking updated.'); await refresh(true); }}
          onStatusChanged={async () => { setEditing(false); setNotice('This booking can no longer be edited. Its current status has been refreshed.'); await refresh(true); }}
          onAccessExpired={() => { clearCustomerBookingAccess(); setEditing(false); setError('Your booking access expired. Verify your phone again to continue.'); }}
          onClose={() => setEditing(false)} />}

        {/* Date & Time */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <SectionHeader title="Date &amp; Time" />
          <DetailRow label="Date" value={booking.bookingDate} />
          <DetailRow label="Time" value={`${formatTime(booking.startTime)} - ${formatTime(booking.endTime)}`} />
          <DetailRow label="Guests" value={booking.numberOfPeople} />
          {booking.therapistAssignments && booking.therapistAssignments.length > 1 ? (
            <div className="flex gap-4 py-1.5">
              <span className="w-36 shrink-0 text-sm text-gray-500">Therapists</span>
              <div className="text-sm font-medium text-gray-900 space-y-0.5">
                {booking.therapistAssignments
                  .slice().sort((a, b) => a.personIndex - b.personIndex)
                  .map(ta => (
                    <div key={ta.therapistId}>
                      Person {ta.personIndex}: {ta.therapistName}
                    </div>
                  ))}
              </div>
            </div>
          ) : (
            <DetailRow label="Therapist" value={booking.therapistName} />
          )}
        </div>

        {/* Services */}
        {services && services.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <SectionHeader title="Services" />
            <div className="space-y-1.5">
              {services.map((s, i) => (
                <div key={i} className="flex justify-between text-sm">
                  <span className="text-gray-700">{s.courseName || `Service #${s.courseId}`}</span>
                  <span className="text-gray-400 text-xs">Person {s.personIndex}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Addons */}
        {addons && addons.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <SectionHeader title="Add-ons" />
            <div className="space-y-1.5">
              {addons.map((a, i) => (
                <div key={i} className="flex justify-between text-sm">
                  <span className="text-gray-700">{a.courseName || `Addon #${a.courseId}`}</span>
                  <span className="text-gray-400 text-xs">Person {a.personIndex}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Preferences */}
        {prefs && Object.keys(prefs).length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <SectionHeader title="Preferences" />

            {prefs.customerName && <DetailRow label="Customer" value={prefs.customerName} />}
            {prefs.customerEmail && <DetailRow label="Email" value={prefs.customerEmail} />}

            {prefs.bodyMassageDuration && (
              <DetailRow label="Body Massage" value={`${prefs.bodyMassageDuration} min`} />
            )}

            {prefs.selectedAddons && Array.isArray(prefs.selectedAddons) && prefs.selectedAddons.length > 0 && (
              <DetailRow label="Add-ons" value={prefs.selectedAddons.join(', ')} />
            )}

            {prefs.optionalExtras && Array.isArray(prefs.optionalExtras) && prefs.optionalExtras.length > 0 && (
              <DetailRow label="Extras" value={prefs.optionalExtras.join(', ')} />
            )}

            {prefs.extraOptions && Array.isArray(prefs.extraOptions) && prefs.extraOptions.length > 0 && (
              <DetailRow label="Extras" value={prefs.extraOptions.join(', ')} />
            )}

            {prefs.massageStrength && <DetailRow label="Strength" value={prefs.massageStrength} />}

            {prefs.conversationPreference && <DetailRow label="Conversation" value={prefs.conversationPreference} />}
            {prefs.chatPref && !prefs.conversationPreference && <DetailRow label="Conversation" value={prefs.chatPref} />}

            {prefs.focusAreas && Array.isArray(prefs.focusAreas) && prefs.focusAreas.length > 0 && (
              <DetailRow label="Focus Areas" value={prefs.focusAreas.join(', ')} />
            )}

            {prefs.avoidAreas && Array.isArray(prefs.avoidAreas) && prefs.avoidAreas.length > 0 && (
              <DetailRow label="Avoid Areas" value={prefs.avoidAreas.join(', ')} />
            )}

            {prefs.notes && <DetailRow label="Notes" value={prefs.notes} />}
          </div>
        )}

      </div>
    </div>
  );
}
