import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Suspense } from 'react';
import BookingDetailPage from './page';
import { api } from '@/lib/api';

const push = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ push, back: jest.fn() }) }));
jest.mock('@/lib/api', () => ({
  api: { bookings: { getById: jest.fn(), cancel: jest.fn() } },
  clearCustomerBookingAccess: jest.fn(),
}));
jest.mock('@/components/booking/BookingEditForm', () => ({
  __esModule: true,
  default: () => <div>Customer edit form</div>,
}));

const booked = {
  bookingId: 42, bookingCode: 'BK209912100001', shopId: 7, shopName: 'Test Spa',
  phoneNumber: '0901234567', bookingDate: '2099-12-10', startTime: '10:00', endTime: '11:00',
  numberOfPeople: 1, status: 'Booked', services: [{ personIndex: 1, courseId: 1, courseName: 'Full Body' }],
};

beforeEach(() => {
  jest.clearAllMocks();
  window.history.pushState({}, '', '/bookings/42?customer=1&edit=1');
  global.confirm = jest.fn().mockReturnValue(true);
  (api.bookings.getById as jest.Mock).mockResolvedValue({ data: booked });
  (api.bookings.cancel as jest.Mock).mockResolvedValue({ success: true });
});

async function renderDetail() {
  await act(async () => {
    render(<Suspense fallback={<div>Loading route...</div>}><BookingDetailPage params={Promise.resolve({ id: '42' })} /></Suspense>);
  });
}

test('customer detail loads with customer token mode and opens the editor', async () => {
  await renderDetail();
  expect(await screen.findByText('Customer edit form')).toBeInTheDocument();
  expect(api.bookings.getById).toHaveBeenCalledWith(42, true);
  expect(screen.getByText('Full Body')).toBeInTheDocument();
});

test('successful cancellation refetches status and hides edit controls', async () => {
  (api.bookings.getById as jest.Mock)
    .mockResolvedValueOnce({ data: booked })
    .mockResolvedValueOnce({ data: { ...booked, status: 'Cancelled' } });
  await renderDetail();
  fireEvent.click(await screen.findByRole('button', { name: 'Cancel booking' }));
  await waitFor(() => expect(screen.getByText('Booking cancelled.')).toBeInTheDocument());
  expect(screen.getByText('Cancelled')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Edit booking' })).not.toBeInTheDocument();
  expect(screen.queryByText('Customer edit form')).not.toBeInTheDocument();
});
