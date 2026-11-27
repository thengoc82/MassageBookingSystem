import { bookableDurations } from './course-options';

test('offers only sums with a main course and valid catalog options', () => {
  expect(bookableDurations([
    { courseId: 1, courseName: 'Main', courseType: 'main', durations: [{ duration: 30, price: 100 }, { duration: 60, price: 200 }] },
    { courseId: 2, courseName: 'Extra', courseType: 'addon', durations: [{ duration: 15, price: 50 }, { duration: 0, price: 10 }] },
    { courseId: 3, courseName: 'Inactive', courseType: 'main', status: 'inactive', durations: [{ duration: 90, price: 300 }] },
  ], 75)).toEqual([30, 45, 60, 75]);
});
