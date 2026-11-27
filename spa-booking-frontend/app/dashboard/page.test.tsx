import { fireEvent, render, screen } from '@testing-library/react';
import DashboardPage from './page';
import { api } from '@/lib/api';
import { localDateStr } from '@/lib/dates';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ push: mockPush }) }));
jest.mock('@/components/TherapistGantt', () => function MockGantt({ shopId, date, duration, gender, selectionMode, onSelectSlot }: {
  shopId: number; date: string; duration: number; gender?: string; selectionMode: string;
  onSelectSlot: (time: string, therapistId: number) => void;
}) {
  return <div data-testid="gantt">{shopId}: {duration}, {date}, {gender || 'any'}, {selectionMode}
    <button onClick={() => onSelectSlot('10:00', selectionMode === 'therapist' ? 9 : 0)}>Choose 10:00</button>
  </div>;
});
jest.mock('@/lib/api', () => ({ api: { shops: { getAll: jest.fn(), getCourses: jest.fn() } } }));

beforeEach(() => jest.clearAllMocks());

test('preselects the linked shop and offers only catalog-backed durations', async () => {
  window.history.pushState({}, '', '/dashboard?shopId=2');
  (api.shops.getAll as jest.Mock).mockResolvedValue({ data: [
    { shopId: 1, shopName: 'First', openTime: '09:00', closeTime: '21:00' },
    { shopId: 2, shopName: 'Second', openTime: '09:00', closeTime: '21:00' },
  ] });
  (api.shops.getCourses as jest.Mock).mockResolvedValue({ data: [
    { courseId: 1, courseName: 'Main', courseType: 'main', durations: [{ duration: 30, price: 100 }] },
    { courseId: 2, courseName: 'Extra', courseType: 'addon', durations: [{ duration: 15, price: 50 }] },
  ] });
  render(<DashboardPage />);
  expect(await screen.findByTestId('gantt')).toHaveTextContent('2: 30');
  expect(screen.getByRole('option', { name: '45 min' })).toBeInTheDocument();
  expect(screen.queryByRole('option', { name: '60 min' })).not.toBeInTheDocument();
});

test('sends the local date and intended preference to the reservation page', async () => {
  window.history.pushState({}, '', '/dashboard');
  (api.shops.getAll as jest.Mock).mockResolvedValue({ data: [
    { shopId: 7, shopName: 'Shop', openTime: '09:00', closeTime: '21:00' },
  ] });
  (api.shops.getCourses as jest.Mock).mockResolvedValue({ data: [
    { courseId: 1, courseName: 'Main', courseType: 'main', durations: [{ duration: 60, price: 100 }] },
  ] });
  render(<DashboardPage />);
  await screen.findByTestId('gantt');
  fireEvent.click(screen.getByRole('button', { name: 'Choose booking date' }));
  fireEvent.click(screen.getByRole('button', { name: String(new Date().getDate()) }));
  expect(screen.getByTestId('gantt')).toHaveTextContent(localDateStr());

  fireEvent.change(screen.getByRole('combobox', { name: 'Therapist preference' }), { target: { value: 'Female' } });
  expect(screen.getByTestId('gantt')).toHaveTextContent('Female, capacity');
  fireEvent.click(screen.getByRole('button', { name: 'Choose 10:00' }));
  expect(mockPush).toHaveBeenLastCalledWith(expect.stringContaining(`date=${localDateStr()}`));
  expect(mockPush).toHaveBeenLastCalledWith(expect.stringContaining('therapistGender=Female'));

  fireEvent.change(screen.getByRole('combobox', { name: 'Therapist preference' }), { target: { value: 'specific' } });
  fireEvent.click(screen.getByRole('button', { name: 'Choose 10:00' }));
  expect(mockPush).toHaveBeenLastCalledWith(expect.stringContaining('therapistId=9'));
  fireEvent.change(screen.getByRole('combobox', { name: 'Guests' }), { target: { value: '2' } });
  fireEvent.click(screen.getByRole('button', { name: 'Choose 10:00' }));
  expect(mockPush.mock.calls.at(-1)?.[0]).not.toContain('therapistId=');
});
