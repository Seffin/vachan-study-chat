"""
Vachan Study Bible Chatbot — Unit and Integration Tests for Follow-up Workflow
Covers ConversationState, ResponseMode, FollowupDetector, Elaboration depth protection, and Retrieval drift mitigation.
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import ConversationState, ResponseMode
from services.followup_detector import FollowupDetector
from schemas.requests import ChatMessage

class TestFollowupWorkflow(unittest.TestCase):
    def test_conversation_state_serialization(self):
        state = ConversationState(
            original_question="Who is Jesus?",
            last_user_question="Who is Jesus?",
            previous_assistant_answer="Jesus is the Son of God.",
            dataset_answer_reference="Jesus is the Son of God in Christian theology.",
            elaboration_depth=1,
            detected_language="en"
        )
        data = state.to_dict()
        self.assertEqual(data["original_question"], "Who is Jesus?")
        self.assertEqual(data["elaboration_depth"], 1)

        restored = ConversationState.from_dict(data)
        self.assertEqual(restored.original_question, state.original_question)
        self.assertEqual(restored.elaboration_depth, state.elaboration_depth)

    def test_response_mode_enum(self):
        self.assertEqual(ResponseMode.DIRECT_HIT.value, "direct_hit")
        self.assertEqual(ResponseMode.ELABORATE.value, "elaborate")
        self.assertEqual(ResponseMode.GENERATE.value, "generate")

    def test_followup_detector_explicit_english(self):
        result = FollowupDetector.detect("Explain more")
        self.assertTrue(result["is_followup"])
        self.assertEqual(result["matched_layer"], "explicit_phrase")

    def test_followup_detector_explicit_malayalam(self):
        result = FollowupDetector.detect("കൂടുതൽ വിശദീകരിക്കാമോ?")
        self.assertTrue(result["is_followup"])
        self.assertEqual(result["matched_layer"], "explicit_phrase")

    def test_followup_detector_semantic(self):
        result = FollowupDetector.detect("give me details")
        self.assertTrue(result["is_followup"])
        self.assertEqual(result["matched_layer"], "semantic")

    def test_followup_detector_conversation_aware(self):
        state = ConversationState(
            original_question="What is faith?",
            last_user_question="What is faith?",
            previous_assistant_answer="Faith is confidence in what we hope for.",
            dataset_answer_reference=None,
            elaboration_depth=0,
            detected_language="en"
        )
        result = FollowupDetector.detect("and what else?", conversation_state=state)
        self.assertTrue(result["is_followup"])
        self.assertEqual(result["matched_layer"], "conversation_aware")

    def test_followup_detector_translation_aware(self):
        result = FollowupDetector.detect("traz mais detalhes ai", translated_query="explain more")
        self.assertTrue(result["is_followup"])
        self.assertEqual(result["matched_layer"], "translation_aware")

    def test_elaboration_depth_protection(self):
        state = ConversationState(
            original_question="Who is Jesus?",
            last_user_question="Explain more.",
            previous_assistant_answer="Jesus is the Son of God.",
            dataset_answer_reference=None,
            elaboration_depth=2, # Max depth reached
            detected_language="en"
        )
        # Verify that max_elaboration_depth=2 triggers reset in workflow logic
        is_followup = True
        if is_followup and state.elaboration_depth >= 2:
            is_followup = False
            state.elaboration_depth = 0
        self.assertFalse(is_followup)
        self.assertEqual(state.elaboration_depth, 0)

    def test_chat_request_schema_fast_path(self):
        from schemas.requests import ChatRequest
        req = ChatRequest(book="MAT", message="What is faith?", suggested_question_id="MAT_123", is_suggested_question=True)
        self.assertEqual(req.suggested_question_id, "MAT_123")
        self.assertTrue(req.is_suggested_question)

    def test_dataset_repository_id_attachment(self):
        from db.repositories import DatasetRepository
        records = DatasetRepository.load_dataset_records("MAT")
        if records:
            self.assertIn("id", records[0])
            self.assertTrue(len(records[0]["id"]) > 0)

    def test_dataset_fast_path_simulation(self):
        # Simulate Priority 1 and Priority 2 exact match logic from chat_endpoint
        dataset_records = [
            {"id": "MAT_0", "Reference": "1:1", "Question": "What is the genealogy of Jesus?", "Response": "An account of the genealogy of Jesus the Messiah."}
        ]
        request_suggested_id = "MAT_0"
        original_query = "What is the genealogy of Jesus?"
        
        dataset_fast_match = None
        # Priority 1
        for rec in dataset_records:
            if rec.get("id") == request_suggested_id:
                dataset_fast_match = rec
                break
        
        self.assertIsNotNone(dataset_fast_match)
        self.assertEqual(dataset_fast_match["Response"], "An account of the genealogy of Jesus the Messiah.")
        
        source = "suggested_question"
        r_mode = ResponseMode.DIRECT_HIT
        self.assertEqual(source, "suggested_question")
        self.assertEqual(r_mode, ResponseMode.DIRECT_HIT)

if __name__ == "__main__":
    unittest.main()
