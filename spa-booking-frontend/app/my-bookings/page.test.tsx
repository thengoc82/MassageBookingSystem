import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import MyBookingsPage from './page';
import { api } from '@/lib/api';

const push = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ push }) }));
jest.mock('@/lib/api', () => ({
  api: { bookings: { getAll: jest.fn(), cancel: jest.fn(), requestAccessCode: jest.fn(), verifyAccessCode: jest.fn() } },
  getCustomerBookingAccess: () => ({ phone: '0901234567', token: 'verified-token' }),
  clearCustomerBookingAccess: jest.fn(),
  saveCustomerBookingAccess: jest.fn(),
}));

const row = {
  bookingId: 42, bookingCode: 'BK209912100001', shopName: 'Test Spa',
  bookingDate: '2099-12-10', startTime: '10:00', numberOfPeople: 1, status: 'Booked',
};
const listing = (status: string) => ({
  success: true,
  data: { data: [{ ...row, status }], pagination: { page: 1, totalPages: 1, total: 1 } },
});

beforeEach(() => {
  jest.clearAllMocks();
  global.confirm = jest.fn().mockReturnValue(true);
  (api.bookings.getAll as jest.Mock).mockResolvedValue(listing('Booked'));
  (api.bookings.cancel as jest.Mock).mockResolvedValue({ success: true });
});

test('verified customer can open the booking editor from the list', async () => {
  render(<MyBookingsPage />);
  fireEvent.click(await screen.findByRole('button', { name: 'Edit booking' }));
  expect(push).toHaveBeenCalledWith('/bookings/42?customer=1&edit=1');
});

test('a late cancellation rejection refreshes status and removes actions', async () => {
  (api.bookings.cancel as jest.Mock).mockRejectedValueOnce({ status: 422, code: 'INVALID_CANCEL_STATUS' });
  (api.bookings.getAll as jest.Mock).mockResolvedValueOnce(listing('Booked')).mockResolvedValueOnce(listing('CheckedIn'));
  render(<MyBookingsPage />);
  fireEvent.click(await screen.findByRole('button', { name: 'Cancel booking' }));
  await waitFor(() => expect(screen.getByText('CheckedIn')).toBeInTheDocument());
  expect(screen.getByText(/can no longer be cancelled/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Edit booking' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Cancel booking' })).not.toBeInTheDocument();
});
