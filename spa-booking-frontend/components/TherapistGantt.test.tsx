import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import TherapistGantt from './TherapistGantt';
import { api } from '@/lib/api';

jest.mock('@/lib/api', () => ({ api: { shops: { getAvailableSlots: jest.fn() } } }));

const props = { shopId: 7, date: '2030-12-10', duration: 60, numberOfPeople: 1 };
const therapists = [
  { therapistId: 9, name: 'Anna', gender: 'Female' },
  { therapistId: 10, name: 'John', gender: 'Male' },
];

beforeEach(() => jest.clearAllMocks());

test('only lets a group select a time with enough capacity', async () => {
  const select = jest.fn();
  (api.shops.getAvailableSlots as jest.Mock).mockResolvedValue({ therapists, data: [
    { startTime: '10:00', endTime: '11:00', availableCapacity: 1, availableTherapistIds: [9] },
    { startTime: '10:15', endTime: '11:15', availableCapacity: 2, availableTherapistIds: [9, 10] },
  ] });
  render(<TherapistGantt {...props} numberOfPeople={2} selectionMode="capacity" onSelectSlot={select} />);
  expect(await screen.findByRole('button', { name: '10:00 unavailable' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Book 10:15' }));
  expect(select).toHaveBeenCalledWith('10:15', 0);
});

test('keeps named-therapist selection tied to the available therapist ID', async () => {
  const select = jest.fn();
  (api.shops.getAvailableSlots as jest.Mock).mockResolvedValue({ therapists, data: [
    { startTime: '10:00', endTime: '11:00', availableCapacity: 1, availableTherapistIds: [9] },
  ] });
  render(<TherapistGantt {...props} selectionMode="therapist" onSelectSlot={select} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Book Anna at 10:00' }));
  expect(screen.getByRole('button', { name: 'John unavailable at 10:00' })).toBeDisabled();
  expect(select).toHaveBeenCalledWith('10:00', 9);
});

test('passes the gender filter and explains empty availability', async () => {
  (api.shops.getAvailableSlots as jest.Mock).mockResolvedValue({ therapists: [therapists[0]], data: [
    { startTime: '10:00', endTime: '11:00', availableCapacity: 0, availableTherapistIds: [] },
  ] });
  render(<TherapistGantt {...props} gender="Female" selectionMode="capacity" />);
  expect(await screen.findByText('No available times match this selection. Choose another date or preference.')).toBeInTheDocument();
  expect(api.shops.getAvailableSlots).toHaveBeenCalledWith(7, expect.objectContaining({ gender: 'Female' }));
});

test('shows API errors and can retry availability', async () => {
  (api.shops.getAvailableSlots as jest.Mock)
    .mockRejectedValueOnce(new Error('Offline'))
    .mockResolvedValueOnce({ therapists, data: [{ startTime: '10:00', endTime: '11:00', availableCapacity: 1, availableTherapistIds: [9] }] });
  render(<TherapistGantt {...props} selectionMode="capacity" />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Offline');
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Book 10:00' })).toBeEnabled());
});
