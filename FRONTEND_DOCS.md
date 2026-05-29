# 🎨 Vachan Study Bible Study Chatbot — Frontend Architecture & API Integration Docs

Welcome to the frontend engineering documentation for the **Vachan Study Bible Study Chatbot**. This document outlines the Next.js React application, detailing how states are structured, how the UI binds to those states, and how it seamlessly connects to the live FastAPI backend or heals itself using local simulation logic when offline.

---

## 📂 Frontend Directory Structure

The frontend is built using **Next.js**, styled with **Tailwind CSS v4** (including custom light/dark color palettes), and uses **Framer Motion** for elegant transitional animations.

```bash
vachan-study-bible-study-chatbot/
├── src/
│   ├── app/
│   │   ├── layout.tsx         # App layout wrapper (fonts, structure)
│   │   ├── globals.css        # Base styling, custom color variables & animations
│   │   └── page.tsx           # Main Page routing (view and theme management)
│   ├── components/
│   │   ├── Navbar.tsx         # Top premium header (theme, view toggle)
│   │   ├── StudyRoom.tsx      # Landing page for selecting study books
│   │   └── Workspace.tsx      # The main multi-pane study interface
│   └── data/
│       └── mockBible.ts       # Mock scripture structures & offline fallback dataset
├── package.json               # Package declarations (Next, Framer Motion, Lucide)
└── .env.example               # Environment template for NEXT_PUBLIC_API_URL
```

---

## 🔄 Core State Architecture

The application's states are central to the multi-pane interactivity inside `src/components/Workspace.tsx`. Here is an overview of the key state variables:

| State Variable Name | Type | Description |
| :--- | :--- | :--- |
| `messages` | `Message[]` | Keeps a history of chat bubbles `{ id, sender, text, timestamp, versesHighlighted[] }`. |
| `inputValue` | `string` | Binds directly to the text input box in the chat bar. |
| `isLoading` | `boolean` | Triggers a pulsing, bouncing bubble loader while waiting for backend APIs. |
| `activeHighlights` | `string[]` | Array of strings (e.g., `["19"]`) representing verses currently highlighted in the reader. |
| `suggestedQuestions`| `string[]` | Array of follow-up questions displayed as clickable interactive chips. |
| `scriptureContent` | `Section[]` | Holds structured scripture text loaded from the backend or the local cache. |

---

## 🔌 API Integration & Fetch Pipelines

The frontend communicates with the FastAPI backend through two critical APIs:

```mermaid
graph TD
    A[User types query / Clicks suggestion] --> B(handleSendMessage)
    B --> C{Check Server Connection}
    C -- Online --> D[POST /api/chat]
    C -- Offline --> E[Self-Healing Local Simulator]
    D --> F[Update chat bubble, highlighted verse & followups]
    E --> F
    G[Mount Workspace / Change Book] --> H[GET /api/scripture/{book}/1]
    H --> I[Populate Scripture Reading Pane]
```

### 1. Dynamic Chat Query (`handleSendMessage`)
When a user sends a message, `handleSendMessage` handles state updates, network communication, and error fallbacks:

```typescript
const handleSendMessage = async (text: string) => {
  if (!text.trim()) return;

  // 1. Immediately append the user's message to the chat view
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
    // 2. Make POST fetch request to FastAPI backend
    const response = await fetch(`${apiURL}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        book: getBookCode(selectedBook), // Translates "Matthew" to "MAT"
        message: text
      })
    });

    if (!response.ok) throw new Error(`HTTP Error Status ${response.status}`);
    const data = await response.json();

    // 3. Append the AI's answer with its exact backend response
    const newAIMessage: Message = {
      id: `ai-${Date.now()}`,
      sender: "ai",
      text: data.answer,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      versesHighlighted: data.reference ? [data.reference.split(":")[1]] : []
    };
    setMessages(prev => [...prev, newAIMessage]);

    // 4. Update the Suggested Chips dynamically
    if (data.suggested_questions) {
      setSuggestedQuestions(data.suggested_questions);
    }

    // 5. Highlight the primary scripture reference and scroll reader pane
    if (data.reference) {
      const verseStr = data.reference.split(":")[1];
      if (verseStr) setActiveHighlights([verseStr]);
    }

  } catch (err) {
    console.warn("FastAPI Offline: Starting dynamic local simulator...", err);
    
    // ===============================================================
    // 🛡️ SELF-HEALING OFFLINE FALLBACK PIPELINE
    // ===============================================================
    setTimeout(() => {
      const responseData = defaultAIResponse(text); // Fetches structured offline replies
      
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
```

### 2. Live Scripture Fetching
Upon mounting or book selection, the component pulls scripture from the backend to populate the reader:
```typescript
const res = await fetch(`${apiURL}/api/scripture/MAT/1`);
const data = await res.json();
// Structures raw verses into logical divisions (e.g. Genealogy vs Birth)
```

---

## 🎨 UI Component Bindings

### 1. Chat Workspace (Middle Pane)
* **Chat Input Area**: 
  * The text input binds to `inputValue` using `value={inputValue}` and updates via `onChange`.
  * Form submission is intercepted: hitting **Enter** or clicking **Send** triggers `handleSendMessage(inputValue)`.
* **Push-to-Talk Recording simulation**:
  * Microphone button triggers `toggleRecording()`. If active, it launches a dynamic wave animation widget and simulates voice input by sending *"Explain verse 19 further"* after 3 seconds.
* **Typing Indicator**:
  * When `isLoading` is true, an elegant pulsing dot bubble is appended using Framer Motion (`AnimatePresence`).
* **Message Bubbles**:
  * AI responses are passed through a custom paragraph and styling parser. It formats text between `**` as bold, `*` as italic, and supports scripture blockquotes (lines starting with `>`).
  * Injects the required dataset disclaimer at the foot of AI bubbles.

---

### 2. Suggested Questions Chips
Follow-up questions are rendered as small clickable buttons at the bottom of the chat pane:
```tsx
{suggestedQuestions.map((q, idx) => (
  <button key={idx} onClick={() => handleSendMessage(q)}>
    {q}
  </button>
))}
```
*Clicking any chip immediately submits that pre-filled text as an active query, offering a fluid, zero-type exploration loop.*

---

### 3. Scripture Pane & Verse Auto-Scrolling (Right Pane)
The scripture context reader displays full biblical text. It communicates bidirectionally with the active chat:

* **Synchronized Highlighting**:
  * Each rendered verse checks whether its number is listed in the `activeHighlights` array:
    ```tsx
    const isHighlighted = activeHighlights.includes(v.number.toString());
    ```
  * If true, it receives the styled blending class: `bg-[#fdf3e2] dark:bg-amber-950/40 text-zinc-950 dark:text-zinc-100 font-medium`.
* **Smooth Auto-Scrolling**:
  * A `useEffect` hook monitors the `activeHighlights` state. When it changes, it locates the active verse element on the page and glides the reading pane smoothly to focus on it:
    ```typescript
    useEffect(() => {
      if (activeHighlights.length > 0) {
        const topVerse = activeHighlights[activeHighlights.length - 1];
        const element = document.getElementById(`verse-text-${topVerse}`);
        if (element) {
          element.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    }, [activeHighlights]);
    ```
* **Interactive Verses**:
  * Users can **click directly on any verse** in the scripture reader. This action toggles its highlighting state and pre-fills the chat input box (e.g., *"Explain verse 19 further in Matthew 1"*), encouraging contextual exploration.

---

## 🛠️ Testing & Offline Environments

1. **Developing Offline**:
   * If you want to refine frontend features without launching the FastAPI server, simply run `npm run dev`. 
   * The app will notice the missing API endpoint and transition to **Local Simulator Mode** instantly. You can type any question or click suggestions to view simulated AI responses, verse highlights, and chapter data.
2. **Developing Online**:
   * Run the FastAPI backend.
   * Make sure your `.env.local` is set to `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`.
   * Start the Next.js server. The UI will pull live scripture data and invoke real-time RAG responses!
