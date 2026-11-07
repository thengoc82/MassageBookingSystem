'use client';

import { useState, useMemo, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';

const BODY_PARTS = ['Neck', 'Back', 'Right Shoulder', 'Left Shoulder', 'Right Arm', 'Left Arm', 'Right Buttock', 'Left Buttock', 'Right Thigh', 'Left Thigh', 'Right Calf', 'Left Calf', 'Right Foot Sole', 'Left Foot Sole'];
const OPTIONS = ['Premium Mattress', 'Cool Premium Mattress', 'Neck & Shoulder Focus', 'Back Focus', 'Lower Back Focus', 'HPM Mattress Pad', 'Premium Face Pillow', 'Recovery Wear', 'Other'];
const MEMBERSHIPS = ['Royal Member', 'App Member', 'Card Member', 'Web Member', 'Senior Member', 'Non-member'];

interface ApiCourse {
  courseId: number;
  courseName: string;
  durations: { duration: number; price: number }[];
  courseType: 'main' | 'addon';
}

function parseDisplayDate(s: string | null): string {
  if (!s) return 'Select a date';
  try {
    const d = new Date(s + 'T00:00:00');
    return d.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  } catch { return s; }
}

function formatPrice(p: number) { return p.toLocaleString() + ' VND'; }

export default function ReservationPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#F5F7FA] flex items-center justify-center text-sm text-gray-500">Loading...</div>}>
      <ReservationForm />
    </Suspense>
  );
}

function ReservationForm() {
  const router = useRouter();
  const sp = useSearchParams();

  const initShopId = sp.get('shopId');
  const initDate = sp.get('date');
  const initTime = sp.get('time') || '12:00';
  const preselectedTherapistId = sp.get('therapistId');
  const slotDuration = Number(sp.get('duration') || '60');
  const people = Number(sp.get('people') || '1');

  const [shopId] = useState<number>(Number(initShopId) || 0);
  const [courses, setCourses] = useState<ApiCourse[]>([]);
  const [displayDate] = useState(() => parseDisplayDate(initDate));
  const [selectedTime] = useState(initTime);
  const [customerType, setCustomerType] = useState<'member' | 'guest'>('member');
  const [phoneNo, setPhoneNo] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [selectedAddons, setSelectedAddons] = useState<Record<number, number>>({});
  const [options, setOptions] = useState<string[]>([]);
  const [tiredParts, setTiredParts] = useState<string[]>([]);
  const [avoidAreas, setAvoidAreas] = useState<string[]>([]);
  const [therapistPref, setTherapistPref] = useState(preselectedTherapistId ? 'specific' : '');
  const [conversationPref, setConversationPref] = useState('');
  const [strength, setStrength] = useState('Normal');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ code: string; name: string } | null>(null);
  const [error, setError] = useState('');

  const fbmCourse = useMemo(() => courses.find(c => c.courseName.toLowerCase().includes('full body')), [courses]);
  const [fbmDuration, setFbmDuration] = useState(0);

  useEffect(() => {
    if (!fbmCourse) return;
    const def = slotDuration >= 30 ? 30 : slotDuration;
    const match = fbmCourse.durations.find(d => d.duration === def);
    setFbmDuration(match ? match.duration : (fbmCourse.durations[0]?.duration || 0));
  }, [fbmCourse, slotDuration]);

  const addonCourses = useMemo(() => courses.filter(c => c.courseId !== fbmCourse?.courseId), [courses, fbmCourse]);

  const selectedTotal = useMemo(() => {
    let total = fbmDuration;
    for (const dur of Object.values(selectedAddons)) total += dur;
    return total;
  }, [fbmDuration, selectedAddons]);
  const remaining = slotDuration - selectedTotal;

  useEffect(() => {
    if (!shopId) return;
    api.shops.getCourses(shopId).then((d: unknown) => {
      const list: ApiCourse[] = Array.isArray(d) ? d as ApiCourse[] : (d as { data?: ApiCourse[] }).data || [];
      setCourses(list);
    }).catch(() => {});
  }, [shopId]);

  const toggleAddon = (courseId: number, duration: number) => {
    setSelectedAddons(prev => {
      if (prev[courseId] === duration) {
        const next = { ...prev };
        delete next[courseId];
        return next;
      }
      if (duration > remaining) return prev;
      return { ...prev, [courseId]: duration };
    });
  };

  const toggleOption = (o: string) => setOptions(p => p.includes(o) ? p.filter(x => x !== o) : [...p, o]);
  const toggleTired = (p: string) => setTiredParts(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);
  const toggleAvoid = (p: string) => setAvoidAreas(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);

  const handleSubmit = async () => {
    if (!shopId || !phoneNo || !fbmCourse) {
      setError('Phone number and course are required');
      return;
    }
    if (remaining !== 0) {
      setError('Please fill the remaining time with additional courses');
      return;
    }
    setSubmitting(true);
    setError('');

    try {
      const services = fbmDuration > 0
        ? Array.from({ length: people }, (_, i) => ({ personIndex: i + 1, courseId: fbmCourse.courseId }))
        : [];

      const addOns: { personIndex: number; courseId: number }[] = [];
      for (const [courseIdStr] of Object.entries(selectedAddons)) {
        const cid = Number(courseIdStr);
        for (let i = 0; i < people; i++) {
          addOns.push({ personIndex: i + 1, courseId: cid });
        }
      }

      const payload: Record<string, unknown> = {
        phoneNumber: phoneNo,
        shopId,
        bookingDate: initDate,
        startTime: selectedTime,
        duration: slotDuration,
        numberOfPeople: people,
        courseId: fbmCourse.courseId,
        services,
        addOns,
        customerName: customerName || undefined,
        massageStrength: strength,
        conversationPreference: conversationPref || undefined,
        focusAreas: tiredParts.length > 0 ? tiredParts : undefined,
        avoidAreas: avoidAreas.length > 0 ? avoidAreas : undefined,
        extraOptions: options.length > 0 ? options : undefined,
        bodyMassageDuration: fbmDuration,
      };

      if (preselectedTherapistId && people === 1) {
        payload.therapistPreferenceType = 'specific';
        payload.therapistPreferenceValue = preselectedTherapistId;
      }

      const res = await api.bookings.create(payload) as any;
      const data = res.data || res;
      try {
        const recent = JSON.parse(localStorage.getItem('recentBookings') || '[]');
        recent.push({ shopId, date: initDate, startTime: selectedTime, duration: slotDuration });
        localStorage.setItem('recentBookings', JSON.stringify(recent.slice(-20)));
      } catch { /* ignore */ }
      setResult({ code: data.bookingCode || '', name: data.therapistName || '' });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Booking failed';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="min-h-screen bg-[#F5F7FA] flex items-center justify-center">
        <div className="bg-white rounded-lg border border-gray-200 p-8 max-w-md w-full text-center space-y-4">
          <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
            <span className="text-emerald-600 text-xl font-bold">&#10003;</span>
          </div>
          <h2 className="text-lg font-bold text-gray-900">Booking Confirmed</h2>
          <div className="bg-gray-50 rounded p-4">
            <div className="text-[11px] text-gray-500 uppercase tracking-wider">Code</div>
            <div className="text-lg font-mono font-bold text-[#1F2B2A]">{result.code}</div>
          </div>
          {result.name && <div className="text-sm text-gray-600">Therapist: <span className="font-semibold">{result.name}</span></div>}
          <button onClick={() => router.push('/dashboard')}
            className="w-full py-2 bg-[#1F2B2A] text-white text-sm font-semibold rounded hover:bg-[#1a2a6b]">Back to Booking</button>
        </div>
      </div>
    );
  }

  const remainingColor = remaining === 0 ? 'text-green-600' : remaining < 0 ? 'text-red-600' : 'text-amber-600';

  return (
    <div className="min-h-screen bg-[#F5F7FA]">
      <div className="max-w-7xl mx-auto p-4 space-y-4">

        {/* Row 1: Date + Time */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 flex gap-8 items-center">
          <div>
            <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Date</label>
            <div className="text-base font-semibold text-gray-900 mt-0.5">{displayDate}</div>
          </div>
          <div className="w-px h-8 bg-gray-200" />
          <div>
            <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Time</label>
            <div className="text-base font-semibold text-gray-900 mt-0.5">{selectedTime}</div>
          </div>
          <div className="w-px h-8 bg-gray-200" />
          <div>
            <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Slot</label>
            <div className="text-base font-semibold text-gray-900 mt-0.5">{slotDuration} min</div>
          </div>
          <div className="w-px h-8 bg-gray-200" />
          <div>
            <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Guests</label>
            <div className="text-base font-semibold text-gray-900 mt-0.5">{people} {people > 1 ? 'people' : 'person'}</div>
          </div>
        </div>

        {/* Customer info */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-3 mb-4">
            <button onClick={() => setCustomerType('member')}
              className={`px-4 py-1.5 rounded text-xs font-medium transition ${customerType === 'member' ? 'bg-[#1F2B2A] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>Member</button>
            <button onClick={() => setCustomerType('guest')}
              className={`px-4 py-1.5 rounded text-xs font-medium transition ${customerType === 'guest' ? 'bg-[#1F2B2A] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>Guest</button>
          </div>
          <div className="flex items-start gap-6 flex-wrap">
            {customerType === 'member' ? (
              <>
                <div className="min-w-[200px] flex-1">
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Membership Number</label>
                  <div className="flex gap-2">
                    <input placeholder="Enter membership no." className="flex-1 border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-900" />
                    <button className="px-3 py-1.5 bg-[#1F2B2A] text-white text-xs rounded hover:bg-[#1a2a6b] shrink-0">Search</button>
                  </div>
                </div>
                <div className="min-w-[200px] flex-1">
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Phone Number</label>
                  <input value={phoneNo} onChange={e => setPhoneNo(e.target.value)} placeholder="090 1234 567" className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-900" />
                </div>
              </>
            ) : (
              <>
                <div className="min-w-[200px] flex-1">
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Customer Name</label>
                  <input value={customerName} onChange={e => setCustomerName(e.target.value)} placeholder="Full name" className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-900" />
                </div>
                <div className="min-w-[200px] flex-1">
                  <label className="text-xs font-medium text-gray-700 mb-1 block">Phone Number</label>
                  <input value={phoneNo} onChange={e => setPhoneNo(e.target.value)} placeholder="090 1234 567" className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm text-gray-900" />
                </div>
              </>
            )}
          </div>
        </div>

        {/* Course selection */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-xs font-semibold text-gray-900 mb-3">Select Courses</h3>

          {/* FBM main course */}
          {fbmCourse && (
            <div className="border border-[#1F2B2A] rounded-lg p-3 mb-4 bg-celadon-soft">
              <div className="text-xs font-semibold text-gray-900">{fbmCourse.courseName} <span className="font-normal text-gray-500">(main)</span></div>
              <div className="flex flex-wrap gap-1 mt-1">
                {fbmCourse.durations.map(d => {
                  const sel = fbmDuration === d.duration;
                  return (
                    <button key={d.duration} onClick={() => setFbmDuration(d.duration)}
                      className={`px-3 py-1 rounded text-[10px] font-semibold border transition ${
                        sel
                          ? 'bg-[#1F2B2A] text-white border-[#1F2B2A]'
                          : 'bg-white text-gray-700 border-gray-200 hover:border-[#1F2B2A]'
                      }`}>
                      {d.duration} min
                    </button>
                  );
                })}
              </div>
              <div className="text-[10px] text-gray-400 mt-1">{people} {people > 1 ? 'people' : 'person'}</div>
            </div>
          )}

          {/* Addon courses */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-3">
            {addonCourses.map(c => (
              <div key={c.courseId}>
                <div className="text-xs font-semibold text-gray-800 mb-1.5">{c.courseName}</div>
                <div className="flex flex-wrap gap-1">
                  {(c.durations || []).map((d: any) => {
                    const sel = selectedAddons[c.courseId] === d.duration;
                    const over = d.duration > remaining && !sel;
                    return (
                      <button key={d.duration}
                        onClick={() => toggleAddon(c.courseId, d.duration)}
                        disabled={over}
                        className={`px-3 py-1 rounded text-[10px] font-semibold border transition ${
                          sel
                            ? 'bg-[#1F2B2A] text-white border-[#1F2B2A]'
                            : over
                              ? 'bg-gray-50 text-gray-300 border-gray-200 cursor-not-allowed'
                              : 'bg-white text-gray-700 border-gray-200 hover:border-[#1F2B2A]'
                        }`}>
                        {d.duration > 0 ? `${d.duration} min` : 'Add'} · {formatPrice(d.price)}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Remaining counter */}
        <div className={`sticky top-4 bg-white rounded-lg border p-4 text-center shadow-md z-10 ${remainingColor}`}>
          <span className="text-sm font-bold">
            Remaining: {remaining} min
            {remaining === 0 && ' ✓'}
            {remaining < 0 && ' (overbooked!)'}
          </span>
        </div>

        {/* 2x4 Grid (options/preferences) */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Options</h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
              {OPTIONS.map(o => (
                <label key={o} className="flex items-center gap-1.5 cursor-pointer">
                  <input type="checkbox" checked={options.includes(o)} onChange={() => toggleOption(o)} className="accent-[#1F2B2A] w-3 h-3" />
                  <span className="text-[11px] text-gray-700">{o}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Tired Parts</h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {BODY_PARTS.map(p => (
                <label key={p} className="flex items-center gap-1.5 cursor-pointer">
                  <input type="checkbox" checked={tiredParts.includes(p)} onChange={() => toggleTired(p)} className="accent-[#1F2B2A] w-3 h-3" />
                  <span className="text-[11px] text-gray-700">{p}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Areas Not To Touch</h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {BODY_PARTS.map(p => (
                <label key={p} className="flex items-center gap-1.5 cursor-pointer">
                  <input type="checkbox" checked={avoidAreas.includes(p)} onChange={() => toggleAvoid(p)} className="accent-[#1F2B2A] w-3 h-3" />
                  <span className="text-[11px] text-gray-700">{p}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Therapist Preference</h3>
            {people > 1 ? (
              <div className="bg-gray-50 border border-gray-200 rounded px-3 py-1.5">
                <span className="text-xs text-gray-600">Therapists will be auto-assigned for group bookings</span>
              </div>
            ) : preselectedTherapistId ? (
              <div className="bg-emerald-50 border border-emerald-200 rounded px-3 py-1.5">
                <span className="text-xs text-emerald-800 font-medium">Locked to selected therapist (#{preselectedTherapistId})</span>
              </div>
            ) : (
              <select value={therapistPref} onChange={e => setTherapistPref(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-xs text-gray-700 bg-white">
                <option value="">No Preference</option>
                <option>Male Preferred</option>
                <option>Female Preferred</option>
              </select>
            )}
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Conversation Preference</h3>
            <div className="space-y-1.5">
              {['No Preference', 'Quiet Session', 'Ask Every Time'].map(p => (
                <label key={p} className="flex items-center gap-1.5 cursor-pointer">
                  <input type="radio" name="convPref" checked={conversationPref === p} onChange={() => setConversationPref(p)} className="accent-[#1F2B2A] w-3 h-3" />
                  <span className="text-[11px] text-gray-700">{p}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-900 mb-2">Massage Strength</h3>
            <div className="flex flex-wrap gap-1">
              {['Stronger', 'Slightly Stronger', 'Normal', 'Slightly Weaker', 'Weaker'].map(s => (
                <button key={s} onClick={() => setStrength(s)}
                  className={`px-2 py-0.5 rounded text-[10px] font-medium border transition ${
                    strength === s ? 'bg-[#1F2B2A] text-white border-[#1F2B2A]' : 'bg-white text-gray-700 border-gray-200'
                  }`}>{s}</button>
              ))}
            </div>
          </div>
        </div>

        {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-xs text-red-700">{error}</div>}
        <div className="h-16" />
      </div>

      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-4 py-2.5 flex items-center gap-3 z-20">
        <button onClick={() => router.push('/dashboard')} className="text-xs text-gray-500 hover:text-gray-700 underline underline-offset-2">Back</button>
        <span className="text-xs text-gray-600 font-mono">#RSV-{initDate?.replace(/-/g, '') || '00000000'}-001</span>
        <div className="flex-1" />
        <button onClick={handleSubmit} disabled={submitting || !phoneNo || !fbmCourse || remaining !== 0}
          className="px-6 py-1.5 bg-[#1F2B2A] text-white text-xs font-semibold rounded hover:bg-[#1a2a6b] shadow-sm disabled:bg-gray-300 disabled:cursor-not-allowed">
          {submitting ? 'Booking...' : remaining !== 0 ? `Fill remaining ${remaining} min` : 'Register Reservation'}
        </button>
      </div>
    </div>
  );
}
