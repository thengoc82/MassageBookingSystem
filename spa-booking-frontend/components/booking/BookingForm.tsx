'use client';

import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { api } from '@/lib/api';
import type { Course, Shop, TimeSlot } from '@/types';

export interface BookingContext {
  shopId: number;
  bookingDate: string;
  startTime: string;
  duration: number;
  numberOfPeople: number;
  therapistId?: number;
}

type Selection = Record<number, number>;

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
    (value.therapistId === undefined || (Number.isInteger(value.therapistId) && value.therapistId > 0));
}

function responseData<T>(response: T[] | { data?: T[] }): T[] {
  return Array.isArray(response) ? response : response.data || [];
}

export default function BookingForm({ context, onConfirmed }: {
  context: BookingContext | null;
  onConfirmed?: () => void;
}) {
  const [shop, setShop] = useState<Shop | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [selected, setSelected] = useState<Selection>({});
  const [phone, setPhone] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [confirmation, setConfirmation] = useState<{ code: string; therapist?: string } | null>(null);
  const submittingRef = useRef(false);

  const shopId = context?.shopId;
  useEffect(() => {
    if (!shopId || !Number.isInteger(shopId)) return;
    let active = true;
    Promise.all([api.shops.getById(shopId), api.shops.getCourses(shopId)])
      .then(([shopResult, courseResult]) => {
        if (!active) return;
        setShop((shopResult.data || shopResult) as Shop);
        setCourses(responseData<Course>(courseResult).filter(course =>
          course.courseType === 'main' && course.status !== 'inactive' &&
          course.durations?.some(option => option.duration > 0 && Number.isFinite(option.price))));
        setLoadError('');
      })
      .catch(() => { if (active) setLoadError('Could not load this shop’s courses. Refresh the page to try again.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [shopId]);

  const chosen = useMemo(() => courses.flatMap(course => {
    const option = course.durations.find(item => item.duration === selected[course.courseId]);
    return option ? [{ course, duration: option.duration, price: option.price }] : [];
  }), [courses, selected]);
  const totalDuration = chosen.reduce((total, item) => total + item.duration, 0);
  const remaining = (context?.duration || 0) - totalDuration;
  const pricePerGuest = chosen.reduce((total, item) => total + item.price, 0);
  const totalPrice = pricePerGuest * (context?.numberOfPeople || 0);
  const phoneValid = /^[+\d][\d\s().-]{7,19}$/.test(phone.trim()) && phone.replace(/\D/g, '').length >= 9;
  const specificTherapistId = context?.numberOfPeople === 1 ? context.therapistId : undefined;
  const ready = validContext(context) && !!shop?.shopName && !loading && !loadError &&
    chosen.length > 0 && remaining === 0 && phoneValid;

  function choose(courseId: number, duration: number) {
    setSelected(current => {
      const next = { ...current };
      if (next[courseId] === duration) delete next[courseId];
      else next[courseId] = duration;
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
    try {
      const slotResult = await api.shops.getAvailableSlots(context.shopId, {
        date: context.bookingDate,
        duration: context.duration,
        numberOfPeople: context.numberOfPeople,
        ...(specificTherapistId ? { show_therapists: true } : {}),
      });
      const slots = responseData<TimeSlot>(slotResult);
      const available = slots.some(slot => slot.startTime === context.startTime &&
        slot.availableCapacity >= context.numberOfPeople &&
        (!specificTherapistId || slot.availableTherapistIds?.includes(specificTherapistId)));
      if (!available) {
        setError('This appointment time is no longer available. Please choose another time from the schedule.');
        return;
      }

      const services = Array.from({ length: context.numberOfPeople }, (_, index) =>
        chosen.map(item => ({ personIndex: index + 1, courseId: item.course.courseId }))).flat();
      const result = await api.bookings.create({
        phoneNumber: phone.trim(),
        shopId: context.shopId,
        bookingDate: context.bookingDate,
        startTime: context.startTime,
        duration: context.duration,
        numberOfPeople: context.numberOfPeople,
        courseId: chosen[0].course.courseId,
        services,
        addOns: [],
        selectedCourses: chosen.map(item => ({ courseId: item.course.courseId, duration: item.duration, price: item.price })),
        notes: notes.trim() || undefined,
        ...(specificTherapistId ? {
          therapistPreferenceType: 'specific',
          therapistPreferenceValue: String(specificTherapistId),
        } : {}),
      }) as { data?: { bookingCode?: string; therapistName?: string }; bookingCode?: string; therapistName?: string };
      const data = result.data || result;
      setConfirmation({ code: data.bookingCode || '', therapist: data.therapistName });
      onConfirmed?.();
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Booking failed. Please try again.';
      setError(message);
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
          <div><dt className="text-ink-soft">Appointment time</dt><dd className="mt-1 font-semibold text-basalt">{context?.startTime || 'Unavailable'}</dd></div>
          <div><dt className="text-ink-soft">Reserved duration</dt><dd className="mt-1 font-semibold text-basalt">{contextValid ? `${context.duration} min` : 'Unavailable'}</dd></div>
          <div><dt className="text-ink-soft">Guests</dt><dd className="mt-1 font-semibold text-basalt">{contextValid ? context.numberOfPeople : 'Unavailable'}</dd></div>
        </dl>
      </section>

      <section aria-labelledby="select-courses" className="rounded-2xl border border-line bg-linen p-5 sm:p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="select-courses" className="text-lg font-bold text-basalt">Select Courses</h2>
          <span className="text-xs font-semibold text-celadon">Required</span>
        </div>
        <p className="mt-1 text-sm text-ink-soft">Choose one duration per course. Your choices apply to each guest.</p>
        {loading && contextValid && <p className="mt-4 text-sm text-ink-soft">Loading courses...</p>}
        {!loading && !loadError && courses.length === 0 && <p className="mt-4 text-sm text-red-700">No courses are available at this shop.</p>}
        {loadError && <p role="alert" className="mt-4 text-sm text-red-700">{loadError}</p>}
        <div className="mt-5 space-y-4">
          {courses.map(course => <div key={course.courseId} className="rounded-xl border border-line p-4">
            <h3 className="font-semibold text-basalt">{course.courseName}</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {course.durations.filter(option => option.duration > 0 && Number.isFinite(option.price)).map(option => {
                const active = selected[course.courseId] === option.duration;
                return <button key={option.duration} type="button" aria-pressed={active}
                  aria-label={`${course.courseName}, ${option.duration} minutes, ${formatPrice(option.price)}`}
                  onClick={() => choose(course.courseId, option.duration)}
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
        {chosen.length === 0 ? <p className="mt-3 text-sm text-red-700">Select at least one course.</p>
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
