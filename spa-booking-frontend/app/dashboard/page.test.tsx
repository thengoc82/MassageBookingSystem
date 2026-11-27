import { render, screen } from '@testing-library/react';
import DashboardPage from './page';
import { api } from '@/lib/api';

jest.mock('next/navigation', () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock('@/components/TherapistGantt', () => function MockGantt({ shopId, duration }: { shopId: number; duration: number }) {
  return <div data-testid="gantt">{shopId}: {duration}</div>;
});
jest.mock('@/lib/api', () => ({ api: { shops: { getAll: jest.fn(), getCourses: jest.fn() } } }));

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
