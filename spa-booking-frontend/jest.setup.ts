/* eslint-disable */
import "@testing-library/jest-dom";

// Mock date-fns to avoid timezone-related issues
jest.mock("date-fns", () => ({
  format: () => "12:00 PM",
}));

// Mock react-markdown to avoid ESM transformation issues
jest.mock("react-markdown", () => ({
  __esModule: true,
  default: (props: any) => {
    return props.children as any;
  },
}));

// Mock remark-gfm
jest.mock("remark-gfm", () => ({
  __esModule: true,
  default: () => null,
}));

// Mock lucide-react to avoid ESM transformation issues
jest.mock("lucide-react", () => ({
  __esModule: true,
  Check: () => null,
  X: () => null,
  Loader2: () => null,
  MessageCircle: () => null,
}));