"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Users, Bookmark, Sparkles, Plus, Clock, Search, BookOpen, AlertCircle } from "lucide-react";
import Navbar from "../components/Navbar";
import StudyRoom from "../components/StudyRoom";
import Workspace from "../components/Workspace";

export default function Home() {
  // Theme state: default to light per requirements
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [mounted, setMounted] = useState(false);

  // 📊 Token tracking & Gemini free tier states
  const [totalTokensUsed, setTotalTokensUsed] = useState<number>(0);
  const [pendingTokens, setPendingTokens] = useState<number>(1000000);
  const [tokenLimit, setTokenLimit] = useState<number>(1000000);
  const [requestsToday, setRequestsToday] = useState<number>(0);
  const [requestsThisMinute, setRequestsThisMinute] = useState<number>(0);

  // Fetch token allocation status on app mount
  useEffect(() => {
    const fetchTokens = async () => {
      try {
        const apiURL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${apiURL}/api/tokens`);
        if (res.ok) {
          const data = await res.json();
          setTotalTokensUsed(data.total_tokens_used);
          setPendingTokens(data.pending_tokens);
          setTokenLimit(data.limit);
          setRequestsToday(data.requests_today);
          setRequestsThisMinute(data.requests_this_minute);
        }
      } catch (err) {
        console.warn("Failed to fetch initial token values", err);
      }
    };
    fetchTokens();
  }, []);

  // Post reset request to backend to refresh quotas
  const handleResetTokens = async () => {
    try {
      const apiURL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiURL}/api/tokens/reset`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setTotalTokensUsed(data.total_tokens_used);
        setPendingTokens(data.pending_tokens);
        setTokenLimit(data.limit);
        setRequestsToday(data.requests_today);
        setRequestsThisMinute(data.requests_this_minute);
      }
    } catch (err) {
      console.warn("Failed to reset token values", err);
    }
  };

  // Callback to update current state from child send actions
  const handleUpdateTokens = (used: number, totalUsed: number, pending: number, reqToday: number, reqMinute: number) => {
    setTotalTokensUsed(totalUsed);
    setPendingTokens(pending);
    setRequestsToday(reqToday);
    setRequestsThisMinute(reqMinute);
  };

  // View state: 'landing' (Study Room), 'workspace' (Multi-Pane), 'notes', 'groups'
  const [view, setView] = useState<"landing" | "workspace" | "notes" | "groups">("landing");

  // Selected Bible Book & Chapter State
  const [selectedBook, setSelectedBook] = useState("Matthew");

  // Notes and group items states for richer features
  const [notes, setNotes] = useState<Array<{id: string, title: string, content: string, date: string, book: string}>>([
    {
      id: "note-1",
      title: "Integrity in Matthew 1:19",
      content: "Joseph's righteousness (dikaios) is expressed through mercy, not just strict legal observance. Resolving to divorce Mary privately is a stunning display of grace.",
      date: "May 25, 2026",
      book: "Matthew"
    },
    {
      id: "note-2",
      title: "Genealogy Numbers",
      content: "Matthew counts three sets of fourteen generations (v. 17). 14 is the numerical value of 'David' in Hebrew (D-V-D = 4+6+4). Shows royal emphasis.",
      date: "May 24, 2026",
      book: "Matthew"
    }
  ]);
  const [newNoteTitle, setNewNoteTitle] = useState("");
  const [newNoteContent, setNewNoteContent] = useState("");

  // Sync theme with local storage & document element
  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem("vachan-study-theme") as "light" | "dark" | null;
      if (savedTheme) {
        setTheme(savedTheme);
      } else {
        // Default to premium Light Mode per requirements
        setTheme("light");
      }
    } catch (e) {
      console.warn("localStorage is not accessible:", e);
      setTheme("light");
    }
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
      root.style.colorScheme = "dark";
    } else {
      root.classList.remove("dark");
      root.style.colorScheme = "light";
    }
    try {
      localStorage.setItem("vachan-study-theme", theme);
    } catch (e) {
      console.warn("localStorage is not accessible:", e);
    }
  }, [theme, mounted]);

  const toggleTheme = () => {
    setTheme(prev => (prev === "light" ? "dark" : "light"));
  };

  const handleSelectBook = (bookName: string) => {
    setSelectedBook(bookName);
    setView("workspace");
  };

  const handleAddNote = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNoteTitle.trim() || !newNoteContent.trim()) return;

    const newNote = {
      id: `note-${Date.now()}`,
      title: newNoteTitle,
      content: newNoteContent,
      date: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
      book: selectedBook
    };

    setNotes([newNote, ...notes]);
    setNewNoteTitle("");
    setNewNoteContent("");
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden transition-colors duration-300">
      
      {/* Top Premium Navbar */}
      <Navbar 
        view={view} 
        setView={setView} 
        theme={theme} 
        setTheme={setTheme} 
        totalTokensUsed={totalTokensUsed}
        pendingTokens={pendingTokens}
        tokenLimit={tokenLimit}
        requestsToday={requestsToday}
        requestsThisMinute={requestsThisMinute}
        onResetTokens={handleResetTokens}
      />

      {/* Main Content Areas with smooth routing transitions */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* VIEW 1: Study Room Landing Page */}
        {view === "landing" && (
          <div className="flex-1 flex flex-col overflow-y-auto custom-transition">
            <StudyRoom onSelectBook={handleSelectBook} />
          </div>
        )}

        {/* VIEW 2: Multi-Pane Workspace */}
        {view === "workspace" && (
          <div className="flex-1 flex flex-col h-full overflow-hidden custom-transition">
            <Workspace 
              selectedBook={selectedBook} 
              setSelectedBook={setSelectedBook}
              onBackToLanding={() => setView("landing")}
              onUpdateTokens={handleUpdateTokens}
            />
          </div>
        )}

        {/* VIEW 3: My Notes Page */}
        {view === "notes" && (
          <div className="flex-1 overflow-y-auto w-full py-12 px-4 sm:px-6 lg:px-8 custom-transition">
            <div className="max-w-4xl mx-auto w-full space-y-8">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-stone-250 dark:border-zinc-800 pb-6">
              <div>
                <h1 className="font-serif font-black text-3xl sm:text-4xl text-stone-900 dark:text-zinc-50 tracking-tight">
                  My Study Notes
                </h1>
                <p className="text-stone-500 dark:text-zinc-400 mt-1.5 text-sm sm:text-base">
                  Review and capture theological reflections during your scripture sessions.
                </p>
              </div>
              
              <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full border border-amber-500/20 bg-amber-500/10 text-amber-600 dark:text-amber-500 self-start">
                <Bookmark className="w-3.5 h-3.5" />
                <span>{notes.length} Reflections</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              
              {/* Note creation form */}
              <div className="md:col-span-1">
                <form onSubmit={handleAddNote} className="p-5 rounded-2xl border border-stone-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4 shadow-sm">
                  <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-zinc-100 flex items-center gap-2">
                    <Plus className="w-4 h-4 text-amber-500" />
                    <span>Add Reflection</span>
                  </h3>
                  
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-stone-400 dark:text-zinc-500 uppercase tracking-wider block">
                      Title
                    </label>
                    <input
                      type="text"
                      placeholder="E.g. Genealogy Secrets..."
                      value={newNoteTitle}
                      onChange={(e) => setNewNoteTitle(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl border border-stone-200 dark:border-zinc-800 bg-stone-50 dark:bg-zinc-950 text-stone-900 dark:text-zinc-100 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-amber-500 text-sm"
                      required
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-stone-400 dark:text-zinc-500 uppercase tracking-wider block">
                      Reflection Text
                    </label>
                    <textarea
                      placeholder="Write down context insights or word meanings..."
                      rows={4}
                      value={newNoteContent}
                      onChange={(e) => setNewNoteContent(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl border border-stone-200 dark:border-zinc-800 bg-stone-50 dark:bg-zinc-950 text-stone-900 dark:text-zinc-100 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-amber-500 text-sm"
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-semibold text-xs shadow-md shadow-amber-500/10 custom-transition cursor-pointer"
                  >
                    Save Reflection
                  </button>
                </form>
              </div>

              {/* Notes List */}
              <div className="md:col-span-2 space-y-4">
                {notes.map((note) => (
                  <div
                    key={note.id}
                    className="p-5 rounded-2xl border border-stone-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 shadow-sm space-y-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <h4 className="font-serif font-bold text-lg text-stone-900 dark:text-zinc-100">
                        {note.title}
                      </h4>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-stone-100 dark:bg-zinc-800 border border-stone-200 dark:border-zinc-700 text-stone-500 dark:text-zinc-400 font-semibold select-none">
                        {note.book}
                      </span>
                    </div>

                    <p className="text-stone-700 dark:text-zinc-300 text-sm sm:text-base leading-relaxed font-sans">
                      {note.content}
                    </p>

                    <div className="flex items-center gap-1.5 text-[10px] text-stone-400 dark:text-zinc-500 font-semibold select-none">
                      <Clock className="w-3.5 h-3.5 text-stone-300 dark:text-zinc-650" />
                      <span>Captured on {note.date}</span>
                    </div>
                  </div>
                ))}
              </div>

            </div>
            </div>
            </div>
        )}

        {/* VIEW 4: Study Groups Page */}
        {view === "groups" && (
          <div className="flex-1 overflow-y-auto w-full py-12 px-4 sm:px-6 lg:px-8 custom-transition">
            <div className="max-w-4xl mx-auto w-full space-y-8">
            <div className="border-b border-stone-250 dark:border-zinc-800 pb-6">
              <h1 className="font-serif font-black text-3xl sm:text-4xl text-stone-900 dark:text-zinc-50 tracking-tight">
                Study Groups
              </h1>
              <p className="text-stone-500 dark:text-zinc-400 mt-1.5 text-sm sm:text-base">
                Collaborate and read scriptures with friends, scholars, and church communities.
              </p>
            </div>

            {/* Group cards grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Group 1 */}
              <div className="p-6 rounded-2xl border border-stone-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm space-y-4">
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <h3 className="font-serif font-bold text-xl text-stone-900 dark:text-zinc-100">
                      Matthew Covenant Study
                    </h3>
                    <p className="text-stone-400 dark:text-zinc-500 text-xs font-semibold mt-0.5">
                      Founded by Pastor Dave • 12 Active Members
                    </p>
                  </div>
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-500 font-bold tracking-wide select-none">
                    Active
                  </span>
                </div>

                <p className="text-stone-600 dark:text-zinc-350 text-sm leading-relaxed">
                  Reading through the gospel of Matthew synchronously using the unfoldingWord translations. Currently examining Chapter 1.
                </p>

                <div className="pt-2 flex justify-between items-center">
                  <div className="flex -space-x-2 overflow-hidden">
                    <div className="inline-block h-7 w-7 rounded-full bg-amber-500 ring-2 ring-white dark:ring-zinc-900 flex items-center justify-center text-[10px] text-white font-bold">JD</div>
                    <div className="inline-block h-7 w-7 rounded-full bg-blue-500 ring-2 ring-white dark:ring-zinc-900 flex items-center justify-center text-[10px] text-white font-bold">AK</div>
                    <div className="inline-block h-7 w-7 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-zinc-900 flex items-center justify-center text-[10px] text-white font-bold">MR</div>
                    <div className="inline-block h-7 w-7 rounded-full bg-stone-300 ring-2 ring-white dark:ring-zinc-900 flex items-center justify-center text-[10px] text-stone-700 font-bold">+9</div>
                  </div>

                  <button 
                    onClick={() => handleSelectBook("Matthew")}
                    className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-semibold text-xs custom-transition shadow-sm shadow-amber-500/10 cursor-pointer"
                  >
                    Join Session
                  </button>
                </div>
              </div>

              {/* Group 2 */}
              <div className="p-6 rounded-2xl border border-stone-250 dark:border-zinc-800 bg-stone-100/50 dark:bg-zinc-900/40 shadow-sm space-y-4">
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <h3 className="font-serif font-bold text-xl text-stone-800 dark:text-zinc-350">
                      Greek Word Studies
                    </h3>
                    <p className="text-stone-400 dark:text-zinc-500 text-xs font-semibold mt-0.5">
                      Founded by Prof. Helen • 28 Active Members
                    </p>
                  </div>
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-stone-200 dark:bg-zinc-800 border border-stone-300 dark:border-zinc-700 text-stone-500 dark:text-zinc-400 font-bold tracking-wide select-none">
                    Upcoming
                  </span>
                </div>

                <p className="text-stone-500 dark:text-zinc-400 text-sm leading-relaxed">
                  Analyzing original Greek structures (e.g. dikaios in v. 19, logos in John 1). Focuses on vocabulary depth, translations, and cross-references.
                </p>

                <div className="pt-2 flex justify-between items-center">
                  <div className="flex -space-x-2 overflow-hidden">
                    <div className="inline-block h-7 w-7 rounded-full bg-purple-500 ring-2 ring-white dark:ring-zinc-900 flex items-center justify-center text-[10px] text-white font-bold">HS</div>
                    <div className="inline-block h-7 w-7 rounded-full bg-rose-500 ring-2 ring-white dark:ring-zinc-900 flex items-center justify-center text-[10px] text-white font-bold">TN</div>
                    <div className="inline-block h-7 w-7 rounded-full bg-stone-300 ring-2 ring-white dark:ring-zinc-900 flex items-center justify-center text-[10px] text-stone-700 font-bold">+26</div>
                  </div>

                  <button 
                    className="px-4 py-2 rounded-xl border border-stone-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 hover:bg-stone-50 dark:hover:bg-zinc-800 text-stone-600 dark:text-zinc-300 font-semibold text-xs custom-transition cursor-pointer"
                  >
                    Remind Me
                  </button>
                </div>
              </div>

            </div>

            {/* Group announcement alert */}
            <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-serif font-bold text-stone-900 dark:text-zinc-100 text-sm">
                  New Collaborative Feature Coming Soon
                </h4>
                <p className="text-stone-500 dark:text-zinc-400 text-xs mt-1 leading-relaxed">
                  Vachan Study will soon support real-time study rooms where users can highlight, read, and cross-examine unfoldingWord manuscripts simultaneously with voice chat rooms.
                </p>
              </div>
            </div>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
