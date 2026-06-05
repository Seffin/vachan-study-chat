"use client";

import React, { useState, useRef, useEffect } from "react";
import { 
  BookOpen, Plus, Settings, HelpCircle, MoreVertical, 
  Send, Mic, ChevronLeft, Menu, Eye, Sparkles, Check
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { 
  booksList, matthew1Content, defaultAIResponse, Section 
} from "../data/mockBible";

interface WorkspaceProps {
  selectedBook: string;
  setSelectedBook: (bookName: string) => void;
  onBackToLanding: () => void;
  onUpdateTokens?: (used: number, totalUsed: number, pending: number, reqToday: number, reqMinute: number) => void;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  suggestedQuestions: string[];
  setSuggestedQuestions: React.Dispatch<React.SetStateAction<string[]>>;
  activeHighlights: string[];
  setActiveHighlights: React.Dispatch<React.SetStateAction<string[]>>;
  selectedChapter: number;
  setSelectedChapter: React.Dispatch<React.SetStateAction<number>>;
  selectedVersion: string;
  setSelectedVersion: React.Dispatch<React.SetStateAction<string>>;
  selectedVerse: string;
  setSelectedVerse: React.Dispatch<React.SetStateAction<string>>;
  scriptureContent: Section[];
  setScriptureContent: React.Dispatch<React.SetStateAction<Section[]>>;
}

interface Message {
  id: string;
  sender: "user" | "ai";
  text: string;
  timestamp: string;
  versesHighlighted?: string[];
  isCustom?: boolean;
  isGeneralKnowledge?: boolean;
  source?: "dataset" | "ai";
}

// Helper to translate full book names into standard 3-letter USFM codes
const getBookCode = (bookName: string): string => {
  const name = bookName.trim();
  const mapping: Record<string, string> = {
    "Genesis": "GEN", "Exodus": "EXO", "Leviticus": "LEV", "Numbers": "NUM", "Deuteronomy": "DEU",
    "Joshua": "JOS", "Judges": "JDG", "Ruth": "RUT", "1 Samuel": "1SA", "2 Samuel": "2SA",
    "1 Kings": "1KI", "2 Kings": "2KI", "1 Chronicles": "1CH", "2 Chronicles": "2CH",
    "Ezra": "EZR", "Nehemiah": "NEH", "Esther": "EST", "Job": "JOB", "Psalms": "PSA",
    "Proverbs": "PRO", "Ecclesiastes": "ECC", "Song of Solomon": "SNG", "Isaiah": "ISA",
    "Jeremiah": "JER", "Lamentations": "LAM", "Ezekiel": "EZK", "Daniel": "DAN", "Hosea": "HOS",
    "Joel": "JOL", "Amos": "AMO", "Obadiah": "OBA", "Jonah": "JON", "Micah": "MIC",
    "Nahum": "NAM", "Habakkuk": "HAB", "Zephaniah": "ZEP", "Haggai": "HAG", "Zechariah": "ZEC",
    "Malachi": "MAL", "Matthew": "MAT", "Mark": "MRK", "Luke": "LUK", "John": "JHN",
    "Acts": "ACT", "Romans": "ROM", "1 Corinthians": "1CO", "2 Corinthians": "2CO",
    "Galatians": "GAL", "Ephesians": "EPH", "Philippians": "PHP", "Colossians": "COL",
    "1 Thessalonians": "1TH", "2 Thessalonians": "2TH", "1 Timothy": "1TI", "2 Timothy": "2TI",
    "Titus": "TIT", "Philemon": "PHM", "Hebrews": "HEB", "James": "JAS", "1 Peter": "1PE",
    "2 Peter": "2PE", "1 John": "1JN", "2 John": "2JN", "3 John": "3JN", "Jude": "JUD",
    "Revelation": "REV"
  };
  return mapping[name] || name.substring(0, 3).toUpperCase();
};

// Helper to get initial message based on the selected book
const getInitialMessageForBook = (bookName: string): Message => {
  if (bookName === "Matthew") {
    return {
      id: "init-1",
      sender: "ai",
      text: "Welcome to your study of **Matthew 1**. In this chapter, we explore the legal lineage of Jesus back to Abraham and David, as well as the wonderful account of His birth and Joseph's faithful response.\n\n*Select a suggested question below, or type your own question to start exploring!*",
      timestamp: "12:00 PM"
    };
  }
  return {
    id: `init-${Date.now()}`,
    sender: "ai",
    text: `Welcome to your study of **${bookName}**. You can ask questions about the text, historical context, or original language meanings below.\n\n*Select a suggested question below, or type your own question to start exploring!*`,
    timestamp: "Now"
  };
};

// Helper to get initial questions based on the selected book
const getInitialQuestionsForBook = (bookName: string): string[] => {
  if (bookName === "Matthew") {
    return [
      "What did Joseph do next?",
      "Explain verse 19 further",
      "Why is the genealogy of Jesus important in Matthew 1?"
    ];
  }
  return [
    `Overview of the book of ${bookName}`,
    `Who wrote ${bookName}?`,
    `Key theological themes in ${bookName}`
  ];
};

// Helper to get initial highlights based on the selected book
const getInitialHighlightsForBook = (bookName: string): string[] => {
  if (bookName === "Matthew") {
    return ["19"];
  }
  return [];
};

// Helper to get high-fidelity mock scripture content when backend is offline
const getMockScriptureForBook = (bookName: string, chapterNum: number = 1): Section[] => {
  if (bookName === "Matthew" && chapterNum === 1) {
    return matthew1Content;
  }
  if (bookName === "Genesis" && chapterNum === 1) {
    return [
      {
        heading: "THE CREATION OF THE WORLD",
        verses: [
          { number: 1, text: "In the beginning, God created the heavens and the earth." },
          { number: 2, text: "The earth was without form and void, and darkness was over the face of the deep. And the Spirit of God was hovering over the face of the waters." },
          { number: 3, text: "And God said, 'Let there be light,' and there was light." },
          { number: 4, text: "And God saw that the light was good. And God separated the light from the darkness." },
          { number: 5, text: "God called the light Day, and the darkness he called Night. And there was evening and there was morning, the first day." }
        ]
      }
    ];
  }
  if (bookName === "Genesis" && chapterNum === 2) {
    return [
      {
        heading: "THE SEVENTH DAY, AND THE GARDEN OF EDEN",
        verses: [
          { number: 1, text: "So the heavens and the earth were completed, and all their hosts." },
          { number: 2, text: "And by the seventh day God had completed his work that he had done, so he rested on the seventh day from all his work that he had done." },
          { number: 3, text: "And God blessed the seventh day and sanctified it, because on it he rested from all his work of creating that God had done." },
          { number: 4, text: "These are the generations of the heavens and the earth when they were created, in the day when Yahweh God made the earth and the heavens," },
          { number: 5, text: "and every shrub of the field had not yet appeared on the earth, and every plant of the field had not yet sprung up, because Yahweh God had not caused it to rain on the earth, and there was no man to work the ground." }
        ]
      }
    ];
  }
  return [
    {
      heading: `THE TEXT OF ${bookName.toUpperCase()} ${chapterNum}`,
      verses: [
        { number: 1, text: `This is the first verse of the book of ${bookName}, chapter ${chapterNum}.` },
        { number: 2, text: `This is the second verse of the book of ${bookName}, chapter ${chapterNum}, exploring theological themes.` },
        { number: 3, text: `This is the third verse of the book of ${bookName}, chapter ${chapterNum}, providing historical context.` }
      ]
    }
  ];
};

export default function Workspace({ 
  selectedBook, 
  setSelectedBook, 
  onBackToLanding,
  onUpdateTokens,
  messages,
  setMessages,
  suggestedQuestions,
  setSuggestedQuestions,
  activeHighlights,
  setActiveHighlights,
  selectedChapter,
  setSelectedChapter,
  selectedVersion,
  setSelectedVersion,
  selectedVerse,
  setSelectedVerse,
  scriptureContent,
  setScriptureContent
}: WorkspaceProps) {
  // Layout Drawers for Mobile
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);

  // Core API Integration States (kept local as they represent active transitions)
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Audio recording simulation state
  const [isRecording, setIsRecording] = useState(false);

  // Chat list auto scroll reference
  const messagesEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // 1. Reset Workspace and Chat Context on Book Switch
  useEffect(() => {
    const bookName = selectedBook;
    setSelectedChapter(1);
    setSelectedVerse("");
    
    // 1. Reset chat messages for the chosen book
    setMessages([
      getInitialMessageForBook(bookName)
    ]);
    
    // 2. Reset suggested questions
    setSuggestedQuestions(getInitialQuestionsForBook(bookName));
    
    // 3. Reset highlights
    setActiveHighlights(getInitialHighlightsForBook(bookName));
  }, [selectedBook]);

  // 2. Fetch Dynamic Scripture on Book or Chapter Change
  useEffect(() => {
    const bookName = selectedBook;
    const chapterNum = selectedChapter;

    // Fetch dynamic book scripture if available on API
    const fetchScripture = async () => {
      const apiURL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      try {
        const bookCode = getBookCode(bookName);
        console.log(`Scripture Fetch: Connecting to ${apiURL}/api/scripture/${bookCode}/${chapterNum}...`);
        const res = await fetch(`${apiURL}/api/scripture/${bookCode}/${chapterNum}`);
        if (res.ok) {
          const data = await res.json();
          if (data.verses) {
            // Check if the backend returned its generic placeholders (e.g. when API key is missing and no offline assets)
            const isPlaceholder = data.verses.length > 0 && 
              data.verses[0].text && 
              data.verses[0].text.startsWith("This is placeholder scripture context");

            if (isPlaceholder) {
              console.log(`Scripture Fetch: Detected backend placeholder, using local high-fidelity fallback for ${bookName} ${chapterNum}`);
              setScriptureContent(getMockScriptureForBook(bookName, chapterNum));
            } else {
              let structured: Section[];
              if (bookName === "Matthew" && chapterNum === 1) {
                const verses = data.verses;
                const genealogyVerses = verses.filter((v: any) => v.verse <= 17);
                const birthVerses = verses.filter((v: any) => v.verse > 17);
                
                structured = [
                  {
                    heading: "THE GENEALOGY OF JESUS CHRIST",
                    verses: genealogyVerses.map((v: any) => ({ number: v.verse, text: v.text }))
                  },
                  {
                    heading: "THE BIRTH OF JESUS CHRIST",
                    verses: birthVerses.map((v: any) => ({ number: v.verse, text: v.text }))
                  }
                ];
              } else {
                structured = [
                  {
                    heading: `THE TEXT OF ${bookName.toUpperCase()} ${chapterNum}`,
                    verses: data.verses.map((v: any) => ({ number: v.verse || v.number, text: v.text }))
                  }
                ];
              }
              setScriptureContent(structured);
              console.log(`Scripture Fetch: ${bookName} ${chapterNum} data loaded dynamically from FastAPI backend!`);
            }
            return;
          }
        }
        throw new Error("API responded without verses list");
      } catch (err) {
        console.warn(`Scripture Fetch Offline: Mapped API is currently offline. Loading high-fidelity local scripture data for ${bookName} ${chapterNum}.`, err);
        setScriptureContent(getMockScriptureForBook(bookName, chapterNum));
      }
    };
    fetchScripture();
  }, [selectedBook, selectedChapter]);

  // 📜 2. Synchronized Scripture Pane Verse Auto-Scrolling
  useEffect(() => {
    if (activeHighlights.length > 0) {
      const topVerse = activeHighlights[activeHighlights.length - 1];
      const element = document.getElementById(`verse-text-${topVerse}`);
      if (element) {
        console.log(`Scripture Scroll: Gliding view to active highlighted Verse ${topVerse}`);
        element.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [activeHighlights]);

  // 📜 3. Scroll Selected Book into View in the Scripture Navigator (Desktop & Mobile)
  useEffect(() => {
    if (!selectedBook) return;

    const timer = setTimeout(() => {
      // 1. Desktop Sidebar Scroll
      const activeDesktop = document.getElementById(`sidebar-book-${selectedBook.toLowerCase()}`);
      if (activeDesktop) {
        activeDesktop.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }

      // 2. Mobile Drawer Scroll
      if (leftOpen) {
        const activeMobile = document.getElementById(`mobile-book-${selectedBook.toLowerCase()}`);
        if (activeMobile) {
          activeMobile.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [selectedBook, leftOpen]);

  // Handle book switching
  const handleBookChange = (bookName: string) => {
    setSelectedBook(bookName);
    setLeftOpen(false);
  };

  // Handle + New Chat
  const handleNewChat = () => {
    setMessages([
      {
        id: `init-${Date.now()}`,
        sender: "ai",
        text: `Starting a fresh study session in **${selectedBook}**. What passages or verses would you like to focus on today?`,
        timestamp: "Now"
      }
    ]);
    setSuggestedQuestions(getInitialQuestionsForBook(selectedBook));
    setActiveHighlights(getInitialHighlightsForBook(selectedBook));
  };

  // 🔌 3. Robust async handleSendMessage connecting Frontend UI to live RAG API
  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    // 1. Immediately append the user's message to the state and clear input field
    const newUserMessage: Message = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages(prev => [...prev, newUserMessage]);
    setInputValue("");
    setIsLoading(true);

    const apiURL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    try {
      console.log(`API Chat Request: Sending query to ${apiURL}/api/chat...`);
      
      // Extract all previous user questions in the current chat session
      const userQueryHistory = messages
        .filter((msg) => msg.sender === "user")
        .map((msg) => msg.text);

      // 2. Make POST fetch request to backend
      const response = await fetch(`${apiURL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          book: getBookCode(selectedBook),
          message: text,
          history: userQueryHistory
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP Error Status ${response.status}`);
      }

      const data = await response.json();

      // Update parent token metrics if available in response
      if (onUpdateTokens && typeof data.total_tokens_used === "number") {
        onUpdateTokens(
          data.tokens_used || 0,
          data.total_tokens_used,
          data.pending_tokens,
          data.requests_today || 0,
          data.requests_this_minute || 0
        );
      }

      // 3. Append the AI's answer
      const newAIMessage: Message = {
        id: `ai-${Date.now()}`,
        sender: "ai",
        text: data.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        versesHighlighted: data.reference ? [data.reference.split(":")[1]] : [],
        isGeneralKnowledge: data.is_general_knowledge || false,
        source: data.source as "dataset" | "ai"
      };
      setMessages(prev => [...prev, newAIMessage]);

      // 4. Update suggested questions chips
      if (data.suggested_questions) {
        setSuggestedQuestions(data.suggested_questions);
      }

      // 5. Update active reference and scroll reader pane
      if (data.reference) {
        const verseStr = data.reference.split(":")[1];
        if (verseStr) {
          setActiveHighlights([verseStr]);
        }
      }

    } catch (err) {
      console.warn("API Connection Failed: Live backend server is currently offline. Launching dynamic mock simulator fallback.", err);
      
      // ===============================================================
      // 🔌 OFFLINE FALLBACK PIPELINE (Seamless continuation)
      // ===============================================================
      setTimeout(() => {
        const responseData = defaultAIResponse(text);
        
        const newAIMessage: Message = {
          id: `ai-${Date.now()}`,
          sender: "ai",
          text: responseData.answer + "\n\n*⚠️ Note: Mapped FastAPI RAG server is offline. Running in zero-config local backup simulator mode.*",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          versesHighlighted: responseData.verseReferences
        };
        
        setMessages(prev => [...prev, newAIMessage]);
        setSuggestedQuestions(responseData.suggestions);
        
        if (responseData.verseReferences && responseData.verseReferences.length > 0) {
          setActiveHighlights(responseData.verseReferences);
        }
      }, 1000);

    } finally {
      setIsLoading(false);
    }
  };

  // Toggle dynamic recording wave
  const toggleRecording = () => {
    if (!isRecording) {
      setIsRecording(true);
      // Simulate speaking input in 3 seconds
      setTimeout(() => {
        setIsRecording(false);
        handleSendMessage("Explain verse 19 further");
      }, 3000);
    } else {
      setIsRecording(false);
    }
  };

  // Interactive: User clicks a scripture verse in the reader
  const handleVerseClick = (verseNum: number) => {
    const verseStr = verseNum.toString();
    if (activeHighlights.includes(verseStr)) {
      setActiveHighlights(prev => prev.filter(v => v !== verseStr));
      setSelectedVerse("");
    } else {
      setActiveHighlights([verseStr]);
      setSelectedVerse(verseStr);
      setInputValue(`Explain verse ${verseStr} further in ${selectedBook} ${selectedChapter}`);
    }
  };

  // Books menu items
  const sidebarBooks = booksList;

  return (
    <div className="flex-1 flex h-full overflow-hidden relative transition-colors duration-300">
      
      {/* ========================================================= */}
      {/* 1. LEFT PANE: Scripture Navigator (Desktop & Mobile Drawer) */}
      {/* ========================================================= */}
      
      {/* Desktop view */}
      <aside 
        className="hidden md:flex flex-col w-[260px] h-full overflow-hidden shrink-0 border-r border-zinc-200 dark:border-zinc-800 bg-[#f8f8f8] dark:bg-zinc-900/60 transition-colors"
        aria-label="Scripture Navigator"
      >
        {/* Header */}
        <div className="p-4 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-2 mb-1.5">
            <BookOpen className="w-5 h-5 text-amber-600 dark:text-amber-500" />
            <h2 className="font-sans font-bold text-lg text-zinc-900 dark:text-zinc-100">Scripture Navigator</h2>
          </div>
          <p className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
            New Testament
          </p>
        </div>

        {/* Action Button */}
        <div className="p-3">
          <button 
            onClick={handleNewChat}
            id="new-chat-button"
            className="w-full py-2.5 px-4 rounded-lg bg-black text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-black dark:hover:bg-zinc-200 font-semibold text-sm flex items-center justify-center gap-2 shadow-sm custom-transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>
        </div>

        {/* Scrollable Book List */}
        <nav className="flex-1 min-h-0 overflow-y-auto px-2 py-1 space-y-1">
          <div className="px-2 py-1.5 text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
            Books
          </div>
          {sidebarBooks.map((book) => {
            const isActive = selectedBook === book.name;
            return (
              <button
                key={book.name}
                id={`sidebar-book-${book.name.toLowerCase()}`}
                onClick={() => handleBookChange(book.name)}
                className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm flex items-center justify-between transition-colors duration-200 cursor-pointer ${
                  isActive 
                    ? "bg-[#fce5c7] text-zinc-950 dark:bg-amber-950/40 dark:text-amber-500 font-bold" 
                    : "text-zinc-600 hover:bg-zinc-200/50 dark:text-zinc-450 dark:hover:bg-zinc-800/60"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <BookOpen className={`w-4 h-4 ${isActive ? "text-amber-600 dark:text-amber-500" : "text-zinc-400 dark:text-zinc-500"}`} />
                  <span className="font-sans font-semibold">{book.name}</span>
                </div>
              </button>
            );
          })}
        </nav>

        {/* Navigator Footer */}
        <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between bg-[#f8f8f8] dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400">
          <button className="flex items-center gap-1.5 text-xs hover:text-zinc-900 dark:hover:text-zinc-100 custom-transition cursor-pointer">
            <Settings className="w-4 h-4" />
            <span>Settings</span>
          </button>
          <button className="flex items-center gap-1.5 text-xs hover:text-zinc-900 dark:hover:text-zinc-100 custom-transition cursor-pointer">
            <HelpCircle className="w-4 h-4" />
            <span>Help</span>
          </button>
        </div>
      </aside>

      {/* Left Drawer for Mobile */}
      <AnimatePresence>
        {leftOpen && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.4 }}
              exit={{ opacity: 0 }}
              onClick={() => setLeftOpen(false)}
              className="fixed inset-0 z-50 bg-black md:hidden"
            />
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 220 }}
              className="fixed left-0 top-0 bottom-0 z-50 w-[270px] bg-white dark:bg-zinc-900 flex flex-col shadow-2xl md:hidden"
            >
              <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
                <div>
                  <h2 className="font-serif font-bold text-lg text-stone-900 dark:text-zinc-100">Navigator</h2>
                  <p className="text-[10px] text-stone-400 dark:text-zinc-500 uppercase tracking-widest font-bold">New Testament</p>
                </div>
                <button onClick={() => setLeftOpen(false)} className="p-2 text-stone-400 hover:text-stone-900 dark:hover:text-zinc-100">
                  <ChevronLeft className="w-5 h-5" />
                </button>
              </div>

              <div className="p-3">
                <button 
                  onClick={() => {
                    handleNewChat();
                    setLeftOpen(false);
                  }}
                  className="w-full py-2.5 rounded-xl bg-amber-500 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-sm"
                >
                  <Plus className="w-4 h-4" />
                  <span>New Chat</span>
                </button>
              </div>

              <nav className="flex-1 min-h-0 overflow-y-auto px-2 space-y-1">
                <div className="px-2 py-1 text-[10px] font-bold text-stone-400 dark:text-zinc-500 uppercase tracking-widest">
                  Books
                </div>
                {sidebarBooks.map((book) => {
                  const isActive = selectedBook === book.name;
                  return (
                    <button
                      key={book.name}
                      id={`mobile-book-${book.name.toLowerCase()}`}
                      onClick={() => handleBookChange(book.name)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg text-sm flex items-center justify-between ${
                        isActive 
                          ? "bg-amber-500/10 text-amber-600 dark:bg-amber-500/20 dark:text-amber-500 font-bold" 
                          : "text-stone-600 dark:text-zinc-400"
                      }`}
                    >
                      <span className="font-serif">{book.name}</span>
                      {isActive && <Check className="w-4 h-4 text-amber-500" />}
                    </button>
                  );
                })}
              </nav>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* ========================================================= */}
      {/* 2. MIDDLE PANE: Study Assistant (Chat Workspace)         */}
      {/* ========================================================= */}
      <main className="flex-1 flex flex-col h-full overflow-hidden min-w-0 bg-white dark:bg-zinc-950 transition-colors">
        
        {/* Header */}
        <div className="px-4 h-14 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setLeftOpen(true)}
              className="p-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 md:hidden text-stone-500 dark:text-zinc-400 hover:text-stone-900 dark:hover:text-zinc-100 cursor-pointer"
              title="Open Navigator"
            >
              <Menu className="w-4 h-4" />
            </button>
            <button
              onClick={onBackToLanding}
              className="p-1 text-stone-400 hover:text-stone-900 dark:hover:text-zinc-100 flex items-center gap-1 text-xs font-semibold uppercase tracking-wider group cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4 group-hover:-translate-x-0.5 custom-transition" />
              <span className="hidden sm:inline">Rooms</span>
            </button>
            <div className="h-4 w-px bg-stone-200 dark:bg-zinc-800 hidden sm:block mx-1" />
            <h2 className="font-sans font-bold text-stone-950 dark:text-zinc-100 text-sm sm:text-base flex items-center gap-2">
              <span>Study Assistant</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-900 text-zinc-550 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-800 font-normal">
                {selectedBook}
              </span>
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <button 
              onClick={() => setRightOpen(true)}
              className="p-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 lg:hidden text-stone-500 dark:text-zinc-400 hover:text-stone-900 dark:hover:text-zinc-100 cursor-pointer"
              title="Open Scripture Context"
            >
              <Eye className="w-4 h-4" />
            </button>
            <button className="p-1.5 text-stone-400 hover:text-stone-755 dark:hover:text-zinc-100 rounded-lg cursor-pointer">
              <MoreVertical className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Scrollable Message List */}
        <div className="flex-1 min-h-0 overflow-y-auto px-4 py-6 space-y-6">
          
          {/* Timestamp Pill */}
          <div className="flex justify-center">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-zinc-100 dark:bg-zinc-900 text-zinc-550 dark:text-zinc-400 text-[11px] font-medium border border-zinc-200/80 dark:border-zinc-800/80">
              <Sparkles className="w-3 h-3 text-amber-500" />
              <span>Today, Study Session</span>
            </div>
          </div>

          {/* Messages */}
          {messages.map((message) => {
            const isAI = message.sender === "ai";
            if (!isAI) {
              return (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className="ml-auto max-w-[85%] flex flex-col items-end gap-1"
                >
                  <div className="px-4 py-2.5 rounded-2xl bg-[#e6e6e6] dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 text-[14.5px] font-sans leading-relaxed shadow-sm">
                    {message.text}
                  </div>
                  <span className="text-[10px] text-zinc-400 dark:text-zinc-500 mr-1 select-none">
                    {message.timestamp}
                  </span>
                </motion.div>
              );
            }

            return (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="mr-auto w-full max-w-[88%] flex flex-col gap-1.5"
              >
                {/* AI Label Header */}
                <div className="flex items-center gap-2 pl-1 select-none">
                  <div className="w-5 h-5 rounded-full bg-[#fce5c7] dark:bg-amber-900/60 border border-amber-500/20 flex items-center justify-center text-[10px] font-bold text-stone-800 dark:text-amber-500">
                    AI
                  </div>
                  <span className="text-xs font-sans font-bold text-stone-700 dark:text-zinc-300">
                    Study Guide AI
                  </span>
                  <span className="text-stone-400 dark:text-zinc-500">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                      <path d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
                    </svg>
                  </span>
                </div>

                {/* Bubble Card Container */}
                <div className="p-4 rounded-xl border border-zinc-200/80 bg-zinc-50/70 dark:border-zinc-800 dark:bg-zinc-900/60 text-zinc-900 dark:text-zinc-100 text-sm sm:text-base leading-relaxed shadow-sm">
                  <div className="font-sans text-[14px] text-stone-850 dark:text-zinc-150 overflow-hidden break-words">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        p: ({ node, ...props }) => <p className="mb-3 last:mb-0" {...props} />,
                        strong: ({ node, ...props }) => <strong className="font-bold text-stone-950 dark:text-white" {...props} />,
                        em: ({ node, ...props }) => <em className="italic text-stone-600 dark:text-zinc-400" {...props} />,
                        blockquote: ({ node, ...props }) => (
                          <blockquote className="my-3 pl-3.5 border-l-4 border-zinc-800 dark:border-zinc-500 bg-white/60 dark:bg-zinc-950/40 py-2.5 pr-2.5 rounded-r-lg font-serif italic text-stone-700 dark:text-zinc-300 text-[13.5px]" {...props} />
                        ),
                        ul: ({ node, ...props }) => <ul className="list-disc pl-5 mb-3 space-y-1" {...props} />,
                        ol: ({ node, ...props }) => <ol className="list-decimal pl-5 mb-3 space-y-1" {...props} />,
                        li: ({ node, ...props }) => <li className="pl-1" {...props} />,
                        h1: ({ node, ...props }) => <h1 className="text-lg font-bold mt-4 mb-2 text-stone-950 dark:text-white" {...props} />,
                        h2: ({ node, ...props }) => <h2 className="text-base font-bold mt-4 mb-2 text-stone-950 dark:text-white" {...props} />,
                        h3: ({ node, ...props }) => <h3 className="text-sm font-bold mt-3 mb-2 text-stone-950 dark:text-white" {...props} />,
                        a: ({ node, ...props }) => <a className="text-amber-600 hover:text-amber-700 underline" {...props} />
                      }}
                    >
                      {message.text}
                    </ReactMarkdown>
                  </div>
                </div>

                <div className="flex items-center gap-3 pl-1 mt-0.5">
                  <span className="text-[10px] text-zinc-400 dark:text-zinc-500 whitespace-nowrap shrink-0">
                    {message.timestamp}
                  </span>
                  {message.source === "ai" && (
                    <div className="text-xs text-amber-600 mt-1 ml-1 flex items-center gap-1"><span>⚠️</span> AI-generated fallback response</div>
                  )}
                  {message.source === "dataset" && (
                    <div className="text-xs text-green-600 mt-1 ml-1 flex items-center gap-1"><span>✅</span> Retrieved from dataset</div>
                  )}
                </div>
              </motion.div>
            );
          })}

          {/* Glowing Typing Loader Bubble (Shown when isLoading is true) */}
          <AnimatePresence>
            {isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex gap-3 max-w-[80%] mr-auto"
              >
                <div className="w-5.5 h-5.5 rounded-full bg-[#fce5c7] dark:bg-amber-900/60 border border-amber-500/20 flex items-center justify-center text-[10px] font-bold text-stone-800 dark:text-amber-500 animate-pulse">
                  AI
                </div>
                <div className="p-4 rounded-xl border border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900 flex items-center gap-1.5 shadow-inner">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-bounce shadow-md shadow-amber-500/35" style={{ animationDelay: "0ms" }} />
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-bounce shadow-md shadow-amber-500/35" style={{ animationDelay: "150ms" }} />
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-bounce shadow-md shadow-amber-500/35" style={{ animationDelay: "300ms" }} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Follow-up Questions Chips */}
        <div className="px-4 py-2 bg-white dark:bg-zinc-950 border-t border-zinc-200 dark:border-zinc-900/60 shrink-0">
          <div className="flex flex-wrap gap-2 py-1 overflow-x-auto select-none no-scrollbar">
            {suggestedQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(q)}
                className="px-3.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-850 bg-white hover:bg-zinc-50 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-xs text-zinc-700 dark:text-zinc-350 shadow-sm hover:border-zinc-400 dark:hover:border-zinc-650 cursor-pointer whitespace-nowrap custom-transition shrink-0"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Input Area (Sticky Bottom) */}
        <div className="p-4 bg-white dark:bg-zinc-950 border-t border-zinc-200 dark:border-zinc-900 shrink-0 relative transition-colors duration-300">
          
          {/* Audio recording animation widget */}
          <AnimatePresence>
            {isRecording && (
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 15 }}
                className="absolute left-4 right-4 -top-12 h-10 px-4 rounded-xl bg-amber-500 text-white flex items-center justify-between text-xs font-semibold shadow-lg"
              >
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5 h-3">
                    <span className="w-1 bg-white rounded-full animate-bounce h-2" style={{ animationDelay: "0ms" }}></span>
                    <span className="w-1 bg-white rounded-full animate-bounce h-3" style={{ animationDelay: "150ms" }}></span>
                    <span className="w-1 bg-white rounded-full animate-bounce h-1" style={{ animationDelay: "300ms" }}></span>
                    <span className="w-1 bg-white rounded-full animate-bounce h-2.5" style={{ animationDelay: "450ms" }}></span>
                  </div>
                  <span>Listening... Try saying "Explain verse 19 further"</span>
                </div>
                <button onClick={() => setIsRecording(false)} className="underline hover:text-amber-100 cursor-pointer">
                  Cancel
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          <form 
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage(inputValue);
            }} 
            className="flex items-center gap-3"
          >
            {/* Attachment Button: Circled Plus */}
            <button
              type="button"
              className="p-1 rounded-full text-zinc-400 hover:text-zinc-650 dark:text-zinc-500 dark:hover:text-zinc-350 cursor-pointer custom-transition shrink-0"
              title="Add Context Attachment"
            >
              <div className="w-6 h-6 rounded-full border-2 border-zinc-300 dark:border-zinc-650 flex items-center justify-center font-bold">
                <Plus className="w-3.5 h-3.5" />
              </div>
            </button>

            {/* Input Box */}
            <input
              type="text"
              id="chat-input"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={selectedBook === "Matthew" ? "Ask about Matthew 1..." : `Ask about ${selectedBook}...`}
              className="flex-1 px-4 py-2.5 rounded-lg bg-[#f1f1f1] dark:bg-zinc-900 border-0 text-zinc-900 dark:text-zinc-100 placeholder-zinc-450 focus:outline-none focus:ring-1 focus:ring-zinc-300 text-sm custom-transition"
            />

            {/* Push-to-Talk Voice Button */}
            <button
              type="button"
              onClick={toggleRecording}
              id="voice-mic-button"
              className={`p-3 rounded-lg cursor-pointer custom-transition shrink-0 ${
                isRecording 
                  ? "bg-red-500 text-white shadow-red-500/20 animate-pulse" 
                  : "bg-black text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-black dark:hover:bg-zinc-200 shadow-sm"
              }`}
              title="Push to Talk Voice Input"
            >
              <Mic className="w-4 h-4" />
            </button>

            {/* Send Button */}
            {inputValue.trim() && (
              <button
                type="submit"
                id="submit-message-button"
                className="p-3 rounded-lg bg-zinc-900 text-white hover:bg-black dark:bg-zinc-100 dark:text-zinc-900 cursor-pointer custom-transition shrink-0 shadow-sm"
                title="Send Message"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </form>
        </div>
      </main>

      {/* ========================================================= */}
      {/* 3. RIGHT PANE: Scripture Context Reader                   */}
      {/* ========================================================= */}

      {/* Desktop view */}
      <aside 
        className="hidden lg:flex flex-col w-[380px] h-full overflow-hidden shrink-0 border-l border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 transition-colors"
        aria-label="Scripture Context Reader"
      >
        {/* Header */}
        <div className="px-4 h-14 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between gap-1 shrink-0">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="font-serif font-black text-base text-zinc-950 dark:text-zinc-50 truncate">
              {selectedBook}
            </span>
            <select
              value={selectedChapter}
              onChange={(e) => {
                setSelectedChapter(Number(e.target.value));
                setSelectedVerse("");
                setActiveHighlights([]);
              }}
              className="bg-transparent font-serif font-black text-base border-b border-dashed border-zinc-400 dark:border-zinc-600 focus:outline-none cursor-pointer text-amber-600 dark:text-amber-500 pr-0.5"
            >
              {(() => {
                const totalChapters = booksList.find((b) => b.name === selectedBook)?.chaptersCount || 28;
                return Array.from({ length: totalChapters }, (_, i) => i + 1).map((ch) => (
                  <option key={ch} value={ch} className="bg-white dark:bg-zinc-900 text-sm text-zinc-900 dark:text-zinc-150">
                    {ch}
                  </option>
                ));
              })()}
            </select>
            <select
              value={selectedVersion}
              onChange={(e) => setSelectedVersion(e.target.value)}
              className="text-[10px] px-1 py-0.5 rounded bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-850 font-bold uppercase tracking-wider text-zinc-550 dark:text-zinc-400 focus:outline-none cursor-pointer"
            >
              <option value="ULT" className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-150">ULT</option>
              <option value="UST" className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-150">UST</option>
              <option value="ESV" className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-150">ESV</option>
              <option value="KJV" className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-150">KJV</option>
            </select>
          </div>
          <div className="flex items-center gap-1.5">
            <select
              value={selectedVerse}
              onChange={(e) => {
                const v = e.target.value;
                setSelectedVerse(v);
                if (v) {
                  setActiveHighlights([v]);
                  setInputValue(`Explain verse ${v} further in ${selectedBook} ${selectedChapter}`);
                } else {
                  setActiveHighlights([]);
                }
              }}
              className="text-xs px-1.5 py-1 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 focus:outline-none cursor-pointer max-w-[80px] text-zinc-700 dark:text-zinc-300"
            >
              <option value="" className="bg-white dark:bg-zinc-900">Verse</option>
              {scriptureContent.flatMap(section => section.verses).map((v) => (
                <option key={v.number} value={v.number.toString()} className="bg-white dark:bg-zinc-900">
                  {v.number}
                </option>
              ))}
            </select>
            <button 
              className="p-1.5 border border-zinc-200 dark:border-zinc-800 text-zinc-550 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 rounded-lg custom-transition cursor-pointer"
              title="Display Options"
            >
              <Settings className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Scrollable Context Area */}
        <div className="flex-1 min-h-0 overflow-y-auto px-6 py-6 space-y-8 select-text">
          {scriptureContent.map((section, sIdx) => (
            <div key={sIdx} className="space-y-4">
              {/* Heading */}
              <h3 className="font-sans font-bold text-xs tracking-wider text-[#9a6e3a] dark:text-amber-500 uppercase select-none">
                {section.heading}
              </h3>
              
              {/* Verses paragraph */}
              <div className="text-[15.5px] sm:text-base leading-relaxed text-zinc-850 dark:text-zinc-200 font-serif">
                {section.verses.map((v) => {
                  const isHighlighted = activeHighlights.includes(v.number.toString());
                  return (
                    <span 
                      key={v.number}
                      onClick={() => handleVerseClick(v.number)}
                      id={`verse-text-${v.number}`}
                      className={`inline transition-all duration-200 cursor-pointer rounded px-1 py-1 mx-0.5 leading-loose ${
                        isHighlighted 
                          ? "bg-[#fdf3e2] text-zinc-950 dark:bg-amber-950/40 dark:text-zinc-100 font-medium" 
                          : "hover:bg-zinc-50 dark:hover:bg-zinc-900/60"
                      }`}
                      title="Click to study verse"
                    >
                      <sup className="text-[10px] font-sans font-bold mr-1 text-[#9a6e3a] dark:text-amber-500 select-none">
                        {v.number}
                      </sup>
                      {v.text}{" "}
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* Right Drawer for Mobile */}
      <AnimatePresence>
        {rightOpen && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.4 }}
              exit={{ opacity: 0 }}
              onClick={() => setRightOpen(false)}
              className="fixed inset-0 z-50 bg-black md:hidden"
            />
            <motion.aside
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 220 }}
              className="fixed right-0 top-0 bottom-0 z-50 w-[320px] bg-white dark:bg-zinc-900 flex flex-col shadow-2xl md:hidden"
            >
              <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between gap-1">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="font-serif font-bold text-base text-stone-900 dark:text-zinc-100 truncate">
                    {selectedBook}
                  </span>
                  <select
                    value={selectedChapter}
                    onChange={(e) => {
                      setSelectedChapter(Number(e.target.value));
                      setSelectedVerse("");
                      setActiveHighlights([]);
                    }}
                    className="bg-transparent font-serif font-bold text-base border-b border-dashed border-zinc-400 dark:border-zinc-600 focus:outline-none cursor-pointer text-amber-600 dark:text-amber-500 pr-0.5"
                  >
                    {(() => {
                      const totalChapters = booksList.find((b) => b.name === selectedBook)?.chaptersCount || 28;
                      return Array.from({ length: totalChapters }, (_, i) => i + 1).map((ch) => (
                        <option key={ch} value={ch} className="bg-white dark:bg-zinc-900 text-sm text-zinc-900 dark:text-zinc-150">
                          {ch}
                        </option>
                      ));
                    })()}
                  </select>
                  <select
                    value={selectedVersion}
                    onChange={(e) => setSelectedVersion(e.target.value)}
                    className="text-[10px] px-1 py-0.5 rounded bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 font-bold uppercase tracking-wider text-stone-650 dark:text-zinc-400 focus:outline-none cursor-pointer"
                  >
                    <option value="ULT" className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-150">ULT</option>
                    <option value="UST" className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-150">UST</option>
                    <option value="ESV" className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-150">ESV</option>
                    <option value="KJV" className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-150">KJV</option>
                  </select>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <select
                    value={selectedVerse}
                    onChange={(e) => {
                      const v = e.target.value;
                      setSelectedVerse(v);
                      if (v) {
                        setActiveHighlights([v]);
                        setInputValue(`Explain verse ${v} further in ${selectedBook} ${selectedChapter}`);
                        setRightOpen(false);
                      } else {
                        setActiveHighlights([]);
                      }
                    }}
                    className="text-xs px-1.5 py-1 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 focus:outline-none cursor-pointer max-w-[70px] text-zinc-700 dark:text-zinc-300"
                  >
                    <option value="" className="bg-white dark:bg-zinc-900">Verse</option>
                    {scriptureContent.flatMap(section => section.verses).map((v) => (
                      <option key={v.number} value={v.number.toString()} className="bg-white dark:bg-zinc-900">
                        {v.number}
                      </option>
                    ))}
                  </select>
                  <button onClick={() => setRightOpen(false)} className="p-2 text-stone-400 hover:text-stone-900 dark:hover:text-zinc-100">
                    <Eye className="w-5 h-5 text-amber-500" />
                  </button>
                </div>
              </div>

              <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-6">
                {scriptureContent.map((section, sIdx) => (
                  <div key={sIdx} className="space-y-3">
                    <h3 className="font-sans font-bold text-[11px] tracking-wider text-amber-600 dark:text-amber-500 uppercase">
                      {section.heading}
                    </h3>
                    <p className="text-sm leading-relaxed text-stone-800 dark:text-zinc-200 font-serif">
                      {section.verses.map((v) => {
                        const isHighlighted = activeHighlights.includes(v.number.toString());
                        return (
                          <span 
                            key={v.number}
                            onClick={() => {
                              handleVerseClick(v.number);
                              setRightOpen(false);
                            }}
                            className={`inline rounded px-0.5 py-0.5 mx-0.5 ${
                              isHighlighted 
                                ? "bg-amber-500/20 text-stone-950 dark:text-white border-b-2 border-amber-500/50 font-medium" 
                                : ""
                            }`}
                          >
                            <sup className="text-[9px] mr-0.5 text-amber-600 dark:text-amber-500">
                              {v.number}
                            </sup>
                            {v.text}{" "}
                          </span>
                        );
                      })}
                    </p>
                  </div>
                ))}
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

    </div>
  );
}
