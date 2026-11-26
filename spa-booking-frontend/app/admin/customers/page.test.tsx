import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import Page from './page';
import { api } from '@/lib/api';

jest.mock('@/components/RequireAuth', () => ({ __esModule: true, default: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
jest.mock('@/components/AdminSidebar', () => ({ __esModule: true, default: () => <div>Sidebar</div> }));
jest.mock('@/lib/api', () => ({ api: { admin: {
  getCustomers: jest.fn(), getCustomerRestrictions: jest.fn(),
  createCustomerRestriction: jest.fn(), updateCustomerRestriction: jest.fn(),
  deleteCustomerRestriction: jest.fn(),
} } }));

const entry = { restrictionId: 7, phoneNumber: '0987654321', reason: 'No show',
  blockedAt: '2026-11-26T10:00:00', blockedBy: 'admin', isActive: true };
const page = { page: 1, size: 20, total: 1, totalPages: 1 };

beforeEach(() => {
  jest.clearAllMocks();
  (api.admin.getCustomers as jest.Mock).mockResolvedValue({ data: [
    { customerId: 1, phoneNumber: '0987654321', memberRank: 'Silver', visitCount: 1, isBlocked: true },
  ] });
  (api.admin.getCustomerRestrictions as jest.Mock).mockResolvedValue({ data: [entry], pagination: page });
  (api.admin.createCustomerRestriction as jest.Mock).mockResolvedValue({ data: entry });
  (api.admin.updateCustomerRestriction as jest.Mock).mockResolvedValue({ data: entry });
  (api.admin.deleteCustomerRestriction as jest.Mock).mockResolvedValue({ data: { restrictionId: 7 } });
});

test('shows reason and status, searches history, and adds a restriction', async () => {
  render(<Page />);
  const list = screen.getByRole('region', { name: 'NG List entries' });
  expect(await within(list).findByText('No show')).toBeInTheDocument();
  expect(within(screen.getByRole('region', { name: 'Customers' })).getByText('Blocked')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Search phone'), { target: { value: '0987' } });
  fireEvent.click(screen.getByRole('button', { name: 'Search' }));
  await waitFor(() => expect(api.admin.getCustomerRestrictions).toHaveBeenCalledWith(
    expect.objectContaining({ phone: '0987', status: 'active' })));
  fireEvent.click(screen.getByRole('button', { name: 'History' }));
  await waitFor(() => expect(api.admin.getCustomerRestrictions).toHaveBeenCalledWith(
    expect.objectContaining({ phone: '0987', status: 'inactive' })));
  fireEvent.change(screen.getByLabelText('Customer phone'), { target: { value: '0987654321' } });
  fireEvent.change(screen.getByLabelText('Reason', { exact: true }), { target: { value: 'Repeated no show' } });
  fireEvent.click(screen.getByRole('button', { name: 'Add to NG List' }));
  await waitFor(() => expect(api.admin.createCustomerRestriction).toHaveBeenCalledWith({
    phoneNumber: '0987654321', reason: 'Repeated no show',
  }));
});

test('edits and removes a restriction, then refreshes both lists', async () => {
  render(<Page />);
  const list = screen.getByRole('region', { name: 'NG List entries' });
  await within(list).findByText('No show');
  fireEvent.click(within(list).getByRole('button', { name: 'Edit reason' }));
  fireEvent.change(screen.getByLabelText('Updated reason'), { target: { value: 'Resolved' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save' }));
  await waitFor(() => expect(api.admin.updateCustomerRestriction).toHaveBeenCalledWith(7, { reason: 'Resolved' }));
  jest.spyOn(window, 'confirm').mockReturnValue(true);
  fireEvent.click(within(list).getByRole('button', { name: 'Remove' }));
  await waitFor(() => expect(api.admin.deleteCustomerRestriction).toHaveBeenCalledWith(7));
  await waitFor(() => expect(api.admin.getCustomers).toHaveBeenCalledTimes(3));
  (window.confirm as jest.Mock).mockRestore();
});

test('shows API errors and keeps the restriction visible', async () => {
  (api.admin.deleteCustomerRestriction as jest.Mock).mockRejectedValueOnce(new Error('Could not remove restriction'));
  render(<Page />);
  const list = screen.getByRole('region', { name: 'NG List entries' });
  await within(list).findByText('No show');
  jest.spyOn(window, 'confirm').mockReturnValue(true);
  fireEvent.click(within(list).getByRole('button', { name: 'Remove' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not remove restriction');
  expect(within(list).getByText('No show')).toBeInTheDocument();
  (window.confirm as jest.Mock).mockRestore();
});
