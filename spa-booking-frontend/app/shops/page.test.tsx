import { render, screen } from '@testing-library/react';
import ShopsPage from './page';
import { api } from '@/lib/api';

jest.mock('@/lib/api', () => ({ api: { shops: { getAll: jest.fn(), getCourses: jest.fn() } } }));

test('shows the public catalog and routes booking through the selected shop schedule', async () => {
  (api.shops.getAll as jest.Mock).mockResolvedValue({ success: true, data: [{
    shopId: 7, shopName: 'Test Spa', address: 'Main Street', phoneNumber: '0901234567',
    status: 'Open', openTime: '09:00', closeTime: '21:00',
  }] });
  (api.shops.getCourses as jest.Mock).mockResolvedValue({ data: [
    { courseId: 1, courseName: 'Main Massage', courseType: 'main', durations: [{ duration: 30, price: 3000 }] },
    { courseId: 2, courseName: 'Head Extra', courseType: 'addon', durations: [{ duration: 15, price: 500 }] },
    { courseId: 3, courseName: 'Invalid Extra', courseType: 'addon', durations: [{ duration: 0, price: 500 }] },
  ] });
  render(<ShopsPage />);
  expect(await screen.findByText('Main Massage')).toBeInTheDocument();
  expect(screen.getByText('Head Extra')).toBeInTheDocument();
  expect(screen.queryByText('Invalid Extra')).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Choose a time' })).toHaveAttribute('href', '/dashboard?shopId=7');
});
