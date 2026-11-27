import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import BookingForm from './BookingForm';
import { api } from '@/lib/api';

jest.mock('@/lib/api', () => ({ api: {
  shops: { getById: jest.fn(), getCourses: jest.fn(), getAvailableSlots: jest.fn() },
  bookings: { create: jest.fn() },
} }));

const context = { shopId: 7, bookingDate: '2026-12-10', startTime: '10:00', duration: 60, numberOfPeople: 2 };
const courses = [
  { courseId: 11, courseName: 'Full Body Massage', courseType: 'main', durations: [{ duration: 30, price: 3000 }, { duration: 60, price: 6000 }] },
  { courseId: 12, courseName: 'Dry Head Spa', courseType: 'main', durations: [{ duration: 30, price: 3000 }] },
  { courseId: 13, courseName: 'Aromatherapy', courseType: 'main', durations: [{ duration: 15, price: 3500 }] },
];

beforeEach(() => {
  jest.clearAllMocks();
  (api.shops.getById as jest.Mock).mockResolvedValue({ data: { shopId: 7, shopName: 'Shinjuku Store', status: 'Open' } });
  (api.shops.getCourses as jest.Mock).mockResolvedValue({ data: courses });
  (api.shops.getAvailableSlots as jest.Mock).mockResolvedValue({ data: [{ startTime: '10:00', endTime: '11:00', availableCapacity: 2 }] });
  (api.bookings.create as jest.Mock).mockResolvedValue({ data: { bookingCode: 'BK123' } });
});

function fillBooking() {
  fireEvent.click(screen.getByRole('button', { name: 'Full Body Massage, 30 minutes, 3,000 VND' }));
  fireEvent.click(screen.getByRole('button', { name: 'Dry Head Spa, 30 minutes, 3,000 VND' }));
  fireEvent.change(screen.getByLabelText(/Phone Number/), { target: { value: '0901234567' } });
}

test('selects multiple courses and requires exact duration and valid phone', async () => {
  render(<BookingForm context={context} />);
  expect(await screen.findByText('Shinjuku Store')).toBeInTheDocument();
  const confirm = screen.getByRole('button', { name: 'Confirm Booking' });
  expect(confirm).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Full Body Massage, 30 minutes, 3,000 VND' }));
  expect(screen.getByText('Select 30 more minutes to match your reserved duration.')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Dry Head Spa, 30 minutes, 3,000 VND' }));
  expect(within(screen.getByRole('region', { name: 'Select Courses' })).getByText('12,000 VND')).toBeInTheDocument();
  expect(confirm).toBeDisabled();
  fireEvent.change(screen.getByLabelText(/Phone Number/), { target: { value: '0901234567' } });
  expect(confirm).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Aromatherapy, 15 minutes, 3,500 VND' }));
  expect(screen.getByText('Remove 15 minutes to match your reserved duration.')).toBeInTheDocument();
  expect(confirm).toBeDisabled();
});

test('revalidates availability and retains a selected therapist for one guest', async () => {
  let resolveBooking!: (value: unknown) => void;
  (api.bookings.create as jest.Mock).mockReturnValue(new Promise(resolve => { resolveBooking = resolve; }));
  (api.shops.getAvailableSlots as jest.Mock).mockResolvedValue({ data: [{ startTime: '10:00', endTime: '11:00', availableCapacity: 2, availableTherapistIds: [9, 10] }] });
  render(<BookingForm context={{ ...context, numberOfPeople: 1, therapistId: 9 }} />);
  await screen.findByText('Shinjuku Store');
  fillBooking();
  fireEvent.change(screen.getByLabelText(/Special Requests/), { target: { value: 'Quiet room' } });
  const confirm = screen.getByRole('button', { name: 'Confirm Booking' });
  fireEvent.click(confirm);
  fireEvent.click(confirm);
  await waitFor(() => expect(api.bookings.create).toHaveBeenCalledTimes(1));
  expect(api.shops.getAvailableSlots).toHaveBeenCalledWith(7, expect.objectContaining({ duration: 60, numberOfPeople: 1, show_therapists: true }));
  expect(api.bookings.create).toHaveBeenCalledWith(expect.objectContaining({
    phoneNumber: '0901234567', duration: 60, notes: 'Quiet room', courseId: 11,
    therapistPreferenceType: 'specific', therapistPreferenceValue: '9',
    services: [{ personIndex: 1, courseId: 11 }, { personIndex: 1, courseId: 12 }],
    selectedCourses: [{ courseId: 11, duration: 30, price: 3000 }, { courseId: 12, duration: 30, price: 3000 }],
  }));
  expect(screen.getByRole('button', { name: 'Confirming...' })).toBeDisabled();
  resolveBooking({ data: { bookingCode: 'BK123' } });
  expect(await screen.findByText('BK123')).toBeInTheDocument();
});

test('sends every selected course for each guest', async () => {
  render(<BookingForm context={context} />);
  await screen.findByText('Shinjuku Store');
  fillBooking();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm Booking' }));
  await waitFor(() => expect(api.bookings.create).toHaveBeenCalledTimes(1));
  expect(api.bookings.create).toHaveBeenCalledWith(expect.objectContaining({
    numberOfPeople: 2,
    services: [{ personIndex: 1, courseId: 11 }, { personIndex: 1, courseId: 12 }, { personIndex: 2, courseId: 11 }, { personIndex: 2, courseId: 12 }],
  }));
});

test('sends add-ons and exact catalog prices for every guest', async () => {
  (api.shops.getCourses as jest.Mock).mockResolvedValue({ data: [
    { courseId: 11, courseName: 'Full Body Massage', courseType: 'main', durations: [{ duration: 30, price: 3000 }, { duration: 30, price: 3500 }] },
    { courseId: 20, courseName: 'Head Add-on', courseType: 'addon', durations: [{ duration: 30, price: 1000 }, { duration: 0, price: 500 }] },
  ] });
  render(<BookingForm context={context} />);
  await screen.findByText('Shinjuku Store');
  fireEvent.click(screen.getByRole('button', { name: 'Full Body Massage, 30 minutes, 3,500 VND' }));
  fireEvent.click(screen.getByRole('button', { name: 'Head Add-on, 30 minutes, 1,000 VND' }));
  fireEvent.change(screen.getByLabelText(/Phone Number/), { target: { value: '0901234567' } });
  expect(screen.queryByRole('button', { name: 'Head Add-on, 0 minutes, 500 VND' })).not.toBeInTheDocument();
  expect(within(screen.getByRole('region', { name: 'Select Courses' })).getByText('9,000 VND')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm Booking' }));
  await waitFor(() => expect(api.bookings.create).toHaveBeenCalledWith(expect.objectContaining({
    services: [{ personIndex: 1, courseId: 11 }, { personIndex: 2, courseId: 11 }],
    addOns: [{ personIndex: 1, courseId: 20 }, { personIndex: 2, courseId: 20 }],
    selectedCourses: [{ courseId: 11, duration: 30, price: 3500 }, { courseId: 20, duration: 30, price: 1000 }],
  })));
});

test('does not submit when the selected slot is gone', async () => {
  (api.shops.getAvailableSlots as jest.Mock).mockResolvedValue({ data: [] });
  render(<BookingForm context={context} />);
  await screen.findByText('Shinjuku Store');
  fillBooking();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm Booking' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('no longer available');
  expect(api.bookings.create).not.toHaveBeenCalled();
});

test('shows a booking API error and lets the customer retry', async () => {
  (api.bookings.create as jest.Mock).mockRejectedValueOnce(new Error('Service temporarily unavailable'));
  render(<BookingForm context={context} />);
  await screen.findByText('Shinjuku Store');
  fillBooking();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm Booking' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Service temporarily unavailable');
  expect(screen.getByRole('button', { name: 'Confirm Booking' })).toBeEnabled();
});

test('shows a blocked booking rejection without a confirmation and can retry after removal', async () => {
  (api.bookings.create as jest.Mock).mockRejectedValueOnce(
    Object.assign(new Error('Customer on NG List'), { code: 'CUSTOMER_BLOCKED' }));
  render(<BookingForm context={context} />);
  await screen.findByText('Shinjuku Store');
  fillBooking();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm Booking' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Customer on NG List');
  expect(screen.queryByText('Booking confirmed')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Confirm Booking' })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm Booking' }));
  expect(await screen.findByText('Booking confirmed')).toBeInTheDocument();
});
