"use client";

import { createContext, useContext, useState, ReactNode } from "react";

type User = {
  id: string;
  name: string;
};

type AuthContextType = {
  user: User | null;
  login: (user: User) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const getInitialUser = (): User | null => {
  if (typeof window === "undefined") return null;
  try {
    const saved = window.localStorage.getItem("auth_user");
    if (saved) {
      return JSON.parse(saved) as User;
    }
  } catch (e) {
    console.error("Failed to parse auth_user from localStorage", e);
  }
  return null;
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(getInitialUser);

  const login = (newUser: User) => {
    setUser(newUser);
    try {
      localStorage.setItem("auth_user", JSON.stringify(newUser));
    } catch (e) {
      console.error("Failed to save auth_user to localStorage", e);
    }
  };

  const logout = () => {
    setUser(null);
    try {
      localStorage.removeItem("auth_user");
    } catch (e) {
      console.error("Failed to remove auth_user from localStorage", e);
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}