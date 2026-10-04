import os
import json
import logging
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
import openai

logger = logging.getLogger(__name__)

class AnswerEvaluation(BaseModel):
    question_id: str
    score: float
    correct: bool
    feedback: str
    reason: str

class EvaluationResult(BaseModel):
    evaluations: List[AnswerEvaluation]
    understanding_score: float
    has_understood: bool

class Evaluator:
    """
    US-13: LLM Evaluation of Developer Answers
    """
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def evaluate_answer(self, question: str, category: str, answer: str, context: str, question_id: str) -> AnswerEvaluation:
        if not answer or not answer.strip():
            return AnswerEvaluation(
                question_id=question_id,
                score=0.0,
                correct=False,
                feedback="No answer provided.",
                reason="The developer left the answer blank."
            )
            
        if not self.client:
            logger.warning("OPENAI_API_KEY is not set. Using heuristic evaluation fallback.")
            return self._heuristic_evaluation(question, category, answer, question_id)

        prompt = f"""
You are an expert technical evaluator assessing a developer's understanding of their Pull Request.
Evaluate the developer's answer to the question based on the provided repository context.

Question ({category}): {question}
Developer's Answer: {answer}

Repository Context:
{context[:2000]}

Respond strictly in valid JSON format matching this schema:
{{
    "score": <float between 0.0 and 1.0>,
    "correct": <boolean>,
    "feedback": "<string: brief feedback for the developer>",
    "reason": "<string: internal reasoning for the score>"
}}
"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are a technical PR reviewer."},
                          {"role": "user", "content": prompt}],
                response_format={ "type": "json_object" },
                temperature=0.0
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            return AnswerEvaluation(
                question_id=question_id,
                score=float(parsed.get("score", 0.0)),
                correct=bool(parsed.get("correct", False)),
                feedback=str(parsed.get("feedback", "")),
                reason=str(parsed.get("reason", ""))
            )
        except Exception as e:
            logger.error(f"LLM Evaluation failed: {e}")
            return self._heuristic_evaluation(question, category, answer, question_id)

    def _heuristic_evaluation(self, question: str, category: str, answer: str, question_id: str) -> AnswerEvaluation:
        # Fallback if LLM fails or is unconfigured
        answer_len = len(answer.strip())
        if answer_len > 20:
            score = 0.8
            correct = True
            feedback = "Looks like a reasonable technical explanation (fallback mode)."
            reason = "Answer length exceeds heuristic threshold."
        else:
            score = 0.2
            correct = False
            feedback = "Answer is too short to demonstrate understanding (fallback mode)."
            reason = "Answer length below heuristic threshold."
            
        return AnswerEvaluation(
            question_id=question_id,
            score=score,
            correct=correct,
            feedback=feedback,
            reason=reason
        )

    def evaluate_all(self, answers_payload: List[Dict[str, str]], context_chunks: List[Dict[str, Any]]) -> EvaluationResult:
        """
        US-14: Understanding Score
        """
        combined_context = "\n".join([c.get("content", "") for c in context_chunks])
        
        evaluations = []
        for ans in answers_payload:
            q_id = ans.get("question_id", "")
            q_text = ans.get("question", "")
            cat = ans.get("category", "")
            ans_text = ans.get("answer", "")
            
            eval_result = self.evaluate_answer(q_text, cat, ans_text, combined_context, q_id)
            evaluations.append(eval_result)
            
        if not evaluations:
            return EvaluationResult(evaluations=[], understanding_score=0.0, has_understood=False)
            
        avg_score = sum(e.score for e in evaluations) / len(evaluations)
        has_understood = avg_score >= 0.6
        
        return EvaluationResult(
            evaluations=evaluations,
            understanding_score=avg_score,
            has_understood=has_understood
        )

class DecisionEngine:
    """
    US-15: PASS/BLOCK Merge Decision
    """
    @staticmethod
    def make_decision(risk_level: str, understanding_score: float) -> Tuple[str, List[str]]:
        reasons = []
        if understanding_score < 0.5:
            reasons.append(f"Developer demonstrated insufficient understanding (score: {understanding_score:.2f}).")
            return "BLOCK", reasons
            
        if risk_level.upper() == "HIGH" and understanding_score < 0.8:
            reasons.append(f"High risk PR requires a high understanding score (>= 0.8), but got {understanding_score:.2f}.")
            return "BLOCK", reasons
            
        reasons.append(f"PR risk is {risk_level} and developer understanding is acceptable ({understanding_score:.2f}).")
        return "PASS", reasons
