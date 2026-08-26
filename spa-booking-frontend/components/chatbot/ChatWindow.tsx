"use client";

import { useEffect, useRef, useState } from "react";
import { X, Loader2, Send } from "lucide-react";
import { useChat } from "@/lib/hooks/useChat";
import { useAuth } from "@/contexts/AuthContext";
import ChatMessage from "./ChatMessage";
import ConfirmationButtons from "./ConfirmationButtons";
import TherapistOptions from "./TherapistOptions";
import TimePicker from "./TimePicker";
import PackageOptions from "./PackageOptions";
import BookingProgress from "./BookingProgress";
import CurrentBooking from "./CurrentBooking";
import ShopOptions from "./ShopOptions";
import DateOptions from "./DateOptions";
import GuestOptions from "./GuestOptions";
import DurationOptions from "./DurationOptions";
import Greeting from "./Greeting";
import PostBookingOptions from "./PostBookingOptions";
import { ConversationPhase } from "@/lib/types";
import { Shop } from "@/lib/shop";

type Props = {
  onClose: () => void;
};

export default function ChatWindow({ onClose }: Props) {
  const { user } = useAuth();
  const {
    messages,
    input,
    setInput,
    sendMessage,
    isLoading,
    error,
    pendingConfirmation,
    confirm,
    cancel,
    updateMessage,
    bookingState,
    shownGreeting,
    isBookingCompleted,
    restartBooking,
    currentPhase,
  } = useChat(user?.id ?? null);

  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [showPostBookingOptions, setShowPostBookingOptions] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isBookingCompleted) {
      setShowPostBookingOptions(true);
    }
  }, [isBookingCompleted]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isLoading]);

  useEffect(() => {
    if (!isLoading && inputRef.current) inputRef.current.focus();
  }, [isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput("");
  };

  const handlePackageSelect = (pkg: any, messageId: string) => {
    updateMessage(messageId, { selectedPackage: pkg });
  };

  const handlePackageConfirm = (messageId: string) => {
    const message = messages.find((m) => m.id === messageId);
    if (!message || !message.selectedPackage) return;
    
    const { name, course, addons, totalDuration, totalPrice } =
      message.selectedPackage;
    const addonIds = addons.map((a: any) => a.addon_id);

    const packageSelection = {
      displayName: name,
      mainCourseId: course.course_id,
      addonIds,
      totalDuration,
      totalPrice,
    };
    sendMessage(`I'll take the "${name.replace(/\n/g, " ")}" package.`, { packageSelection });
    setEditingSection(null);
  };

  const handleTimeSelect = (time: string | null, messageId: string) => {
    updateMessage(messageId, { selectedTime: time || undefined });
  };

  const handleTimeConfirm = (messageId: string) => {
    const message = messages.find((m) => m.id === messageId);
    if (!message || !message.selectedTime) return;
    sendMessage(message.selectedTime);
    setEditingSection(null);
  };

  const handleShopSelect = (shop: Shop) => {
    sendMessage(`I'd like to visit ${shop.shopName}.`);
    setEditingSection(null);
  };

  const handleDateSelect = (date: string) => {
    sendMessage(date);
    setEditingSection(null);
  };

  const handleGuestsSelect = (guests: number) => {
    sendMessage(guests.toString());
    setEditingSection(null);
  };
  
  const handleDurationSelect = (duration: number) => {
    sendMessage(`${duration} minutes`);
    setEditingSection(null);
  };

  const handleTherapistSelect = (
    therapistId: string | null,
    messageId: string
  ) => {
    updateMessage(messageId, { selectedTherapistId: therapistId || undefined });
  };

  const handleTherapistConfirm = (messageId: string) => {
    const message = messages.find((m) => m.id === messageId);
    if (!message || !message.selectedTherapistId) return;
    const therapist = message.data?.options?.find(
      (t: any) => t.therapistId === message.selectedTherapistId
    );
    if (!therapist) return;
    sendMessage(`${therapist.name}`);
    setEditingSection(null);
  };

  const handleTherapistSkip = () => {
    sendMessage("No preference");
    setEditingSection(null);
  };

  const handleEditSection = (section: string) => {
    if (bookingState?.time) return;
    setEditingSection(section);
  };

  useEffect(() => {
    if (bookingState?.time) {
      setEditingSection(null);
    }
  }, [bookingState?.time]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const handleBookAnother = () => {
    restartBooking();
    setShowPostBookingOptions(false);
  };

  const handleAskQuestion = () => {
    setShowPostBookingOptions(false);
  };

  const activeStep = () => {
    if (!bookingState) return 0;
    if (bookingState.bookingCode) return 11;
    if (bookingState.confirm) return 10;
    if (bookingState.review) return 9;
    if (bookingState.phone) return 8;
    if (bookingState.therapistId) return 7;
    if (bookingState.time) return 6;
    if (bookingState.courseId) return 5;
    if (bookingState.duration) return 4;
    if (bookingState.guests) return 3;
    if (bookingState.date) return 2;
    if (bookingState.shopId) return 1;
    return 0;
  };

  const hideBookingUI =
    currentPhase === ConversationPhase.GREETING ||
    currentPhase === ConversationPhase.FAQ_PROMPT ||
    currentPhase === ConversationPhase.FAQ_SEARCH ||
    currentPhase === ConversationPhase.BOOKING_COMPLETE ||
    currentPhase === ConversationPhase.ACTION_COMPLETE;

  const showBookingUI = !hideBookingUI;

  const renderMessageContent = () => {
    return messages.map((m) => {
       const isPackageSelection = m.phase === ConversationPhase.SELECTING_PACKAGE && m.data?.packages;
       const isTimeSelection = m.phase === ConversationPhase.SEARCHING_SLOTS && m.data?.available_times;
       const isTherapistSelection = m.phase === ConversationPhase.SELECTING_THERAPIST && m.data?.options;
       const isShopSelection = m.phase === ConversationPhase.SEARCHING_SHOPS && m.data?.shops;
       const isDateSelection = m.phase === ConversationPhase.SELECTING_DATE;
       const isGuestSelection = m.phase === ConversationPhase.COLLECTING_PEOPLE;
       const isDurationSelection = m.phase === ConversationPhase.COLLECTING_DURATION;
 
       return (
         <div key={m.id}>
           <ChatMessage message={m} />
           {isShopSelection && (
            <div className="mt-2">
              <ShopOptions
                shops={m.data.shops}
                onSelect={handleShopSelect}
                selectedShopId={bookingState?.shopId || null}
                isCompleted={!!bookingState?.shopId && editingSection !== 'shop'}
                onEdit={() => handleEditSection('shop')}
              />
            </div>
           )}
           {isDateSelection && (
            <div className="mt-2">
              <DateOptions
                onSelect={handleDateSelect}
                isCompleted={!!bookingState?.date && editingSection !== 'date'}
                onEdit={() => handleEditSection('date')}
                selectedDate={bookingState?.date || null}
              />
            </div>
           )}
            {isGuestSelection && (
              <div className="mt-2">
                <GuestOptions
                  onSelect={handleGuestsSelect}
                  selectedGuests={bookingState?.guests || null}
                  isCompleted={!!bookingState?.guests && editingSection !== 'guests'}
                  onEdit={() => handleEditSection('guests')}
                />
              </div>
            )}
            {isDurationSelection && (
              <div className="mt-2">
                <DurationOptions
                  onSelect={handleDurationSelect}
                  selectedDuration={bookingState?.duration || null}
                  isCompleted={!!bookingState?.duration && editingSection !== 'duration'}
                  onEdit={() => handleEditSection('duration')}
                />
              </div>
            )}
           {isPackageSelection && (
             <div className="mt-2">
               <PackageOptions
                 packages={m.data.packages}
                onSelect={(pkg) => handlePackageSelect(pkg, m.id)}
                onConfirm={() => handlePackageConfirm(m.id)}
                selectedPackage={m.selectedPackage || null}
                isCompleted={!!bookingState?.courseId && editingSection !== 'course'}
                onEdit={() => handleEditSection('course')}
              />
            </div>
          )}
          {isTimeSelection && (
            <div className="mt-2">
              <TimePicker
                times={m.data.available_times}
                onSelect={(time) => handleTimeSelect(time, m.id)}
                onConfirm={() => handleTimeConfirm(m.id)}
                selectedTime={m.selectedTime}
                isCompleted={!!bookingState?.time && editingSection !== 'time'}
                onEdit={() => handleEditSection('time')}
              />
            </div>
          )}
          {isTherapistSelection && (
            <div className="mt-2">
              <TherapistOptions
                message={m}
                onSelect={(therapistId) => handleTherapistSelect(therapistId, m.id)}
                onConfirm={() => handleTherapistConfirm(m.id)}
                onSkip={handleTherapistSkip}
                selectedTherapistId={m.selectedTherapistId?.toString()}
                isCompleted={!!bookingState?.therapistId && editingSection !== 'therapist'}
                onEdit={() => handleEditSection('therapist')}
                selectedTherapistName={bookingState?.therapistName}
              />
            </div>
          )}
        </div>
       );
    });
  };

  return (
    <div
      className={`flex h-[70vh] w-full flex-col rounded-2xl bg-white shadow-2xl ring-1 ring-gray-200/50 ${
        showBookingUI ? "min-w-[800px] max-w-4xl" : "min-w-[400px] max-w-lg"
      }`}
    >
      <div className="flex h-full">
        <div
          className={`flex flex-col ${
            showBookingUI ? "w-[65%] border-r border-gray-200/80" : "w-full"
          }`}
        >
          <div className="flex items-center justify-between border-b border-gray-200/80 px-4 py-3">
            <div>
              <h2 className="text-base font-semibold text-gray-800">Booking Assistant</h2>
              <p className="flex items-center gap-1.5 text-xs text-gray-500">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500"></span>
                </span>
                Online
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close chat"
              className="rounded-full p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-400"
            >
              <X size={20} />
            </button>
          </div>

          <div
            ref={scrollRef}
            className="flex-1 space-y-4 overflow-y-auto bg-white/80 p-4"
          >
            {renderMessageContent()}
            {isLoading && (
              <div className="flex items-start gap-2.5">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-gray-100 to-gray-300 text-xs font-bold text-gray-500 shadow-inner">
                  AI
                </div>
                <div
                  className="rounded-xl bg-gray-100 px-3 py-2 text-sm text-gray-700"
                  aria-live="polite"
                >
                  <Loader2 className="inline animate-spin" size={16} />
                  <span className="ml-2">Typing…</span>
                </div>
              </div>
            )}
            {pendingConfirmation && (
              <ConfirmationButtons
                onConfirm={() => confirm("yes")}
                onCancel={() => cancel("no")}
                 disabled={isLoading}
               />
             )}
             {showPostBookingOptions && (
                <PostBookingOptions
                    onBookAnother={handleBookAnother}
                    onAskQuestion={handleAskQuestion}
                />
             )}
             {error && (
               <div
                 role="alert"
                className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200"
              >
                {error}
              </div>
            )}
            {shownGreeting && <Greeting sendMessage={sendMessage} disabled={isLoading} />}
          </div>

          <form
            onSubmit={handleSubmit}
            className="flex items-end gap-2 border-t border-gray-200/80 bg-white/90 p-3 backdrop-blur-sm"
          >
            <label htmlFor="chat-input" className="sr-only">
              Message
            </label>
            <textarea
              id="chat-input"
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={isLoading}
              placeholder={isLoading ? "Waiting for response…" : "Type a message…"}
              className="flex-1 resize-none rounded-lg border border-gray-300/80 bg-white/50 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-gray-100"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              aria-label="Send message"
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm transition-colors hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              <Send size={18} />
            </button>
          </form>
        </div>

        {showBookingUI && (
          <div className="flex w-[35%] flex-col bg-gray-50/50">
            <div className="border-b border-gray-200/80 p-4">
              <BookingProgress activeStep={activeStep()} />
            </div>
            <div className="flex-1 p-4">
              <CurrentBooking
                booking={bookingState || {}}
                editingSection={editingSection}
                onChangeSection={handleEditSection}
                onClearSection={() => setEditingSection(null)}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
