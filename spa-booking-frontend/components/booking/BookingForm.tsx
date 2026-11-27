'use client';

import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { api } from '@/lib/api';
import { bookableCourses, bookableOptions } from '@/lib/course-options';
import { localDateStr, timeToMin } from '@/lib/dates';
import type { Course, CourseDuration, Shop, TimeSlot } from '@/types';

export interface BookingContext {
  shopId: number;
  bookingDate: string;
  startTime: string;
  duration: number;
  numberOfPeople: number;
  therapistId?: number;
  therapistGender?: 'Male' | 'Female';
}

type Selection = Record<number, CourseDuration>;

function formatPrice(price: number) {
  return `${price.toLocaleString('en-US')} VND`;
}

function validContext(value: BookingContext | null): value is BookingContext {
  const date = value?.bookingDate || '';
  const parsedDate = /^\d{4}-\d{2}-\d{2}$/.test(date) ? new Date(`${date}T00:00:00`) : null;
  return !!value && Number.isInteger(value.shopId) && value.shopId > 0 &&
    !!parsedDate && !Number.isNaN(parsedDate.getTime()) &&
    `${parsedDate.getFullYear()}-${String(parsedDate.getMonth() + 1).padStart(2, '0')}-${String(parsedDate.getDate()).padStart(2, '0')}` === date &&
    /^([01]\d|2[0-3]):[0-5]\d$/.test(value.startTime) &&
    Number.isInteger(value.duration) && value.duration > 0 &&
    Number.isInteger(value.numberOfPeople) && value.numberOfPeople > 0 &&
    (value.therapistId === undefined || (Number.isInteger(value.therapistId) && value.therapistId > 0)) &&
    (value.therapistGender === undefined || ['Male', 'Female'].includes(value.therapistGender)) &&
    !(value.therapistId && value.therapistGender) &&
    (value.numberOfPeople === 1 || (!value.therapistId && !value.therapistGender));
}

function responseData<T>(response: T[] | { data?: T[] }): T[] {
  return Array.isArray(response) ? response : response.data || [];
}

interface BookingFormProps {
  context: BookingContext | null;
  onConfirmed?: (startTime: string) => void;
}

export default function BookingForm(props: BookingFormProps) {
  const context = props.context;
  const key = context ? [context.shopId, context.bookingDate, context.startTime,
    context.duration, context.numberOfPeople, context.therapistId, context.therapistGender].join(':') : 'missing';
  return <BookingFormContent key={key} {...props} />;
}

function BookingFormContent({ context, onConfirmed }: BookingFormProps) {
  const [shop, setShop] = useState<Shop | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [selected, setSelected] = useState<Selection>({});
  const [phone, setPhone] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [bookingTime, setBookingTime] = useState(context?.startTime || '');
  const [alternatives, setAlternatives] = useState<TimeSlot[]>([]);
  const [recoveryState, setRecoveryState] = useState<'none' | 'loading' | 'ready' | 'empty' | 'error'>('none');
  const [confirmation, setConfirmation] = useState<{ code: string; therapist?: string } | null>(null);
  const submittingRef = useRef(false);
  const recoveryRequest = useRef(0);

  const shopId = context?.shopId;
  useEffect(() => {
    if (!shopId || !Number.isInteger(shopId)) return;
    let active = true;
    Promise.all([api.shops.getById(shopId), api.shops.getCourses(shopId)])
      .then(([shopResult, courseResult]) => {
        if (!active) return;
        setShop((shopResult.data || shopResult) as Shop);
        setCourses(bookableCourses(responseData<Course>(courseResult)));
        setLoadError('');
      })
      .catch(() => { if (active) setLoadError('Could not load this shop’s courses. Refresh the page to try again.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [shopId]);

  const chosen = useMemo(() => courses.flatMap(course => {
    const choice = selected[course.courseId];
    const option = bookableOptions(course).find(item =>
      item.duration === choice?.duration && item.price === choice?.price);
    return option ? [{ course, duration: option.duration, price: option.price }] : [];
  }), [courses, selected]);
  const chosenMain = chosen.filter(item => item.course.courseType === 'main');
  const chosenAddons = chosen.filter(item => item.course.courseType === 'addon');
  const totalDuration = chosen.reduce((total, item) => total + item.duration, 0);
  const remaining = (context?.duration || 0) - totalDuration;
  const pricePerGuest = chosen.reduce((total, item) => total + item.price, 0);
  const totalPrice = pricePerGuest * (context?.numberOfPeople || 0);
  const phoneValid = /^[+\d][\d\s().-]{7,19}$/.test(phone.trim()) && phone.replace(/\D/g, '').length >= 9;
  const specificTherapistId = context?.numberOfPeople === 1 ? context.therapistId : undefined;
  const therapistGender = context?.numberOfPeople === 1 && !specificTherapistId ? context.therapistGender : undefined;
  const ready = validContext(context) && !!shop?.shopName && shop.status === 'Open' && !loading && !loadError &&
    chosenMain.length > 0 && remaining === 0 && phoneValid && /^([01]\d|2[0-3]):[0-5]\d$/.test(bookingTime);

  function slotQuery(booking: BookingContext) {
    return {
      date: booking.bookingDate,
      duration: booking.duration,
      numberOfPeople: booking.numberOfPeople,
      ...(specificTherapistId ? { show_therapists: true } : {}),
      ...(therapistGender ? { gender: therapistGender } : {}),
    };
  }

  function matchesChoice(slot: TimeSlot, booking: BookingContext) {
    return slot.availableCapacity >= booking.numberOfPeople &&
      (!specificTherapistId || !!slot.availableTherapistIds?.includes(specificTherapistId));
  }

  function isFutureTime(time: string, date: string) {
    const today = localDateStr();
    return date > today || (date === today && timeToMin(time) >
      new Date().getHours() * 60 + new Date().getMinutes());
  }

  async function refreshAlternatives(knownSlots?: TimeSlot[]) {
    if (!context) return;
    const requestId = ++recoveryRequest.current;
    setRecoveryState('loading');
    try {
      const slots = knownSlots || responseData<TimeSlot>(await api.shops.getAvailableSlots(context.shopId, slotQuery(context)));
      if (requestId !== recoveryRequest.current) return;
      const choices = slots.filter(slot => slot.startTime !== bookingTime && matchesChoice(slot, context) &&
        isFutureTime(slot.startTime, context.bookingDate));
      choices.sort((a, b) => Math.abs(timeToMin(a.startTime) - timeToMin(bookingTime)) -
        Math.abs(timeToMin(b.startTime) - timeToMin(bookingTime)) || a.startTime.localeCompare(b.startTime));
      setAlternatives(choices.slice(0, 8));
      setRecoveryState(choices.length ? 'ready' : 'empty');
    } catch {
      if (requestId !== recoveryRequest.current) return;
      setAlternatives([]);
      setRecoveryState('error');
    }
  }

  function choose(courseId: number, option: CourseDuration) {
    setSelected(current => {
      const next = { ...current };
      if (next[courseId]?.duration === option.duration && next[courseId]?.price === option.price) delete next[courseId];
      else next[courseId] = option;
      return next;
    });
    setError('');
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ready || !context || submittingRef.current) return;
    submittingRef.current = true;
    setSubmitting(true);
    setError('');
    let stage: 'precheck' | 'create' = 'precheck';
    try {
      const slotResult = await api.shops.getAvailableSlots(context.shopId, slotQuery(context));
      const slots = responseData<TimeSlot>(slotResult);
      const available = isFutureTime(bookingTime, context.bookingDate) &&
        slots.some(slot => slot.startTime === bookingTime && matchesChoice(slot, context));
      if (!available) {
        setError('This appointment time is no longer available. Choose another time below.');
        await refreshAlternatives(slots);
        return;
      }

      const services = Array.from({ length: context.numberOfPeople }, (_, index) =>
        chosenMain.map(item => ({ personIndex: index + 1, courseId: item.course.courseId }))).flat();
      const addOns = Array.from({ length: context.numberOfPeople }, (_, index) =>
        chosenAddons.map(item => ({ personIndex: index + 1, courseId: item.course.courseId }))).flat();
      stage = 'create';
      const result = await api.bookings.create({
        phoneNumber: phone.trim(),
        shopId: context.shopId,
        bookingDate: context.bookingDate,
        startTime: bookingTime,
        duration: context.duration,
        numberOfPeople: context.numberOfPeople,
        courseId: chosenMain[0].course.courseId,
        services,
        addOns,
        selectedCourses: chosen.map(item => ({ courseId: item.course.courseId, duration: item.duration, price: item.price })),
        notes: notes.trim() || undefined,
        ...(specificTherapistId ? {
          therapistPreferenceType: 'specific',
          therapistPreferenceValue: String(specificTherapistId),
        } : therapistGender ? {
          therapistPreferenceType: 'gender',
          therapistPreferenceValue: therapistGender,
        } : {}),
      }) as { data?: { bookingCode?: string; therapistName?: string }; bookingCode?: string; therapistName?: string };
      const data = result.data || result;
      setConfirmation({ code: data.bookingCode || '', therapist: data.therapistName });
      onConfirmed?.(bookingTime);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Booking failed. Please try again.';
      const code = (cause as { code?: string } | null)?.code;
      if (stage === 'precheck') {
        setError(`Could not check available times: ${message}. Try again.`);
        setRecoveryState('error');
      } else if (code === 'SLOT_UNAVAILABLE' || code === 'INSUFFICIENT_THERAPISTS' || code === 'SHOP_CLOSED') {
        setError('This appointment time is no longer available. Choose another time below.');
        await refreshAlternatives();
      } else if (code === 'BOOKING_CONFLICT') {
        setError('Booking confirmation was busy. Refresh available times or try again.');
        await refreshAlternatives();
      } else {
        setError(message);
      }
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  if (confirmation) return <main className="min-h-screen bg-mist px-4 py-12">
    <div className="mx-auto max-w-lg rounded-2xl border border-line bg-linen p-8 text-center shadow-sm">
      <div className="mb-3 text-4xl text-celadon" aria-hidden="true">✓</div>
      <h1 className="text-2xl font-bold text-basalt">Booking confirmed</h1>
      <p className="mt-3 text-ink-soft">Your booking code is</p>
      <p className="mt-2 text-2xl font-bold tracking-wide text-basalt">{confirmation.code}</p>
      {confirmation.therapist && <p className="mt-3 text-sm text-ink-soft">Therapist: {confirmation.therapist}</p>}
    </div>
  </main>;

  const dateLabel = context?.bookingDate && /^\d{4}-\d{2}-\d{2}$/.test(context.bookingDate)
    ? new Date(`${context.bookingDate}T00:00:00`).toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
    : 'Unavailable';
  const contextValid = validContext(context);

  return <main className="min-h-screen bg-mist px-4 py-8 sm:py-12">
    <form onSubmit={submit} noValidate className="mx-auto max-w-3xl space-y-5">
      <header className="mb-7">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-celadon">Your appointment</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-basalt sm:text-4xl">Complete your booking</h1>
      </header>

      <section aria-labelledby="booking-summary" className="rounded-2xl border border-line bg-linen p-5 sm:p-6">
        <h2 id="booking-summary" className="text-lg font-bold text-basalt">Booking Summary</h2>
        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-3">
          <div><dt className="text-ink-soft">Shop</dt><dd className="mt-1 font-semibold text-basalt">{shop?.shopName || 'Unavailable'}</dd></div>
          <div><dt className="text-ink-soft">Date</dt><dd className="mt-1 font-semibold text-basalt">{dateLabel}</dd></div>
          <div><dt className="text-ink-soft">Appointment time</dt><dd className="mt-1 font-semibold text-basalt">{bookingTime || 'Unavailable'}</dd></div>
          <div><dt className="text-ink-soft">Reserved duration</dt><dd className="mt-1 font-semibold text-basalt">{contextValid ? `${context.duration} min` : 'Unavailable'}</dd></div>
          <div><dt className="text-ink-soft">Guests</dt><dd className="mt-1 font-semibold text-basalt">{contextValid ? context.numberOfPeople : 'Unavailable'}</dd></div>
          {context?.numberOfPeople === 1 && <div><dt className="text-ink-soft">Therapist preference</dt><dd className="mt-1 font-semibold text-basalt">
            {specificTherapistId ? `Selected therapist #${specificTherapistId}` : therapistGender ? `${therapistGender} therapist` : 'Any therapist'}
          </dd></div>}
        </dl>
        {recoveryState !== 'none' && <div className="mt-5 rounded-xl border border-line bg-mist p-4" aria-live="polite">
          <h3 className="font-semibold text-basalt">Choose another time</h3>
          <p className="mt-1 text-sm text-ink-soft">Your shop, date, courses, guests, and contact details are saved on this page.</p>
          {recoveryState === 'loading' && <p className="mt-3 text-sm">Refreshing available times...</p>}
          {recoveryState === 'error' && <p role="alert" className="mt-3 text-sm text-red-700">Could not refresh available times. Try again.</p>}
          {recoveryState === 'empty' && <p className="mt-3 text-sm">No other matching times are available on this date.</p>}
          {recoveryState === 'ready' && <div className="mt-3 flex flex-wrap gap-2">{alternatives.map(slot =>
            <button key={slot.startTime} type="button" onClick={() => { setBookingTime(slot.startTime); setRecoveryState('none'); setError(''); }}
              className="rounded-lg border border-celadon bg-white px-3 py-2 text-sm font-semibold text-basalt hover:bg-celadon-soft">
              {slot.startTime}–{slot.endTime}
            </button>)}</div>}
          <button type="button" onClick={() => void refreshAlternatives()} disabled={recoveryState === 'loading'}
            className="mt-4 text-sm font-semibold text-celadon-deep underline disabled:opacity-50">Refresh available times</button>
        </div>}
      </section>

      <section aria-labelledby="select-courses" className="rounded-2xl border border-line bg-linen p-5 sm:p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="select-courses" className="text-lg font-bold text-basalt">Select Courses</h2>
          <span className="text-xs font-semibold text-celadon">Required</span>
        </div>
        <p className="mt-1 text-sm text-ink-soft">Choose one duration per course. Your choices apply to each guest.</p>
        {loading && contextValid && <p className="mt-4 text-sm text-ink-soft">Loading courses...</p>}
        {!loading && !loadError && !courses.some(course => course.courseType === 'main') && <p className="mt-4 text-sm text-red-700">No main courses are available at this shop.</p>}
        {loadError && <p role="alert" className="mt-4 text-sm text-red-700">{loadError}</p>}
        <div className="mt-5 space-y-4">
          {courses.map(course => <div key={course.courseId} className="rounded-xl border border-line p-4">
            <h3 className="font-semibold text-basalt">{course.courseName}</h3>
            <p className="text-xs text-ink-soft">{course.courseType === 'addon' ? 'Optional add-on' : 'Main course'}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {bookableOptions(course).map(option => {
                const active = selected[course.courseId]?.duration === option.duration && selected[course.courseId]?.price === option.price;
                return <button key={`${option.duration}-${option.price}`} type="button" aria-pressed={active}
                  aria-label={`${course.courseName}, ${option.duration} minutes, ${formatPrice(option.price)}`}
                  onClick={() => choose(course.courseId, option)}
                  className={`min-w-32 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${active
                    ? 'border-celadon bg-celadon-soft text-basalt shadow-sm'
                    : 'border-line bg-white text-basalt hover:border-celadon'}`}>
                  <span className="block font-semibold">{option.duration} min</span>
                  <span className="block text-xs">{formatPrice(option.price)}</span>
                </button>;
              })}
            </div>
          </div>)}
        </div>
        <div className="mt-5 rounded-xl bg-mist p-4 text-sm text-basalt" aria-live="polite">
          <div className="flex flex-wrap justify-between gap-2"><span>Selected duration</span><strong>{totalDuration} min</strong></div>
          <div className="mt-1 flex flex-wrap justify-between gap-2"><span>Remaining duration</span><strong className={remaining < 0 ? 'text-red-700' : 'text-celadon-deep'}>{remaining} min</strong></div>
          <div className="mt-2 flex flex-wrap justify-between gap-2 border-t border-line pt-2"><span>Total price{context && context.numberOfPeople > 1 ? ` for ${context.numberOfPeople} guests` : ''}</span><strong>{formatPrice(totalPrice)}</strong></div>
        </div>
        {chosenMain.length === 0 ? <p className="mt-3 text-sm text-red-700">Select at least one main course.</p>
          : remaining !== 0 ? <p className="mt-3 text-sm text-red-700">{remaining > 0 ? `Select ${remaining} more minutes to match your reserved duration.` : `Remove ${Math.abs(remaining)} minutes to match your reserved duration.`}</p>
          : <p className="mt-3 text-sm text-celadon-deep">Your courses fill the reserved duration exactly.</p>}
      </section>

      <section aria-labelledby="customer-information" className="rounded-2xl border border-line bg-linen p-5 sm:p-6">
        <h2 id="customer-information" className="text-lg font-bold text-basalt">Customer Information</h2>
        <div className="mt-4 space-y-4">
          <div><label htmlFor="booking-phone" className="block text-sm font-semibold text-basalt">Phone Number <span className="text-celadon">*</span></label>
            <input id="booking-phone" type="tel" autoComplete="tel" value={phone} onChange={event => setPhone(event.target.value)}
              aria-invalid={!!phone && !phoneValid} aria-describedby="phone-help" placeholder="090 1234 567"
              className="mt-2 w-full rounded-lg border border-line bg-white px-3 py-3 text-basalt sm:max-w-sm" />
            <p id="phone-help" className={`mt-1 text-xs ${phone && !phoneValid ? 'text-red-700' : 'text-ink-soft'}`}>{phone && !phoneValid ? 'Enter a valid phone number with at least 9 digits.' : 'Required for your booking confirmation.'}</p>
          </div>
          <div><label htmlFor="booking-notes" className="block text-sm font-semibold text-basalt">Special Requests <span className="font-normal text-ink-soft">(optional)</span></label>
            <textarea id="booking-notes" rows={3} value={notes} onChange={event => setNotes(event.target.value)} placeholder="Anything we should know?"
              className="mt-2 w-full rounded-lg border border-line bg-white px-3 py-3 text-basalt" /></div>
        </div>
        <div aria-labelledby="final-summary" className="mt-6 border-t border-line pt-5">
          <h2 id="final-summary" className="text-lg font-bold text-basalt">Final booking summary</h2>
          {chosen.length ? <ul className="mt-4 divide-y divide-line border-y border-line text-sm">
            {chosen.map(item => <li key={item.course.courseId} className="flex flex-wrap justify-between gap-2 py-3 text-basalt">
              <span>{item.course.courseName} · {item.duration} min</span><strong>{formatPrice(item.price)}{context && context.numberOfPeople > 1 ? ' per guest' : ''}</strong>
            </li>)}
          </ul> : <p className="mt-3 text-sm text-ink-soft">No courses selected yet.</p>}
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm text-basalt">
            <div><dt className="text-ink-soft">Total duration</dt><dd className="font-semibold">{totalDuration} min</dd></div>
            <div><dt className="text-ink-soft">Total price</dt><dd className="font-semibold">{formatPrice(totalPrice)}</dd></div>
            <div><dt className="text-ink-soft">Phone Number</dt><dd className="font-semibold">{phone.trim() || 'Not provided'}</dd></div>
            <div><dt className="text-ink-soft">Special Requests</dt><dd className="font-semibold whitespace-pre-wrap">{notes.trim() || 'None'}</dd></div>
          </dl>
          {!contextValid && <p role="alert" className="mt-4 text-sm text-red-700">Booking details are incomplete. Please select a slot again.</p>}
          {!loading && contextValid && !shop?.shopName && !loadError && <p role="alert" className="mt-4 text-sm text-red-700">Shop information is unavailable.</p>}
          {!loading && shop?.status === 'Closed' && <p role="alert" className="mt-4 text-sm text-red-700">This shop is closed. Choose another shop.</p>}
          {!phoneValid && <p className="mt-4 text-sm text-red-700">Enter a valid phone number to confirm.</p>}
          {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          <button type="submit" disabled={!ready || submitting}
            className="mt-5 w-full rounded-xl bg-basalt px-5 py-3 font-semibold text-white transition-colors hover:bg-basalt-2 disabled:cursor-not-allowed disabled:bg-line disabled:text-ink-soft sm:w-auto">
            {submitting ? 'Confirming...' : 'Confirm Booking'}
          </button>
        </div>
      </section>
    </form>
  </main>;
}
