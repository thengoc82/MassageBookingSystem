import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import Page from './page';
import { api } from '@/lib/api';

jest.mock('@/components/RequireAuth', () => ({ __esModule: true, default: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
jest.mock('@/components/AdminSidebar', () => ({ __esModule: true, default: () => <div>Sidebar</div> }));
jest.mock('@/lib/api', () => ({ api: { admin: {
  getShops: jest.fn(), getTherapists: jest.fn(), getTherapistShifts: jest.fn(),
  getTherapistSchedule: jest.fn(), createTherapistShift: jest.fn(),
  updateTherapistShift: jest.fn(), deleteTherapistShift: jest.fn(),
} } }));

const existing = { shiftId: 8, therapistId: 4, dayOfWeek: 'Monday', startTime: '09:00', endTime: '17:00', effectiveFrom: '2026-12-01' };

beforeEach(() => {
  jest.clearAllMocks();
  (api.admin.getShops as jest.Mock).mockResolvedValue({ data: [{ shopId: 2, shopName: 'Test Spa' }] });
  (api.admin.getTherapists as jest.Mock).mockResolvedValue({ data: [{ therapistId: 4, name: 'Anna' }] });
  (api.admin.getTherapistShifts as jest.Mock).mockResolvedValue({ data: [existing] });
  (api.admin.getTherapistSchedule as jest.Mock).mockResolvedValue({ data: { schedule: [{ bookingId: 10, date: '2026-12-07', startTime: '10:00', endTime: '11:00', bookingCode: 'BK123', customerPhone: '0901234567', status: 'Booked' }] } });
  (api.admin.createTherapistShift as jest.Mock).mockResolvedValue({ data: { shiftId: 9 } });
  (api.admin.updateTherapistShift as jest.Mock).mockResolvedValue({ data: { ...existing, endTime: '18:00' } });
  (api.admin.deleteTherapistShift as jest.Mock).mockResolvedValue({ data: { shiftId: 8 } });
});

test('shows weekly shifts alongside the existing booking schedule and creates a shift', async () => {
  render(<Page />);
  const weekly = screen.getByRole('region', { name: 'Weekly shifts' });
  expect(await within(weekly).findByText(/09:00–17:00/)).toBeInTheDocument();
  expect(api.admin.getTherapistShifts).toHaveBeenCalledWith(2, { therapistId: 4 });
  fireEvent.click(screen.getByRole('button', { name: 'View Schedule' }));
  expect(await within(screen.getByRole('region', { name: 'Bookings' })).findByText(/BK123/)).toBeInTheDocument();
  expect(api.admin.getTherapistSchedule).toHaveBeenCalledWith(4, expect.any(String), expect.any(String));
  fireEvent.change(screen.getByLabelText('Shift end'), { target: { value: '18:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Add shift' }));
  await waitFor(() => expect(api.admin.createTherapistShift).toHaveBeenCalledWith(expect.objectContaining({
    therapistId: 4, dayOfWeek: 'Monday', startTime: '09:00', endTime: '18:00',
  })));
  expect(api.admin.getTherapistShifts).toHaveBeenCalledTimes(2);
  expect(within(screen.getByRole('region', { name: 'Bookings' })).getByText(/BK123/)).toBeInTheDocument();
});

test('edits a shift and shows a booking conflict without deleting it', async () => {
  render(<Page />);
  const weekly = screen.getByRole('region', { name: 'Weekly shifts' });
  await within(weekly).findByText(/09:00–17:00/);
  fireEvent.click(within(weekly).getByRole('button', { name: 'Edit' }));
  expect(screen.getByLabelText('Shift start')).toHaveValue('09:00');
  fireEvent.change(screen.getByLabelText('Shift end'), { target: { value: '18:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save shift' }));
  await waitFor(() => expect(api.admin.updateTherapistShift).toHaveBeenCalledWith(8, expect.objectContaining({ endTime: '18:00' })));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Add shift' })).toBeInTheDocument());
  jest.spyOn(window, 'confirm').mockReturnValue(true);
  (api.admin.deleteTherapistShift as jest.Mock).mockRejectedValueOnce(new Error('Shift change would leave an existing booking uncovered'));
  fireEvent.click(within(weekly).getByRole('button', { name: 'Delete' }));
  expect(await within(weekly).findByRole('alert')).toHaveTextContent('existing booking uncovered');
  expect(within(weekly).getByText(/09:00–17:00/)).toBeInTheDocument();
  expect(api.admin.deleteTherapistShift).toHaveBeenCalledWith(8);
  (window.confirm as jest.Mock).mockRestore();
});

test('deletes a shift and refreshes the weekly list', async () => {
  render(<Page />);
  const weekly = screen.getByRole('region', { name: 'Weekly shifts' });
  await within(weekly).findByText(/09:00–17:00/);
  jest.spyOn(window, 'confirm').mockReturnValue(true);
  (api.admin.getTherapistShifts as jest.Mock).mockResolvedValueOnce({ data: [] });
  fireEvent.click(within(weekly).getByRole('button', { name: 'Delete' }));
  await waitFor(() => expect(api.admin.deleteTherapistShift).toHaveBeenCalledWith(8));
  expect(await within(weekly).findByText('No weekly shifts.')).toBeInTheDocument();
  (window.confirm as jest.Mock).mockRestore();
});
