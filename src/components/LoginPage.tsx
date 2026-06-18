'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface LoginPageProps {
  onLogin: (token: string, user: { username: string; user_id: string }) => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!username) {
      setError('Username is required');
      return;
    }

    if (!password) {
      setError('Password is required');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    if (!isLogin && !email) {
      setError('Email is required for registration');
      return;
    }

    setIsLoading(true);

    try {
      const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
      const body = isLogin 
        ? { username, password } 
        : { username, email, password };

      // In tests NEXT_PUBLIC_API_URL might be undefined, fallback to ''
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
      
      const res = await fetch(`${baseUrl}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail?.error || data.detail || data.error || 'Authentication failed');
      }

      if (isLogin) {
        // Success login
        if (data.access_token) {
          onLogin(data.access_token, data.user);
        }
      } else {
        // Success register -> switch to login
        setIsLogin(true);
        setPassword('');
        setError('Registration successful. Please sign in.');
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-stone-50 dark:bg-zinc-950 flex flex-col items-center justify-center p-4">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="w-full max-w-md"
      >
        {/* Logo Header */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 bg-amber-500 rounded-xl flex items-center justify-center shadow-lg shadow-amber-500/20 mb-4 relative overflow-hidden">
             <span className="font-serif font-bold text-white text-2xl relative z-10">V</span>
             <motion.div 
                animate={{ scale: [1, 1.2, 1] }} 
                transition={{ duration: 2, repeat: Infinity }}
                className="absolute inset-0 bg-gradient-to-tr from-amber-600 to-amber-400 opacity-50"
             />
          </div>
          <h1 className="text-2xl font-serif font-black text-stone-900 dark:text-zinc-50 tracking-tight">
            Vachan Study
          </h1>
          <p className="text-stone-500 dark:text-zinc-400 text-sm mt-1">
            Logos Bible Study Chatbot
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border border-stone-200 dark:border-zinc-800 rounded-2xl shadow-xl p-8">
          <h2 className="text-xl font-serif font-bold text-stone-900 dark:text-zinc-50 mb-2">
            {isLogin ? '📖 Welcome Back' : '✨ Create Account'}
          </h2>
          <p className="text-stone-500 dark:text-zinc-400 text-sm mb-6">
            {isLogin ? 'Sign in to continue your study journey' : 'Join to explore the scriptures'}
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <AnimatePresence mode="wait">
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className={`p-3 rounded-xl text-sm ${error.includes('successful') ? 'bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20'}`}
                >
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            <div>
              <label htmlFor="username" className="block text-xs font-bold text-stone-700 dark:text-zinc-300 uppercase tracking-wider mb-1">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-stone-50 dark:bg-zinc-950 border border-stone-200 dark:border-zinc-800 rounded-xl px-4 py-3 text-stone-900 dark:text-zinc-50 placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all"
                placeholder="Enter your username"
                disabled={isLoading}
              />
            </div>

            <AnimatePresence>
              {!isLogin && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <label className="block text-xs font-bold text-stone-700 dark:text-zinc-300 uppercase tracking-wider mb-1 mt-4">
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-stone-50 dark:bg-zinc-950 border border-stone-200 dark:border-zinc-800 rounded-xl px-4 py-3 text-stone-900 dark:text-zinc-50 placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all"
                    placeholder="Enter your email"
                    disabled={isLoading}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            <div>
              <label htmlFor="password" className="block text-xs font-bold text-stone-700 dark:text-zinc-300 uppercase tracking-wider mb-1 mt-4">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-stone-50 dark:bg-zinc-950 border border-stone-200 dark:border-zinc-800 rounded-xl px-4 py-3 text-stone-900 dark:text-zinc-50 placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-500/50 transition-all"
                placeholder="••••••••"
                disabled={isLoading}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-white font-bold rounded-xl px-4 py-3 shadow-md shadow-amber-500/20 transition-all disabled:opacity-70 flex items-center justify-center mt-6"
            >
              {isLoading ? (
                <span className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  {isLogin ? 'Signing In...' : 'Creating Account...'}
                </span>
              ) : (
                isLogin ? 'Sign In' : 'Sign Up'
              )}
            </button>
          </form>

          {/* Toggle Mode */}
          <div className="mt-6 text-center text-sm text-stone-500 dark:text-zinc-400">
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <button
              type="button"
              onClick={() => {
                setIsLogin(!isLogin);
                setError('');
              }}
              className="font-bold text-amber-600 dark:text-amber-500 hover:underline focus:outline-none"
            >
              {isLogin ? 'Sign up →' : 'Sign in →'}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
