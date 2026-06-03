"use client";

import React from "react";
import { Sun, Moon, User, Compass, FileText, Users, Database } from "lucide-react";
import { motion } from "framer-motion";

interface NavbarProps {
  view: "landing" | "workspace" | "notes" | "groups" | "dataset_viewer";
  setView: (view: "landing" | "workspace" | "notes" | "groups" | "dataset_viewer") => void;
  theme: "light" | "dark";
  setTheme: (theme: "light" | "dark") => void;
  totalTokensUsed: number;
  pendingTokens: number;
  tokenLimit: number;
  requestsToday: number;
  requestsThisMinute: number;
  onResetTokens: () => void;
}

export default function Navbar({ 
  view, 
  setView, 
  theme, 
  setTheme,
  totalTokensUsed,
  pendingTokens,
  tokenLimit,
  requestsToday,
  requestsThisMinute,
  onResetTokens
}: NavbarProps) {
  const tabs = [
    { id: "landing", label: "Study Room", icon: Compass },
    { id: "notes", label: "My Notes", icon: FileText },
    { id: "groups", label: "Groups", icon: Users },
    { id: "dataset_viewer", label: "Dataset Viewer", icon: Database },
  ] as const;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-zinc-200/80 dark:border-zinc-800/80 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Left: Brand Logo */}
        <div 
          className="flex items-center gap-2 cursor-pointer group"
          onClick={() => setView("landing")}
          id="navbar-logo"
        >
          <div className="relative w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center text-white shadow-md shadow-amber-500/20 group-hover:scale-105 custom-transition">
            <span className="font-serif font-black text-lg">V</span>
            <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-amber-200 animate-pulse"></span>
          </div>
          <span className="font-serif font-bold text-xl sm:text-2xl tracking-wide bg-gradient-to-r from-stone-900 to-stone-600 dark:from-zinc-100 dark:to-zinc-400 bg-clip-text text-transparent group-hover:from-amber-500 group-hover:to-amber-600 custom-transition">
            Vachan Study
          </span>
        </div>

        {/* Center: Desktop Links */}
        <nav className="hidden md:flex items-center gap-1" aria-label="Main Navigation">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = view === tab.id || (tab.id === "landing" && view === "workspace");
            return (
              <button
                key={tab.id}
                id={`nav-tab-${tab.id}`}
                onClick={() => setView(tab.id === "landing" ? "landing" : tab.id)}
                className={`relative px-4 py-2 rounded-full text-sm font-medium flex items-center gap-2 transition-colors duration-200 cursor-pointer ${
                  isActive 
                    ? "text-amber-600 dark:text-amber-500 font-semibold" 
                    : "text-stone-500 hover:text-stone-900 dark:text-zinc-400 dark:hover:text-zinc-100"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
                {isActive && (
                  <motion.div
                    layoutId="activeTabUnderline"
                    className="absolute bottom-0 left-4 right-4 h-0.5 bg-amber-500 dark:bg-amber-500 rounded-full"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
              </button>
            );
          })}
        </nav>

        {/* Right: Actions (Radio Theme Switcher & Profile) */}
        <div className="flex items-center gap-4">

          {/* Token Status Pill (Glassmorphic design with active limits display) */}
          <div className="relative group flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-stone-50 hover:bg-stone-105/80 dark:bg-zinc-900 dark:hover:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-800 text-xs shadow-sm transition-all duration-300">
            <span className="flex items-center gap-1 font-bold text-amber-600 dark:text-amber-500 select-none">
              <svg className="w-3.5 h-3.5 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>Gemini:</span>
            </span>
            
            <div className="flex flex-col gap-0.5 min-w-[90px]">
              <div className="flex justify-between text-[9px] font-extrabold text-zinc-505 dark:text-zinc-400 font-sans tracking-wide">
                <span>{totalTokensUsed.toLocaleString()} used</span>
                <span>{pendingTokens.toLocaleString()} left</span>
              </div>
              <div className="w-full h-1.5 bg-zinc-200 dark:bg-zinc-800 rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all duration-500 ${
                    pendingTokens === 0 
                      ? "bg-red-500" 
                      : (totalTokensUsed / (totalTokensUsed + pendingTokens || 1)) > 0.8
                      ? "bg-amber-500"
                      : "bg-emerald-500"
                  }`} 
                  style={{ width: `${Math.min(100, (totalTokensUsed / (totalTokensUsed + pendingTokens || 1)) * 100)}%` }}
                />
              </div>
            </div>

            {/* Quota reset button */}
            <button
              onClick={onResetTokens}
              title="Refill Gemini Token Quota"
              className="p-1 hover:bg-zinc-200 dark:hover:bg-zinc-700/60 text-zinc-400 dark:text-zinc-500 hover:text-amber-600 dark:hover:text-amber-500 rounded transition-colors duration-200 cursor-pointer"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3 3 3" />
              </svg>
            </button>

            {/* Premium Rich Tooltip displaying Free Tier Limits */}
            <div className="absolute top-full right-0 mt-2.5 w-60 p-3.5 rounded-2xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-850 shadow-xl opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0 pointer-events-none transition-all duration-300 z-50">
              <h4 className="font-sans font-bold text-stone-900 dark:text-zinc-100 text-xs border-b border-zinc-150 dark:border-zinc-800 pb-1.5 mb-2 flex items-center gap-1">
                <span>Gemini API Free Tier Status</span>
              </h4>
              <div className="space-y-1.5 text-[10px] text-zinc-500 dark:text-zinc-450 font-sans leading-relaxed">
                <div className="flex justify-between">
                  <span className="font-semibold">Rate Limit:</span>
                  <span className={`font-bold ${requestsThisMinute >= 15 ? "text-red-500" : "text-zinc-800 dark:text-zinc-200"}`}>
                    {requestsThisMinute}/15 RPM (Min)
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="font-semibold">Daily Requests:</span>
                  <span className={`font-bold ${requestsToday >= 1500 ? "text-red-500" : "text-zinc-800 dark:text-zinc-200"}`}>
                    {requestsToday.toLocaleString()}/1,500 RPD
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="font-semibold">Token Limit (TPM):</span>
                  <span>1,000,000 TPM</span>
                </div>
                <div className="pt-2 mt-1 border-t border-zinc-150 dark:border-zinc-850 flex items-center gap-1 text-[9px] text-amber-600 dark:text-amber-500 font-bold select-none">
                  <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Auto-fallbacks local offline if limited</span>
                </div>
              </div>
            </div>
          </div>
          
          {/* Segmented Radio Theme Switcher */}
          <div 
            className="flex items-center bg-zinc-100 dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 p-0.5 rounded-lg select-none"
            role="radiogroup"
            aria-label="Theme Selection"
          >
            {/* Light Mode Radio Option */}
            <label className="relative flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer transition-colors duration-200">
              <input
                type="radio"
                name="theme-selection"
                value="light"
                checked={theme === "light"}
                onChange={() => setTheme("light")}
                className="sr-only"
                id="theme-radio-light"
              />
              <Sun className={`w-3.5 h-3.5 relative z-10 ${theme === "light" ? "text-amber-600" : "text-zinc-450 dark:text-zinc-500"}`} />
              <span className={`relative z-10 ${theme === "light" ? "text-zinc-950" : "text-zinc-500 dark:text-zinc-400"}`}>
                Light
              </span>
              {theme === "light" && (
                <motion.div
                  layoutId="activeThemeHighlight"
                  className="absolute inset-0 bg-white dark:bg-zinc-800 rounded-md shadow-sm border border-zinc-200/30"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
            </label>

            {/* Dark Mode Radio Option */}
            <label className="relative flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer transition-colors duration-200">
              <input
                type="radio"
                name="theme-selection"
                value="dark"
                checked={theme === "dark"}
                onChange={() => setTheme("dark")}
                className="sr-only"
                id="theme-radio-dark"
              />
              <Moon className={`w-3.5 h-3.5 relative z-10 ${theme === "dark" ? "text-amber-500" : "text-zinc-500 dark:text-zinc-550"}`} />
              <span className={`relative z-10 ${theme === "dark" ? "text-zinc-50" : "text-zinc-500 dark:text-zinc-400"}`}>
                Dark
              </span>
              {theme === "dark" && (
                <motion.div
                  layoutId="activeThemeHighlight"
                  className="absolute inset-0 bg-white dark:bg-zinc-800 rounded-md shadow-sm border border-zinc-200/30"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
            </label>
          </div>

          {/* User Profile */}
          <button
            id="profile-dropdown-button"
            className="p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 hover:bg-zinc-100 dark:bg-zinc-900 dark:hover:bg-zinc-800/80 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 shadow-sm cursor-pointer custom-transition"
            aria-label="User Profile"
          >
            <User className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
