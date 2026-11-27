import type { Course, CourseDuration } from '@/types';

export function bookableOptions(course: Course): CourseDuration[] {
  const valid = (course.durations || []).filter(option =>
    Number.isInteger(option.duration) && option.duration > 0 &&
    Number.isInteger(option.price) && option.price >= 0);
  return valid.filter((option, index) => valid.findIndex(item =>
    item.duration === option.duration && item.price === option.price) === index);
}

export function bookableCourses(courses: Course[]): Course[] {
  return courses.filter(course =>
    (course.courseType === 'main' || course.courseType === 'addon') &&
    course.status !== 'inactive' && bookableOptions(course).length > 0);
}

/** Durations that can be made from one or more main courses and optional add-ons. */
export function bookableDurations(courses: Course[], maxMinutes: number): number[] {
  let none = new Set([0]);
  let withMain = new Set<number>();
  for (const course of bookableCourses(courses)) {
    const options = bookableOptions(course);
    const nextNone = new Set(none);
    const nextWithMain = new Set(withMain);
    for (const option of options) {
      for (const minutes of withMain) {
        if (minutes + option.duration <= maxMinutes) nextWithMain.add(minutes + option.duration);
      }
      for (const minutes of none) {
        if (minutes + option.duration > maxMinutes) continue;
        if (course.courseType === 'main') nextWithMain.add(minutes + option.duration);
        else nextNone.add(minutes + option.duration);
      }
    }
    none = nextNone;
    withMain = nextWithMain;
  }
  return [...withMain].sort((a, b) => a - b);
}
