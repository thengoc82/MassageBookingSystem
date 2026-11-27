import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import BookingEditForm from './BookingEditForm';
import { api } from '@/lib/api';
import type { Booking } from '@/types';

jest.mock('@/lib/api', () => ({
  api: {
    shops: { getCourses: jest.fn(), getAvailableSlots: jest.fn() },
    bookings: { update: jest.fn() },
  },
}));

const booking: Booking = {
  bookingId: 42, bookingCode: 'BK209912100001', shopId: 7, shopName: 'Test Spa',
  phoneNumber: '0901234567', bookingDate: '2099-12-10', startTime: '10:00', endTime: '11:00',
  numberOfPeople: 1, status: 'Booked', therapistId: 3, therapistName: 'Anna',
  services: [{ personIndex: 1, courseId: 1, courseName: 'Full Body' }], addOns: [],
  preferences: { notes: 'Keep this request', selectedCourses: [{ courseId: 1, duration: 60, price: 6000 }] },
};

const courses = [
  { courseId: 1, courseName: 'Full Body', courseType: 'main', durations: [{ duration: 60, price: 6000 }] },
  { courseId: 2, courseName: 'Head Spa', courseType: 'addon', durations: [{ duration: 30, price: 3000 }] },
];

const callbacks = () => ({
  onSaved: jest.fn().mockResolvedValue(undefined),
  onStatusChanged: jest.fn().mockResolvedValue(undefined),
  onAccessExpired: jest.fn(), onClose: jest.fn(),
});

beforeEach(() => {
  jest.clearAllMocks();
  (api.shops.getAvailableSlots as jest.Mock).mockResolvedValue({ data: [], therapists: [{ therapistId: 3, name: 'Anna', gender: 'Female' }] });
  (api.shops.getCourses as jest.Mock).mockResolvedValue({ data: courses });
  (api.bookings.update as jest.Mock).mockResolvedValue({ success: true });
});

test('reschedules with a partial customer PATCH and preserves saved fields', async () => {
  const actions = callbacks();
  render(<BookingEditForm booking={booking} {...actions} />);
  expect(screen.getByText('Keep this request')).toBeInTheDocument();
  expect(screen.getByText('0901234567')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Start time'), { target: { value: '11:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
  await waitFor(() => expect(api.bookings.update).toHaveBeenCalledWith(42, { startTime: '11:00' }, true));
  expect(api.shops.getCourses).not.toHaveBeenCalled();
  await waitFor(() => expect(actions.onSaved).toHaveBeenCalled());
});

test('course edit retains saved option and submits complete valid selection', async () => {
  render(<BookingEditForm booking={booking} {...callbacks()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Change courses and duration' }));
  await screen.findByText('Head Spa');
  expect(screen.getByRole('button', { name: '60 min · 6,000 VND' })).toHaveAttribute('aria-pressed', 'true');
  fireEvent.click(screen.getByRole('button', { name: '30 min · 3,000 VND' }));
  expect(screen.getByText('Selected total: 90 minutes per guest')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
  await waitFor(() => expect(api.bookings.update).toHaveBeenCalledWith(42, {
    duration: 90,
    services: [{ personIndex: 1, courseId: 1 }],
    addOns: [{ personIndex: 1, courseId: 2 }],
    selectedCourses: [{ courseId: 1, duration: 60, price: 6000 }, { courseId: 2, duration: 30, price: 3000 }],
  }, true));
});

test('legacy booking without a saved price requires an explicit course option', async () => {
  render(<BookingEditForm booking={{ ...booking, preferences: { notes: 'Keep this request' } }} {...callbacks()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Change courses and duration' }));
  await screen.findByText('Full Body');
  expect(screen.getByRole('button', { name: '60 min · 6,000 VND' })).toHaveAttribute('aria-pressed', 'false');
  expect(screen.getByText(/could not be preselected/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
  expect(api.bookings.update).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: '60 min · 6,000 VND' }));
  fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
  await waitFor(() => expect(api.bookings.update).toHaveBeenCalledWith(42, expect.objectContaining({ duration: 60 }), true));
});

test('refreshes status after backend rejects a late edit', async () => {
  (api.bookings.update as jest.Mock).mockRejectedValueOnce({ status: 422, code: 'INVALID_MODIFY_STATUS' });
  const actions = callbacks();
  render(<BookingEditForm booking={booking} {...actions} />);
  fireEvent.change(screen.getByLabelText('Start time'), { target: { value: '11:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
  await waitFor(() => expect(actions.onStatusChanged).toHaveBeenCalled());
  expect(actions.onSaved).not.toHaveBeenCalled();
});

test('unavailable time keeps the entered edit for another attempt', async () => {
  (api.bookings.update as jest.Mock).mockRejectedValueOnce({ status: 422, code: 'SLOT_UNAVAILABLE' });
  render(<BookingEditForm booking={booking} {...callbacks()} />);
  fireEvent.change(screen.getByLabelText('Start time'), { target: { value: '11:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
  expect(await screen.findByText(/no longer available/)).toBeInTheDocument();
  expect(screen.getByLabelText('Start time')).toHaveValue('11:00');
});
