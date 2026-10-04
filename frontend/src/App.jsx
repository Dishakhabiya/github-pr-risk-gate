import React, { useState } from "react";
import Navbar from "./components/Navbar";
import PRAnalysis from "./pages/PRAnalysis";
import RiskAnalysis from "./pages/RiskAnalysis";
import PRUnderstanding from "./pages/PRUnderstanding";
import FinalResult from "./pages/FinalResult";

import {
  analyzePR,
  getRepositoryContext,
  getQuestions,
  submitAnswers,
} from "./services/api";

export default function App() {
  const [activeTab, setActiveTab] = useState("analysis");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const [prData, setPrData] = useState(null);
  const [riskData, setRiskData] = useState(null);
  const [contextData, setContextData] = useState(null);
  const [questionData, setQuestionData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [finalResult, setFinalResult] = useState(null);

  const handleAnalyzePR = async (repo, prNumber) => {
    setLoading(true);
    setError(null);
    setSubmitError(null);
    setSubmitSuccess(false);
    setPrData(null);
    setRiskData(null);
    setContextData(null);
    setQuestionData(null);
    setAnswers({});
    setFinalResult(null);

    try {
      const prRes = await analyzePR(repo, prNumber);
      setPrData(prRes);

      setRiskData({
        pr_id: prRes.pr_id,
        repository: prRes.repository,
        title: prRes.title,
        features: prRes.features,
        risk_score: prRes.risk_score,
        risk_level: prRes.risk_level,
        threshold: prRes.threshold || 0.5,
        model_name: prRes.model_name,
      });

      try {
        const contextRes = await getRepositoryContext(repo, prNumber);
        setContextData(contextRes);

        const qRes = await getQuestions(prRes);
        setQuestionData(qRes);
      } catch (_) {
        // Context / question fetching is non-blocking — PR risk still loads
      }

      setAnswers({});
      setFinalResult(null);
    } catch (err) {
      setError(err.message || "Failed to analyze Pull Request.");
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerChange = (questionId, value) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: value,
    }));
  };

  /**
   * Build a fully-structured answer payload for each question.
   * This ensures answers can never be accidentally associated with the wrong question
   * because every answer entry carries its own question_id, question text, and category.
   */
  const buildAnswerPayload = () => {
    const questions = questionData?.questions || [];
    return questions.map((q, idx) => {
      const id = q.id !== undefined ? q.id : idx;
      return {
        question_id: String(id),
        question: q.question,
        category: q.category || "general",
        answer: answers[id] || "",
      };
    });
  };

  const handleSubmitAnswers = async () => {
    if (!prData) return;
    setSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(false);

    try {
      const result = await submitAnswers(
        prData.repository,
        prData.pr_id,
        answers,
        buildAnswerPayload()
      );
      setSubmitSuccess(true);
      setFinalResult(result);
      // Brief delay so success message is visible before navigating
      setTimeout(() => setActiveTab("result"), 800);
    } catch (err) {
      setSubmitError(err.message || "Failed to submit answers for evaluation.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setPrData(null);
    setRiskData(null);
    setContextData(null);
    setQuestionData(null);
    setAnswers({});
    setFinalResult(null);
    setSubmitError(null);
    setSubmitSuccess(false);
    setActiveTab("analysis");
  };

  return (
    <div className="app-wrapper">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentPR={prData}
      />

      <main className="main-content">
        {activeTab === "analysis" && (
          <PRAnalysis
            prData={prData}
            loading={loading}
            error={error}
            onAnalyze={handleAnalyzePR}
            onNext={() => setActiveTab("risk")}
          />
        )}

        {activeTab === "risk" && (
          <RiskAnalysis
            riskData={riskData}
            prData={prData}
            onNext={() => setActiveTab("understanding")}
          />
        )}

        {activeTab === "understanding" && (
          <PRUnderstanding
            contextData={contextData}
            questionData={questionData}
            answers={answers}
            onAnswerChange={handleAnswerChange}
            onSubmitAnswers={handleSubmitAnswers}
            submitting={submitting}
            submitError={submitError}
            submitSuccess={submitSuccess}
          />
        )}

        {activeTab === "result" && (
          <FinalResult finalResult={finalResult} onReset={handleReset} />
        )}
      </main>
    </div>
  );
}
