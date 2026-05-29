"use client";

import React, { useState } from "react";
import { Search, Compass, BookOpen, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { booksList, Book } from "../data/mockBible";

interface StudyRoomProps {
  onSelectBook: (bookName: string) => void;
}

export default function StudyRoom({ onSelectBook }: StudyRoomProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredBooks = booksList.filter((book) =>
    book.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const oldTestamentBooks = filteredBooks.filter((b) => b.testament === "Old");
  const newTestamentBooks = filteredBooks.filter((b) => b.testament === "New");

  // Framer motion variants
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.03 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0 }
  };

  return (
    <div className="flex-1 py-12 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto w-full transition-colors duration-300">
      
      {/* Hero Section */}
      <div className="text-center mb-12">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-amber-500/20 bg-amber-500/10 text-amber-600 dark:text-amber-500 text-xs font-semibold uppercase tracking-wider mb-4"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Interactive Scripture Companion</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="font-serif font-black text-4xl sm:text-5xl lg:text-6xl text-stone-900 dark:text-zinc-50 tracking-tight leading-tight"
          id="study-room-title"
        >
          Study Room
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-3 text-lg text-stone-500 dark:text-zinc-400 font-sans max-w-xl mx-auto"
        >
          Select a Book to Begin Your Study.
        </motion.p>

        {/* Search Bar */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="mt-8 max-w-md mx-auto relative group"
        >
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-stone-400 dark:text-zinc-500 group-focus-within:text-amber-500 dark:group-focus-within:text-amber-500 custom-transition">
            <Search className="w-5 h-5" />
          </div>
          <input
            type="text"
            id="book-filter-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter books (e.g. Matthew, Malachi)..."
            className="block w-full pl-11 pr-4 py-3.5 rounded-2xl border border-stone-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 text-stone-900 dark:text-zinc-100 placeholder-stone-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 dark:focus:border-amber-500 shadow-sm dark:shadow-inner text-base custom-transition"
          />
        </motion.div>
      </div>

      {/* Grid of Books */}
      <div className="space-y-12">
        
        {/* Old Testament */}
        {oldTestamentBooks.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
            className="space-y-4"
          >
            <div className="flex items-center gap-4">
              <span className="text-xs font-semibold tracking-widest text-amber-600 dark:text-amber-500 uppercase whitespace-nowrap">
                Old Testament
              </span>
              <div className="h-px w-full bg-gradient-to-r from-stone-200 via-stone-200/50 to-transparent dark:from-zinc-800 dark:via-zinc-800/40 dark:to-transparent" />
            </div>

            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3"
            >
              {oldTestamentBooks.map((book) => (
                <motion.button
                  key={book.name}
                  variants={itemVariants}
                  whileHover={{ y: -3, scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onSelectBook(book.name)}
                  id={`book-card-${book.name.toLowerCase().replace(/\s+/g, "-")}`}
                  className={`p-4 rounded-xl border text-center transition-all duration-200 cursor-pointer ${
                    book.available 
                      ? "border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10 dark:border-amber-500/20 dark:bg-amber-950/20 dark:hover:bg-amber-950/40 shadow-sm"
                      : "border-stone-200 hover:bg-stone-100/80 bg-white dark:border-zinc-800/80 dark:bg-zinc-900/60 dark:hover:bg-zinc-800/80"
                  }`}
                >
                  <span className="font-serif font-bold text-stone-900 dark:text-zinc-100 block text-base sm:text-lg">
                    {book.name}
                  </span>
                  <span className="text-[10px] uppercase font-semibold text-stone-400 dark:text-zinc-500 tracking-wider mt-1 block">
                    {book.chaptersCount} Chapters
                  </span>
                </motion.button>
              ))}
            </motion.div>
          </motion.div>
        )}

        {/* New Testament */}
        {newTestamentBooks.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="space-y-4"
          >
            <div className="flex items-center gap-4">
              <span className="text-xs font-semibold tracking-widest text-amber-600 dark:text-amber-500 uppercase whitespace-nowrap">
                New Testament
              </span>
              <div className="h-px w-full bg-gradient-to-r from-stone-200 via-stone-200/50 to-transparent dark:from-zinc-800 dark:via-zinc-800/40 dark:to-transparent" />
            </div>

            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3"
            >
              {newTestamentBooks.map((book) => (
                <motion.button
                  key={book.name}
                  variants={itemVariants}
                  whileHover={{ y: -3, scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onSelectBook(book.name)}
                  id={`book-card-${book.name.toLowerCase().replace(/\s+/g, "-")}`}
                  className={`p-4 rounded-xl border text-center transition-all duration-200 cursor-pointer ${
                    book.available 
                      ? "border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10 dark:border-amber-500/20 dark:bg-amber-950/20 dark:hover:bg-amber-950/40 shadow-sm"
                      : "border-stone-200 hover:bg-stone-100/80 bg-white dark:border-zinc-800/80 dark:bg-zinc-900/60 dark:hover:bg-zinc-800/80"
                  }`}
                >
                  <span className="font-serif font-bold text-stone-900 dark:text-zinc-100 block text-base sm:text-lg">
                    {book.name}
                  </span>
                  <span className="text-[10px] uppercase font-semibold text-stone-400 dark:text-zinc-500 tracking-wider mt-1 block">
                    {book.chaptersCount} Chapters
                  </span>
                </motion.button>
              ))}
            </motion.div>
          </motion.div>
        )}

        {/* Empty state */}
        {filteredBooks.length === 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center py-16 bg-white dark:bg-zinc-900/40 rounded-2xl border border-dashed border-stone-200 dark:border-zinc-800"
          >
            <BookOpen className="w-12 h-12 text-stone-300 dark:text-zinc-700 mx-auto mb-4" />
            <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-zinc-100">No books found</h3>
            <p className="text-stone-400 dark:text-zinc-500 mt-1 max-w-xs mx-auto text-sm">
              We couldn't find any scripture book matching "{searchQuery}". Try searching for another.
            </p>
          </motion.div>
        )}
      </div>
    </div>
  );
}
