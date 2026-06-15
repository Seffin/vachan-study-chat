"use client";

import React, { useState } from "react";
import { Sun, Moon, User, Compass, FileText, Users, Database, Menu, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

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
  const [menuOpen, setMenuOpen] = useState(false);

  const tabs = [
    { id: "landing", label: "Study Room", icon: Compass },
    { id: "notes", label: "My Notes", icon: FileText },
    { id: "groups", label: "Groups", icon: Users },
    { id: "dataset_viewer", label: "Dataset Viewer", icon: Database },
  ] as const;

  return (
    <header className="sticky top-0 z-45 w-full border-b border-zinc-200/80 dark:border-zinc-800/80 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Left: Brand Logo */}
        <div 
          className="flex items-center gap-2 cursor-pointer group"
          onClick={() => {
            setView("landing");
            setMenuOpen(false);
          }}
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

        {/* Center: Desktop Links (Hidden on mobile/tablet) */}
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

        {/* Right: Actions */}
        <div className="flex items-center gap-2 md:gap-4">

          {/* Desktop Token Status Pill (Hidden on mobile) */}
          <div className="hidden md:flex relative group items-center gap-2.5 px-3 py-1.5 rounded-xl bg-stone-50 hover:bg-stone-105/80 dark:bg-zinc-900 dark:hover:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-800 text-xs shadow-sm transition-all duration-300">
            <span className="flex items-center gap-1 font-bold text-amber-600 dark:text-amber-500 select-none">
              <svg className="w-3.5 h-3.5 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>Gemini:</span>
            </span>
            
            <div className="flex flex-col gap-0.5 min-w-[90px]">
              <div className="flex justify-between text-[9px] font-extrabold text-zinc-500 dark:text-zinc-400 font-sans tracking-wide">
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

            <button
              onClick={onResetTokens}
              title="Refill Gemini Token Quota"
              className="p-1 hover:bg-zinc-200 dark:hover:bg-zinc-700/60 text-zinc-400 dark:text-zinc-500 hover:text-amber-600 dark:hover:text-amber-500 rounded transition-colors duration-200 cursor-pointer"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3 3 3" />
              </svg>
            </button>
          </div>
          
          {/* Desktop Segmented Radio Theme Switcher (Hidden on mobile) */}
          <div 
            className="hidden md:flex items-center bg-zinc-100 dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 p-0.5 rounded-lg select-none"
            role="radiogroup"
            aria-label="Theme Selection"
          >
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
              <Moon className={`w-3.5 h-3.5 relative z-10 ${theme === "dark" ? "text-amber-500" : "text-zinc-505 dark:text-zinc-500"}`} />
              <span className={`relative z-10 ${theme === "dark" ? "text-zinc-50" : "text-zinc-550 dark:text-zinc-400"}`}>
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

          {/* Desktop User Profile (Hidden on mobile) */}
          <button
            id="profile-dropdown-button"
            className="hidden md:block p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 hover:bg-zinc-100 dark:bg-zinc-900 dark:hover:bg-zinc-800/80 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 shadow-sm cursor-pointer custom-transition"
            aria-label="User Profile"
          >
            <User className="w-4 h-4" />
          </button>

          {/* Mobile Theme Toggle Button (Visible only on mobile) */}
          <button
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            className="md:hidden p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-550 dark:text-zinc-400 cursor-pointer"
            title="Toggle Theme"
          >
            {theme === "light" ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4 text-amber-500" />}
          </button>

          {/* Mobile Hamburger Menu Toggle Button (Visible only on mobile) */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-550 dark:text-zinc-400 cursor-pointer"
            aria-label="Toggle Menu"
          >
            {menuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Overlay */}
      <AnimatePresence>
        {menuOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.4 }}
              exit={{ opacity: 0 }}
              onClick={() => setMenuOpen(false)}
              className="fixed inset-0 top-16 z-30 bg-black md:hidden"
            />
            {/* Slide-out Panel */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 220 }}
              className="fixed right-0 top-16 bottom-0 z-30 w-full max-w-[280px] bg-white dark:bg-zinc-950 border-l border-zinc-200 dark:border-zinc-900 shadow-2xl md:hidden flex flex-col p-5 overflow-y-auto space-y-6"
            >
              {/* Navigation Links */}
              <div className="space-y-1">
                <div className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest pb-2">
                  Navigation
                </div>
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = view === tab.id || (tab.id === "landing" && view === "workspace");
                  return (
                    <button
                      key={tab.id}
                      onClick={() => {
                        setView(tab.id === "landing" ? "landing" : tab.id);
                        setMenuOpen(false);
                      }}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-colors duration-200 cursor-pointer ${
                        isActive
                          ? "bg-amber-500/10 text-amber-600 dark:bg-amber-550/20 dark:text-amber-500"
                          : "text-zinc-650 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>

              <hr className="border-zinc-200 dark:border-zinc-900" />

              {/* Gemini Token Metrics */}
              <div className="space-y-2">
                <div className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
                  Gemini API Quota
                </div>
                <div className="p-3.5 rounded-2xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-3">
                  <div className="flex justify-between text-[10px] font-bold text-zinc-650 dark:text-zinc-350">
                    <span>{totalTokensUsed.toLocaleString()} used</span>
                    <span>{pendingTokens.toLocaleString()} left</span>
                  </div>
                  <div className="w-full h-1.5 bg-zinc-200 dark:bg-zinc-800 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-500 ${
                        pendingTokens === 0 ? "bg-red-500" : "bg-emerald-550"
                      }`} 
                      style={{ width: `${Math.min(100, (totalTokensUsed / (totalTokensUsed + pendingTokens || 1)) * 100)}%` }}
                    />
                  </div>
                  <button
                    onClick={() => {
                      onResetTokens();
                      setMenuOpen(false);
                    }}
                    className="w-full py-2 bg-amber-500 hover:bg-amber-600 text-white text-[11px] font-bold rounded-xl flex items-center justify-center gap-1.5 shadow-sm shadow-amber-500/10 cursor-pointer"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3 3 3" />
                    </svg>
                    <span>Refill Gemini Quota</span>
                  </button>
                </div>
              </div>

              {/* Profile Details */}
              <div className="pt-4 mt-auto">
                <button 
                  onClick={() => setMenuOpen(false)}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-zinc-200 dark:border-zinc-800 text-zinc-650 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900 text-sm font-semibold cursor-pointer"
                >
                  <User className="w-4 h-4" />
                  <span>View Profile</span>
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </header>
  );
}
