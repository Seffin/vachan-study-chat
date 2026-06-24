"""
Vachan Study Bible Chatbot — Follow-Up Detection Service
Provides multilingual, 4-layer follow-up detection to determine elaboration intent.
"""

import re
from typing import Dict, Any, Optional, List
from app.models import ConversationState
from schemas.requests import ChatMessage

class FollowupDetector:
    # Layer 1: Explicit dictionaries (English/Malayalam as initial examples only)
    EXPLICIT_PHRASES = {
        "en": ["explain more", "tell me more", "elaborate", "give me more details", "more details", "explain in detail", "expand on that", "what does that mean", "why", "how", "details", "more"],
        "ml": ["കൂടുതൽ വിശദീകരിക്കാമോ?", "വിശദീകരിക്കൂ", "കൂടുതൽ പറയൂ", "വിശദമാക്കാമോ", "കൂടുതൽ വിശദീകരിക്കുക", "വിശദീകരിക്കാമോ"],
    }

    # Layer 2: Semantic fallback patterns / short contextual queries across supported languages
    SEMANTIC_KEYWORDS = [
        "explain", "elaborate", "details", "more", "why", "how", "what does", "expand",
        "വിശദീകരിക്കാമോ", "വിശദീകരിക്കൂ", "കൂടുതൽ"
    ]

    @classmethod
    def detect(
        cls,
        original_query: str,
        translated_query: Optional[str] = None,
        conversation_state: Optional[ConversationState] = None,
        history: Optional[List[ChatMessage]] = None,
        detected_language: str = "en"
    ) -> Dict[str, Any]:
        """
        Evaluates query using a 4-layer detection approach:
        1. Explicit Follow-Up Phrase Detection
        2. Semantic Follow-Up Detection
        3. Conversation-Aware Detection
        4. Translation-Aware Detection (evaluating translated query if Phase 1 is borderline)
        """
        query_clean = original_query.lower().strip()
        
        # Output contract defaults
        result = {
            "is_followup": False,
            "intent": "none",
            "confidence": 0.0,
            "matched_layer": "none",
            "detected_language": detected_language,
            "requires_elaboration": False
        }

        if not query_clean:
            return result

        # ── Layer 1: Explicit Follow-Up Phrase Detection ──
        for lang, phrases in cls.EXPLICIT_PHRASES.items():
            if any(query_clean == p.lower() or query_clean.rstrip("?.!") == p.lower().rstrip("?.!") for p in phrases):
                result.update({
                    "is_followup": True,
                    "intent": "elaborate",
                    "confidence": 0.95,
                    "matched_layer": "explicit_phrase",
                    "requires_elaboration": True
                })
                print(f"FollowupDetector: Matched Layer 1 (Explicit Phrase) -> {result}", flush=True)
                return result

        # ── Layer 2: Semantic Follow-Up Detection ──
        # Detect short contextual queries (e.g. <= 6 words) containing elaboration semantics
        word_count = len(query_clean.split())
        if word_count <= 6 and any(keyword in query_clean for keyword in cls.SEMANTIC_KEYWORDS):
            result.update({
                "is_followup": True,
                "intent": "elaborate",
                "confidence": 0.85,
                "matched_layer": "semantic",
                "requires_elaboration": True
            })
            print(f"FollowupDetector: Matched Layer 2 (Semantic) -> {result}", flush=True)
            return result

        # ── Layer 3: Conversation-Aware Detection ──
        # If the query is short (<= 8 words) and there is recent conversation context / last_user_question
        has_active_context = (conversation_state and conversation_state.last_user_question) or (history and len(history) > 0)
        if word_count <= 8 and has_active_context:
            # Check if query references previous context or is a short continuation, rather than a standalone Bible question
            continuation_keywords = ["and", "else", "what about", "mean", "example", "why", "how", "clarify", "referring", "he", "she", "they", "this", "that", "detalhes"]
            # Treat as continuation if very short (<= 3 words) or contains continuation keywords
            if word_count <= 3 or any(k in query_clean.split() or f" {k} " in f" {query_clean} " for k in continuation_keywords):
                result.update({
                    "is_followup": True,
                    "intent": "elaborate",
                    "confidence": 0.75, # Borderline/moderate confidence
                    "matched_layer": "conversation_aware",
                    "requires_elaboration": True
                })
                print(f"FollowupDetector: Matched Layer 3 (Conversation-Aware) -> {result}", flush=True)
            # Do not return immediately if confidence is borderline (< 0.80), allow Layer 4 enhancement check

        # ── Layer 4: Translation-Aware Detection ──
        # Run when Phase 1 confidence is borderline or missed, and translated query is available
        if translated_query and translated_query != original_query:
            t_clean = translated_query.lower().strip()
            t_words = len(t_clean.split())
            
            # Check explicit and semantic matches on translated query
            if any(t_clean == p.lower() or t_clean.rstrip("?.!") == p.lower().rstrip("?.!") for p in cls.EXPLICIT_PHRASES["en"]):
                result.update({
                    "is_followup": True,
                    "intent": "elaborate",
                    "confidence": 0.90,
                    "matched_layer": "translation_aware",
                    "requires_elaboration": True
                })
                print(f"FollowupDetector: Matched Layer 4 (Translation-Aware Explicit) -> {result}", flush=True)
                return result

            if t_words <= 6 and any(keyword in t_clean for keyword in cls.SEMANTIC_KEYWORDS):
                result.update({
                    "is_followup": True,
                    "intent": "elaborate",
                    "confidence": 0.85,
                    "matched_layer": "translation_aware",
                    "requires_elaboration": True
                })
                print(f"FollowupDetector: Matched Layer 4 (Translation-Aware Semantic) -> {result}", flush=True)
                return result

        print(f"FollowupDetector: Final result -> {result}", flush=True)
        return result
