"use client";

import { useAuth } from "@/contexts/AuthContext";
import Link from "next/link";
import AuthNav from "@/components/AuthNav";
import React from "react";

export default function NavBar() {
  const { user } = useAuth();
  const getDashboardHref = () => {
    console.log("User object from useAuth:", user);
    if (!user) {
      return "/";
    }
    const href = (() => {
      switch (user.role) {
        case "admin":
          return "/admin";
        case "therapist":
          return "/therapist";
        default:
          return "/dashboard";
      }
    })();
    console.log("Determined href:", href);
    return href;
  };

  return (
    <>
      <nav className="bg-[#031050]">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
                <Link href={getDashboardHref()} className="text-2xl font-bold text-white">
                Massage Booking App
              </Link>
              <AuthNav />
          </div>
        </div>
      </nav>
      <div className="h-0.5 bg-gradient-to-r from-[#1E3A5F] via-[#5B7FAF] to-[#1E3A5F]" />
    </>
  );
}