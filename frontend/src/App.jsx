import React, { useState } from "react";
import Navbar from "./components/Navbar";
import PRAnalysis from "./pages/PRAnalysis";
import RiskAnalysis from "./pages/RiskAnalysis";
import PRUnderstanding from "./pages/PRUnderstanding";
import FinalResult from "./pages/FinalResult";

import {
  analyzePR,
  getRiskPrediction,
  getRepositoryContext,
  getQuestions,
  submitAnswers,
} from "./services/api";

export default function App() {
  const [activeTab, setActiveTab] = useState("analysis");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const [prData, setPrData] = useState(null);
  const [riskData, setRiskData] = useState(null);
  const [contextData, setContextData] = useState(null);
  const [questionData, setQuestionData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [finalResult, setFinalResult] = useState(null);

  const handleAnalyzePR = async (repo, prNumber) => {
    setLoading(true);
    setError(null);
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

        const qRes = await getQuestions(repo, prNumber);
        setQuestionData(qRes);
      } catch (_) {
        // Fallback for mock context/questions if needed
      }

      // Reset answers and final result for new PR
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

  const handlePrefillSampleAnswers = () => {
    if (questionData?.sample_answers) {
      setAnswers({ ...questionData.sample_answers });
    }
  };

  const handleSubmitAnswers = async () => {
    if (!prData) return;
    setSubmitting(true);
    try {
      const result = await submitAnswers(
        prData.repository,
        prData.pr_id,
        answers
      );
      setFinalResult(result);
      setActiveTab("result");
    } catch (err) {
      setError(err.message || "Failed to submit answers for evaluation.");
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
            onPrefillSampleAnswers={handlePrefillSampleAnswers}
            onSubmitAnswers={handleSubmitAnswers}
            submitting={submitting}
          />
        )}

        {activeTab === "result" && (
          <FinalResult finalResult={finalResult} onReset={handleReset} />
        )}
      </main>
    </div>
  );
}
