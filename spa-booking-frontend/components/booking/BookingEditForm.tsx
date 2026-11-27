'use client';

import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { api } from '@/lib/api';
import { bookableCourses, bookableOptions } from '@/lib/course-options';
import { localDateStr, timeToMin } from '@/lib/dates';
import type { Booking, Course, CourseDuration, TherapistInfo, TimeSlot } from '@/types';

type Preference = 'keep' | 'any' | 'Male' | 'Female' | 'specific';
type Selection = Record<number, CourseDuration>;

function savedDuration(booking: Booking) {
  return timeToMin(booking.endTime) - timeToMin(booking.startTime);
}

function savedSelection(booking: Booking, courses: Course[]): Selection {
  const ids = [...new Set([...(booking.services || []), ...(booking.addOns || [])].map(row => row.courseId))];
  const saved = Array.isArray(booking.preferences?.selectedCourses)
    ? booking.preferences.selectedCourses as { courseId: number; duration: number; price: number }[] : [];
  const selection: Selection = {};
  for (const id of ids) {
    const course = courses.find(item => item.courseId === id);
    if (!course) continue;
    const prior = saved.find(item => item.courseId === id);
    const chosen = prior && bookableOptions(course).find(item => item.duration === prior.duration && item.price === prior.price);
    if (chosen) selection[id] = chosen;
  }
  return selection;
}

function editError(cause: unknown) {
  const error = cause as { status?: number; code?: string; message?: string };
  switch (error.code) {
    case 'INVALID_MODIFY_STATUS': return 'This booking can no longer be edited. Its current status has been refreshed.';
    case 'SLOT_UNAVAILABLE':
    case 'INSUFFICIENT_THERAPISTS': return 'That time or therapist is no longer available. Choose another option and try again.';
    case 'SHOP_CLOSED': return 'The shop is closed for the requested time. Choose another time.';
    case 'BOOKING_CONFLICT': return 'Booking updates are busy. Please try again.';
    case 'VALIDATION_ERROR': return error.message || 'The selected courses or duration are no longer valid.';
    default: return error.message || 'Could not update this booking. Please try again.';
  }
}

export default function BookingEditForm({ booking, onSaved, onStatusChanged, onAccessExpired, onClose }: {
  booking: Booking;
  onSaved: () => Promise<void>;
  onStatusChanged: () => Promise<void>;
  onAccessExpired: () => void;
  onClose: () => void;
}) {
  const [date, setDate] = useState(booking.bookingDate);
  const [time, setTime] = useState(booking.startTime);
  const [preference, setPreference] = useState<Preference>('keep');
  const [therapistId, setTherapistId] = useState('');
  const [therapists, setTherapists] = useState<TherapistInfo[]>([]);
  const [servicesOpen, setServicesOpen] = useState(false);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selection, setSelection] = useState<Selection>({});
  const [unresolvedSavedChoices, setUnresolvedSavedChoices] = useState(false);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState('');
  const [slots, setSlots] = useState<TimeSlot[]>([]);
  const [slotLoading, setSlotLoading] = useState(false);
  const [slotError, setSlotError] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const chosen = useMemo(() => courses.flatMap(course => {
    const option = selection[course.courseId];
    return option ? [{ course, ...option }] : [];
  }), [courses, selection]);
  const duration = servicesOpen ? chosen.reduce((sum, item) => sum + item.duration, 0) : savedDuration(booking);
  const hasMain = chosen.some(item => item.course.courseType === 'main');
  const existingIds = [...new Set([...(booking.services || []), ...(booking.addOns || [])].map(row => row.courseId))];
  const changed = date !== booking.bookingDate || time !== booking.startTime || servicesOpen || preference !== 'keep';
  const timeIsFuture = date > localDateStr() || (date === localDateStr() && timeToMin(time) > new Date().getHours() * 60 + new Date().getMinutes());

  useEffect(() => {
    if (booking.numberOfPeople !== 1) return;
    let active = true;
    api.shops.getAvailableSlots(booking.shopId, {
      date: booking.bookingDate, duration: savedDuration(booking), numberOfPeople: 1, show_therapists: true,
    }).then((response: { therapists?: TherapistInfo[] }) => {
      if (active) setTherapists(response.therapists || []);
    }).catch(() => { /* A named therapist can be chosen after a later availability refresh. */ });
    return () => { active = false; };
  }, [booking]);

  async function openServices() {
    setServicesOpen(true);
    if (courses.length) return;
    setCatalogLoading(true);
    setCatalogError('');
    try {
      const response = await api.shops.getCourses(booking.shopId);
      const list = bookableCourses((response.data || []) as Course[]);
      setCourses(list);
      const initial = savedSelection(booking, list);
      setSelection(initial);
      setUnresolvedSavedChoices(existingIds.some(id => !initial[id]));
    } catch {
      setCatalogError('Could not load the current course catalog. Try again.');
    } finally {
      setCatalogLoading(false);
    }
  }

  async function refreshSlots() {
    setSlotLoading(true);
    setSlotError('');
    try {
      const response = await api.shops.getAvailableSlots(booking.shopId, {
        date, duration: duration || savedDuration(booking), numberOfPeople: booking.numberOfPeople,
        ...(booking.numberOfPeople === 1 ? { show_therapists: true } : {}),
        ...(preference === 'Male' || preference === 'Female' ? { gender: preference } : {}),
      });
      setSlots((response.data || []).filter((slot: TimeSlot) =>
        slot.availableCapacity >= booking.numberOfPeople &&
        (preference !== 'specific' || !!slot.availableTherapistIds?.includes(Number(therapistId)))));
      if (response.therapists) setTherapists(response.therapists);
    } catch {
      setSlots([]);
      setSlotError('Could not load available times. You can still submit a time for the final booking check.');
    } finally {
      setSlotLoading(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || !changed) return;
    setError('');
    if (!timeIsFuture) {
      setError('Choose a future date and time.');
      return;
    }
    if (servicesOpen && (!hasMain || duration <= 0)) {
      setError('Choose at least one valid main course.');
      return;
    }
    if (preference === 'specific' && !therapistId) {
      setError('Choose a therapist.');
      return;
    }
    const update: Record<string, unknown> = {};
    if (date !== booking.bookingDate) update.bookingDate = date;
    if (time !== booking.startTime) update.startTime = time;
    if (servicesOpen) {
      update.duration = duration;
      update.services = Array.from({ length: booking.numberOfPeople }, (_, index) =>
        chosen.filter(item => item.course.courseType === 'main').map(item => ({ personIndex: index + 1, courseId: item.course.courseId }))).flat();
      update.addOns = Array.from({ length: booking.numberOfPeople }, (_, index) =>
        chosen.filter(item => item.course.courseType === 'addon').map(item => ({ personIndex: index + 1, courseId: item.course.courseId }))).flat();
      update.selectedCourses = chosen.map(item => ({ courseId: item.course.courseId, duration: item.duration, price: item.price }));
    }
    if (preference !== 'keep') {
      update.therapistPreferenceType = preference === 'any' ? 'no_preference' : preference === 'specific' ? 'specific' : 'gender';
      if (preference === 'specific') update.therapistPreferenceValue = Number(therapistId);
      if (preference === 'Male' || preference === 'Female') update.therapistPreferenceValue = preference;
    }
    setSaving(true);
    try {
      await api.bookings.update(booking.bookingId, update, true);
      await onSaved();
    } catch (cause) {
      const status = (cause as { status?: number })?.status;
      if (status === 401) onAccessExpired();
      else {
        setError(editError(cause));
        if ((cause as { code?: string })?.code === 'INVALID_MODIFY_STATUS') await onStatusChanged();
      }
    } finally {
      setSaving(false);
    }
  }

  return <form onSubmit={submit} className="rounded-xl border border-celadon bg-white p-6 space-y-5">
    <div>
      <h2 className="text-lg font-bold text-gray-900">Edit booking</h2>
      <p className="mt-1 text-sm text-gray-600">You can change the date, time, courses, duration, and one-guest therapist preference. Shop, guests, phone, and special requests stay as booked.</p>
    </div>
    <dl className="grid gap-2 rounded-lg bg-gray-50 p-3 text-sm text-gray-800 sm:grid-cols-2">
      <div><dt className="text-gray-500">Shop</dt><dd>{booking.shopName || `Shop #${booking.shopId}`}</dd></div>
      <div><dt className="text-gray-500">Guests</dt><dd>{booking.numberOfPeople}</dd></div>
      <div><dt className="text-gray-500">Phone</dt><dd>{booking.phoneNumber}</dd></div>
      <div><dt className="text-gray-500">Special requests</dt><dd>{typeof booking.preferences?.notes === 'string' ? booking.preferences.notes : 'None'}</dd></div>
    </dl>
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-medium text-gray-800">Date
        <input type="date" required min={localDateStr()} value={date} onChange={event => { setDate(event.target.value); setSlots([]); }} className="mt-1 block w-full rounded-lg border border-gray-300 p-2 text-gray-900" />
      </label>
      <label className="text-sm font-medium text-gray-800">Start time
        <input type="time" required value={time} onChange={event => setTime(event.target.value)} className="mt-1 block w-full rounded-lg border border-gray-300 p-2 text-gray-900" />
      </label>
    </div>
    <div className="text-sm text-gray-700">Reserved duration: <strong>{duration || savedDuration(booking)} minutes</strong>. Change courses to change duration.</div>
    <div>
      <button type="button" onClick={() => { if (servicesOpen) setServicesOpen(false); else void openServices(); }} className="text-sm font-semibold text-celadon-deep underline">
        {servicesOpen ? 'Keep saved courses' : 'Change courses and duration'}
      </button>
      {servicesOpen && <div className="mt-3 space-y-3">
        {catalogLoading && <p className="text-sm">Loading courses...</p>}
        {catalogError && <p role="alert" className="text-sm text-red-700">{catalogError}</p>}
        {courses.map(course => <div key={course.courseId} className="rounded-lg border border-gray-200 p-3">
          <p className="font-medium text-gray-900">{course.courseName} <span className="text-xs text-gray-500">({course.courseType === 'main' ? 'main' : 'add-on'})</span></p>
          <div className="mt-2 flex flex-wrap gap-2">{bookableOptions(course).map(option => {
            const selected = selection[course.courseId]?.duration === option.duration && selection[course.courseId]?.price === option.price;
            return <button key={`${option.duration}-${option.price}`} type="button" aria-pressed={selected}
              onClick={() => setSelection(current => {
                const next = { ...current };
                if (selected) delete next[course.courseId]; else next[course.courseId] = option;
                return next;
              })}
              className={`rounded-lg border px-3 py-2 text-sm ${selected ? 'border-celadon bg-celadon-soft text-gray-900' : 'border-gray-300 text-gray-700'}`}>
              {option.duration} min · {option.price.toLocaleString('en-US')} VND
            </button>;
          })}</div>
        </div>)}
        {unresolvedSavedChoices && <p className="text-sm text-amber-800">Some saved course options could not be preselected. Choose current options; any unselected courses will be removed when you save.</p>}
        <p className="text-sm text-gray-700">Selected total: {duration} minutes per guest</p>
      </div>}
    </div>
    {booking.numberOfPeople === 1 && <label className="block text-sm font-medium text-gray-800">Therapist preference
      <select value={preference} onChange={event => setPreference(event.target.value as Preference)} className="mt-1 block w-full rounded-lg border border-gray-300 p-2 text-gray-900">
        <option value="keep">Keep assignment if available</option>
        <option value="any">Any available therapist</option>
        <option value="Female">Female therapist</option>
        <option value="Male">Male therapist</option>
        <option value="specific">Choose a therapist</option>
      </select>
      {preference === 'specific' && <select aria-label="Choose therapist" value={therapistId} onChange={event => setTherapistId(event.target.value)} className="mt-2 block w-full rounded-lg border border-gray-300 p-2 text-gray-900">
        <option value="">Select a therapist</option>
        {therapists.map(item => <option key={item.therapistId} value={item.therapistId}>{item.name}</option>)}
      </select>}
      <span className="mt-1 block text-xs font-normal text-gray-500">The current therapist is {booking.therapistName || 'not listed'}. An “any” choice may keep this assignment when it remains eligible.</span>
    </label>}
    <div>
      <button type="button" onClick={() => void refreshSlots()} disabled={slotLoading || duration <= 0} className="text-sm font-semibold text-celadon-deep underline disabled:opacity-50">{slotLoading ? 'Checking times...' : 'See available times'}</button>
      {slotError && <p role="alert" className="mt-2 text-sm text-red-700">{slotError}</p>}
      {slots.length > 0 && <div className="mt-2 flex flex-wrap gap-2">{slots.filter(slot => date > localDateStr() || timeToMin(slot.startTime) > new Date().getHours() * 60 + new Date().getMinutes()).slice(0, 24).map(slot =>
        <button type="button" key={slot.startTime} onClick={() => setTime(slot.startTime)} className="rounded-lg border border-gray-300 px-2 py-1 text-sm text-gray-800 hover:border-celadon">{slot.startTime}</button>)}</div>}
      <p className="mt-1 text-xs text-gray-500">The availability list includes your current booking as occupied. You can keep its time; the final update checks availability without counting this booking.</p>
    </div>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <div className="flex gap-3">
      <button type="submit" disabled={saving || !changed || (servicesOpen && (catalogLoading || !!catalogError))} className="rounded-lg bg-celadon px-4 py-2 font-semibold text-white disabled:opacity-50">{saving ? 'Saving...' : 'Save changes'}</button>
      <button type="button" onClick={onClose} disabled={saving} className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700">Close</button>
    </div>
  </form>;
}
