import { api } from './api';

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem('access_token', 'admin-token');
  global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ success: true, data: [] }) });
});

test('shift requests use admin authentication and the documented routes', async () => {
  const shift = { therapistId: 4, dayOfWeek: 'Monday', startTime: '09:00', endTime: '17:00', effectiveFrom: '2026-12-01' };
  await api.admin.getTherapistShifts(2, { therapistId: 4, dayOfWeek: 'Monday' });
  await api.admin.getTherapistShift(7);
  await api.admin.createTherapistShift(shift);
  await api.admin.updateTherapistShift(7, { endTime: '18:00' });
  await api.admin.deleteTherapistShift(7);

  expect(global.fetch).toHaveBeenNthCalledWith(1,
    expect.stringContaining('/admin/shops/2/therapist-shifts?therapistId=4&dayOfWeek=Monday'),
    { headers: { 'Content-Type': 'application/json', Authorization: 'Bearer admin-token' } });
  expect(global.fetch).toHaveBeenNthCalledWith(2, expect.stringContaining('/admin/therapist-shifts/7'),
    { headers: { 'Content-Type': 'application/json', Authorization: 'Bearer admin-token' } });
  expect(global.fetch).toHaveBeenNthCalledWith(3, expect.stringContaining('/admin/therapist-shifts'),
    { method: 'POST', body: JSON.stringify(shift), headers: { 'Content-Type': 'application/json', Authorization: 'Bearer admin-token' } });
  expect(global.fetch).toHaveBeenNthCalledWith(4, expect.stringContaining('/admin/therapist-shifts/7'),
    { method: 'PATCH', body: JSON.stringify({ endTime: '18:00' }), headers: { 'Content-Type': 'application/json', Authorization: 'Bearer admin-token' } });
  expect(global.fetch).toHaveBeenNthCalledWith(5, expect.stringContaining('/admin/therapist-shifts/7'),
    { method: 'DELETE', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer admin-token' } });
});
