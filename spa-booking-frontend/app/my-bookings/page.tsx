'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import type { Booking } from '@/types';

export default function MyBookingsPage() {
  const router = useRouter();
  const [phoneNumber, setPhoneNumber] = useState('');
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  const handleSearch = async (targetPage = 1) => {
    if (!phoneNumber) return;

    try {
      setLoading(true);
      setPage(targetPage);
      const response = await api.bookings.getAll({ phone: phoneNumber, page: targetPage, size: 10 });

      if (response.success) {
        const pagination = response.data.pagination;
        setBookings(response.data.data || response.data);
        setTotalPages(pagination?.totalPages || 1);
        setTotal(pagination?.total || 0);
        setSearched(true);
      }
    } catch (error) {
      console.error('Failed to load bookings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (bookingId: number) => {
    if (!confirm('Are you sure you want to cancel this booking?')) return;

    try {
      const response = await api.bookings.cancel(bookingId);
      if (response.success) {
        handleSearch(page);
      }
    } catch (error) {
      console.error('Failed to cancel booking:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Booked':
        return 'bg-celadon-soft text-[#1F4A41]';
      case 'CheckedIn':
        return 'bg-green-100 text-green-800';
      case 'CheckedOut':
        return 'bg-gray-100 text-gray-800';
      case 'Cancelled':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-white py-8">
      <div className="container mx-auto px-4 max-w-4xl">
        <h1 className="text-4xl font-bold mb-8">My Bookings</h1>

        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <label className="block text-sm text-black font-medium mb-2">Enter Your Phone Number</label>
          <div className="flex gap-2">
            <input
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="0123456789"
              className="flex-1 rounded-lg border-2 border-[#365F91] p-3 text-gray-900 placeholder:text-[#6B7C93]"
            />
            <button
              onClick={() => handleSearch()}
              disabled={!phoneNumber || loading}
              className="bg-celadon text-white px-6 py-3 rounded-lg hover:bg-celadon-deep disabled:bg-gray-300"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </div>

        {searched && bookings.length === 0 && (
          <div className="bg-white rounded-lg shadow-lg p-8 text-center text-gray-600">
            No bookings found for this phone number
          </div>
        )}

        <div className="space-y-4">
          {bookings.map((booking) => (
            <div
              key={booking.bookingId}
              onClick={() => router.push(`/bookings/${booking.bookingId}`)}
              className="bg-white rounded-lg shadow-lg p-6 cursor-pointer hover:shadow-xl transition-shadow"
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">Booking #{booking.bookingCode}</h2>
                  <p className="text-gray-600">{booking.shopName}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm ${getStatusColor(booking.status)}`}>
                  {booking.status}
                </span>
              </div>

              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <div>
                  <div className="flex">
                    <div className="w-24 bg-gray-100 border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 rounded-l-md">
                      Date
                    </div>
                    <div className="flex-1 bg-white border-t border-r border-b border-gray-300 px-3 py-2 text-gray-900 font-medium rounded-r-md">
                      {booking.bookingDate}
                    </div>
                  </div>
                </div>

                <div>
                  <div className="flex">
                    <div className="w-24 bg-gray-100 border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 rounded-l-md">
                      Time
                    </div>
                    <div className="flex-1 bg-white border-t border-r border-b border-gray-300 px-3 py-2 text-gray-900 font-medium rounded-r-md">
                      {booking.startTime}
                    </div>
                  </div>
                </div>

                <div>
                  <div className="flex">
                    <div className="w-24 bg-gray-100 border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 rounded-l-md">
                      Guests
                    </div>
                    <div className="flex-1 bg-white border-t border-r border-b border-gray-300 px-3 py-2 text-gray-900 font-medium rounded-r-md">
                      {booking.numberOfPeople}
                    </div>
                  </div>
                </div>

                {booking.therapistName && (
                  <div>
                    <div className="flex">
                      <div className="w-24 bg-gray-100 border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 rounded-l-md">
                        Therapist
                      </div>
                      <div className="flex-1 bg-white border-t border-r border-b border-gray-300 px-3 py-2 text-gray-900 font-medium rounded-r-md">
                        {booking.therapistName}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {booking.status === 'Booked' && (
                <button
                  onClick={(e) => { e.stopPropagation(); handleCancel(booking.bookingId); }}
                  className="w-full bg-red-600 text-white py-2 rounded-lg hover:bg-red-700"
                >
                  Cancel Booking
                </button>
              )}
            </div>
          ))}
        </div>

        {searched && totalPages > 1 && (
          <div className="flex items-center justify-between pt-4 border-t border-gray-200">
            <span className="text-sm text-gray-500">{total} booking{total !== 1 ? 's' : ''}</span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleSearch(page - 1)}
                disabled={page <= 1 || loading}
                className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
              <button
                onClick={() => handleSearch(page + 1)}
                disabled={page >= totalPages || loading}
                className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
