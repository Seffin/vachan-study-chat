"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Users, Bookmark, Sparkles, Plus, Clock, Search, BookOpen, AlertCircle, Database } from "lucide-react";
import Navbar from "../components/Navbar";
import StudyRoom from "../components/StudyRoom";
import Workspace from "../components/Workspace";
import LoginPage from "../components/LoginPage";
import { booksList, Section } from "../data/mockBible";

export interface Message {
  id: string;
  sender: "user" | "ai";
  text: string;
  timestamp: string;
  versesHighlighted?: string[];
  isCustom?: boolean;
  isGeneralKnowledge?: boolean;
}

export default function Home() {
  // Theme state: default to light per requirements
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [mounted, setMounted] = useState(false);

  // 🔐 Auth states
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<{ username: string; user_id: string } | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  // Validate token on mount
  useEffect(() => {
    const token = localStorage.getItem("vachan-auth-token");
    if (token) {
      const apiURL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      fetch(`${apiURL}/api/auth/me`, {
        headers: { "Authorization": `Bearer ${token}` }
      }).then(res => {
        if (res.ok) return res.json();
        throw new Error("Invalid token");
      }).then(user => {
        setAuthToken(token);
        setCurrentUser(user);
      }).catch(() => {
        localStorage.removeItem("vachan-auth-token");
      }).finally(() => setAuthChecked(true));
    } else {
      setAuthChecked(true);
    }
  }, []);

  const handleLogin = (token: string, user: { username: string; user_id: string }) => {
    localStorage.setItem("vachan-auth-token", token);
    setAuthToken(token);
    setCurrentUser(user);
  };

  const handleLogout = async () => {
    if (authToken) {
      const apiURL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      try {
        await fetch(`${apiURL}/api/auth/logout`, {
          method: "POST",
          headers: { "Authorization": `Bearer ${authToken}` }
        });
      } catch (e) {}
    }
    localStorage.removeItem("vachan-auth-token");
    setAuthToken(null);
    setCurrentUser(null);
  };

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

  // View state: 'landing' (Study Room), 'workspace' (Multi-Pane), 'notes', 'groups', 'dataset_viewer'
  const [view, setView] = useState<"landing" | "workspace" | "notes" | "groups" | "dataset_viewer">("landing");

  // 📝 Lifted Workspace states to persist across tab switches
  const [workspaceMessages, setWorkspaceMessages] = useState<Message[]>([]);
  const [workspaceSuggestedQuestions, setWorkspaceSuggestedQuestions] = useState<string[]>([]);
  const [workspaceActiveHighlights, setWorkspaceActiveHighlights] = useState<string[]>([]);
  const [workspaceSelectedChapter, setWorkspaceSelectedChapter] = useState(1);
  const [workspaceSelectedVersion, setWorkspaceSelectedVersion] = useState("ULT");
  const [workspaceSelectedVerse, setWorkspaceSelectedVerse] = useState<string>("");
  const [workspaceScriptureContent, setWorkspaceScriptureContent] = useState<Section[]>([]);

  // Q&A Dataset Viewer States
  const [dataset, setDataset] = useState<Array<{Reference: string, Question: string, Response: string}>>([]);
  const [datasetSearch, setDatasetSearch] = useState("");
  const [datasetLoading, setDatasetLoading] = useState(false);
  const [datasetError, setDatasetError] = useState("");

  // Selected Bible Book & Chapter State
  const [selectedBook, setSelectedBook] = useState("Matthew");

  // Auto-fetch book Q&A dataset on view activation or book selection change
  useEffect(() => {
    if (view !== "dataset_viewer") return;
    
    const fetchDataset = async () => {
      setDatasetLoading(true);
      setDatasetError("");
      try {
        const apiURL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${apiURL}/api/dataset/${selectedBook}`);
        if (!res.ok) {
          throw new Error(`HTTP Error Status ${res.status}`);
        }
        const data = await res.json();
        setDataset(data.data || []);
      } catch (err: any) {
        console.warn("Failed to fetch book dataset", err);
        setDatasetError(err.message || "Failed to load dataset");
        setDataset([]);
      } finally {
        setDatasetLoading(false);
      }
    };
    
    fetchDataset();
  }, [selectedBook, view]);

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

  if (!authChecked) {
    return <div className="h-screen bg-stone-50 dark:bg-zinc-950 flex flex-col items-center justify-center p-4">
      <div className="w-12 h-12 bg-amber-500 rounded-xl flex items-center justify-center shadow-lg shadow-amber-500/20 mb-4 animate-pulse">
        <span className="font-serif font-bold text-white text-2xl">V</span>
      </div>
    </div>;
  }

  if (!authToken) {
    return <LoginPage onLogin={handleLogin} />;
  }

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
        currentUser={currentUser}
        onLogout={handleLogout}
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
              messages={workspaceMessages}
              setMessages={setWorkspaceMessages}
              suggestedQuestions={workspaceSuggestedQuestions}
              setSuggestedQuestions={setWorkspaceSuggestedQuestions}
              activeHighlights={workspaceActiveHighlights}
              setActiveHighlights={setWorkspaceActiveHighlights}
              selectedChapter={workspaceSelectedChapter}
              setSelectedChapter={setWorkspaceSelectedChapter}
              selectedVersion={workspaceSelectedVersion}
              setSelectedVersion={setWorkspaceSelectedVersion}
              selectedVerse={workspaceSelectedVerse}
              setSelectedVerse={setWorkspaceSelectedVerse}
              scriptureContent={workspaceScriptureContent}
              setScriptureContent={setWorkspaceScriptureContent}
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
        {/* VIEW 5: Dataset Viewer Page */}
        {view === "dataset_viewer" && (
          <div className="flex-1 overflow-y-auto w-full py-12 px-4 sm:px-6 lg:px-8 custom-transition">
            <div className="max-w-4xl mx-auto w-full space-y-8">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-stone-250 dark:border-zinc-800 pb-6">
                <div>
                  <h1 className="font-serif font-black text-3xl sm:text-4xl text-stone-900 dark:text-zinc-50 tracking-tight flex items-center gap-2">
                    <Database className="w-8 h-8 text-amber-600 dark:text-amber-500" />
                    <span>unfoldingWord Q&A Dataset</span>
                  </h1>
                  <p className="text-stone-500 dark:text-zinc-400 mt-1.5 text-sm sm:text-base">
                    Inspect the source questions and answers retrieved from Translation Questions.
                  </p>
                </div>
              </div>

              {/* Controls bar */}
              <div className="flex flex-col sm:flex-row items-center gap-4 bg-[#f8f8f8] dark:bg-zinc-900/40 p-4 rounded-2xl border border-zinc-205 dark:border-zinc-800 shadow-sm">
                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <span className="text-xs font-bold text-stone-500 dark:text-zinc-400 uppercase tracking-wider whitespace-nowrap">
                    Active Book:
                  </span>
                  <select
                    value={selectedBook}
                    onChange={(e) => setSelectedBook(e.target.value)}
                    className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl px-3 py-2 text-sm text-stone-900 dark:text-zinc-105 font-sans focus:outline-none focus:ring-1 focus:ring-amber-550 cursor-pointer min-w-[150px]"
                  >
                    {booksList.map((b) => (
                      <option key={b.name} value={b.name}>
                        {b.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="relative flex-1 w-full">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400 dark:text-zinc-550" />
                  <input
                    type="text"
                    placeholder="Search questions or responses..."
                    value={datasetSearch}
                    onChange={(e) => setDatasetSearch(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-amber-550 text-sm shadow-inner"
                  />
                </div>
              </div>

              {/* Data loading, error or cards list states */}
              {datasetLoading ? (
                <div className="grid grid-cols-1 gap-4">
                  {[1, 2, 3].map((n) => (
                    <div key={n} className="p-5 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 shadow-sm space-y-3 animate-pulse">
                      <div className="h-4 bg-zinc-200 dark:bg-zinc-800 rounded w-24"></div>
                      <div className="h-5 bg-zinc-200 dark:bg-zinc-800 rounded w-3/4"></div>
                      <div className="h-16 bg-zinc-200 dark:bg-zinc-800 rounded w-full"></div>
                    </div>
                  ))}
                </div>
              ) : datasetError ? (
                <div className="p-6 rounded-2xl border border-red-500/20 bg-red-500/5 text-red-650 dark:text-red-500 text-sm flex items-center gap-3">
                  <AlertCircle className="w-5 h-5 shrink-0" />
                  <span>{datasetError} (Verify your backend FastAPI server is running locally)</span>
                </div>
              ) : (() => {
                const filtered = dataset.filter((item) => {
                  const query = datasetSearch.toLowerCase().trim();
                  return (
                    item.Question.toLowerCase().includes(query) ||
                    item.Response.toLowerCase().includes(query) ||
                    item.Reference.toLowerCase().includes(query)
                  );
                });

                if (filtered.length === 0) {
                  return (
                    <div className="text-center py-12 text-zinc-400 dark:text-zinc-500 font-sans">
                      <Search className="w-12 h-12 mx-auto text-zinc-300 dark:text-zinc-800 mb-3" />
                      <p>No matches found in the dataset for "{datasetSearch}".</p>
                    </div>
                  );
                }

                return (
                  <div className="space-y-4">
                    <div className="text-xs font-bold text-zinc-450 dark:text-zinc-500 flex justify-between select-none">
                      <span>SHOWING {filtered.length} QUESTIONS</span>
                      <span>TOTAL {dataset.length} QUESTIONS</span>
                    </div>

                    <div className="grid grid-cols-1 gap-4">
                      {filtered.map((item, idx) => (
                        <div
                          key={idx}
                          className="p-5 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 shadow-sm space-y-3 hover:border-amber-500/40 dark:hover:border-amber-500/40 custom-transition hover:shadow-md hover:-translate-y-0.5 group"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] px-2.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-500 font-bold select-none group-hover:bg-amber-500 group-hover:text-white custom-transition">
                              {selectedBook} {item.Reference}
                            </span>
                          </div>

                          <h4 className="font-serif font-bold text-lg text-zinc-900 dark:text-zinc-100 leading-snug">
                            {item.Question}
                          </h4>

                          <p className="text-zinc-700 dark:text-zinc-300 text-sm sm:text-[14.5px] leading-relaxed font-sans bg-zinc-50 dark:bg-zinc-950/40 p-3.5 rounded-xl border border-zinc-150 dark:border-zinc-850/80">
                            {item.Response}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
