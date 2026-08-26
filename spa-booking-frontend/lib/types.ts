// spa-booking-frontend/lib/types.ts

// The user-facing state of the booking, derived from ConversationState.
export interface BookingState {
  shopId?: number;
  shopName?: string;
  courseId?: number;
  courseName?: string;
  addonIds?: number[];
  addonNames?: string[];
  date?: string;
  time?: string;
  duration?: number;
  guests?: number;
  therapistId?: number;
  therapistName?: string;
  phone?: string;
  bookingCode?: string;
  status?: string;
  // A flag to indicate the bot is ready to finalize the booking
  review?: boolean; 
  // A flag to indicate the final confirmation step
  confirm?: boolean;
}

export const ConversationPhase = {
  GREETING: "greeting",
  COLLECTING_PEOPLE: "collecting_people",
  COLLECTING_DURATION: "collecting_duration",
  SELECTING_DATE: "selecting_date",
  SEARCHING_SHOPS: "searching_shops",
  SELECTING_PACKAGE: "selecting_package",
  SEARCHING_COURSES: "searching_courses",
  SEARCHING_SLOTS: "searching_slots",
  SELECTING_THERAPIST: "selecting_therapist",
  CHECKING_ELIGIBILITY: "checking_eligibility",
  REQUESTING_REVIEW: "requesting_review",
  CONFIRMING_BOOKING: "confirming_booking",
  UPDATING_BOOKING: "updating_booking",
  ACTION_COMPLETE: "action_complete",
  BOOKING_COMPLETE: "booking_complete",
  POST_BOOKING: "post_booking",
  LOOKING_UP_BOOKING: "looking_up_booking",
  FAQ_SEARCH: "faq_search",
  FAQ_PROMPT: "faq_prompt",
  ERROR: "error",
} as const;

export type ConversationPhase = (typeof ConversationPhase)[keyof typeof ConversationPhase];

// Matches the backend's ChatRequest model
export interface ChatRequest {
  message: string;
  session_id: string;
  user_id?: string | null;
  start_conversation?: boolean;
  packageSelection?: {
    displayName: string;
    mainCourseId: string;
    addonIds: string[];
    totalDuration: number;
    totalPrice: number;
  };
}

// Matches the backend's ChatResponse model
export interface ChatResponse {
  success: boolean;
  message: string;
  session_id: string;
  phase: ConversationPhase;
  // This will contain the synchronized frontend booking state
  booking_state: BookingState; 
  data?: any;
  payload?: any;
  error?: string | null;
}
