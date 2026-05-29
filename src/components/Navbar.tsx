"use client";

import React from "react";
import { Sun, Moon, User, Compass, FileText, Users } from "lucide-react";
import { motion } from "framer-motion";

interface NavbarProps {
  view: "landing" | "workspace" | "notes" | "groups";
  setView: (view: "landing" | "workspace" | "notes" | "groups") => void;
  theme: "light" | "dark";
  setTheme: (theme: "light" | "dark") => void;
}

export default function Navbar({ view, setView, theme, setTheme }: NavbarProps) {
  const tabs = [
    { id: "landing", label: "Study Room", icon: Compass },
    { id: "notes", label: "My Notes", icon: FileText },
    { id: "groups", label: "Groups", icon: Users },
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
