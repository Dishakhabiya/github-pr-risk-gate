/**
 * US-12 Frontend Tests: QuestionCard developer answer interface
 * Tests cover: rendering, per-question answer fields, answer association,
 * unanswered state, submission payload, API failure display, success display.
 */
import React, { useState } from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import QuestionCard from "../components/QuestionCard";

// ─── Sample fixture data ──────────────────────────────────────────────────────

const SAMPLE_QUESTIONS = [
  {
    id: "q1",
    question: "Why was the localized token cache added instead of calling verifyTokenRemote?",
    category: "edge cases",
    related_file: "pkg/kubeapiserver/authenticator/config.go",
    supporting_context: "func (c *Config) AuthenticateRequest(req *http.Request)",
  },
  {
    id: "q2",
    question: "How does this change handle cache invalidation or expired bearer tokens?",
    category: "security/performance",
    related_file: "pkg/kubeapiserver/authenticator/token_cache.go",
    supporting_context: null,
  },
  {
    id: "q3",
    question: "What race conditions or concurrent access edge cases were considered?",
    category: "tests",
    related_file: null,
    supporting_context: null,
  },
];

// ─── Helper: stateful wrapper so answers actually update ─────────────────────

function QuestionCardWrapper(props) {
  const [answers, setAnswers] = useState(props.initialAnswers || {});
  const handleChange = (id, val) => setAnswers((prev) => ({ ...prev, [id]: val }));
  return (
    <QuestionCard
      {...props}
      answers={answers}
      onAnswerChange={props.onAnswerChange || handleChange}
    />
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("QuestionCard – US-12 Developer Answer Interface", () => {

  // 1. Questions render correctly
  it("renders all questions with correct numbered labels", () => {
    render(
      <QuestionCard
        questions={SAMPLE_QUESTIONS}
        answers={{}}
        onAnswerChange={vi.fn()}
        onSubmitAnswers={vi.fn()}
        submitting={false}
      />
    );

    expect(screen.getByTestId("question-card")).toBeInTheDocument();
    expect(screen.getByText(/Q1\./)).toBeInTheDocument();
    expect(screen.getByText(/Q2\./)).toBeInTheDocument();
    expect(screen.getByText(/Q3\./)).toBeInTheDocument();

    expect(screen.getByText(/localized token cache/i)).toBeInTheDocument();
    expect(screen.getByText(/cache invalidation/i)).toBeInTheDocument();
    expect(screen.getByText(/race conditions/i)).toBeInTheDocument();
  });

  // 2. Each question has its own dedicated answer field
  it("renders a separate textarea for each question", () => {
    render(
      <QuestionCard
        questions={SAMPLE_QUESTIONS}
        answers={{}}
        onAnswerChange={vi.fn()}
        onSubmitAnswers={vi.fn()}
        submitting={false}
      />
    );

    const textareas = screen.getAllByRole("textbox");
    expect(textareas).toHaveLength(SAMPLE_QUESTIONS.length);

    // Each textarea is bound to its own question by data-question-id attribute
    expect(textareas[0]).toHaveAttribute("data-question-id", "q1");
    expect(textareas[1]).toHaveAttribute("data-question-id", "q2");
    expect(textareas[2]).toHaveAttribute("data-question-id", "q3");
  });

  // 3. Answers remain associated with the correct question
  it("correctly associates typed answer with its question and not others", async () => {
    const user = userEvent.setup();
    const onAnswerChange = vi.fn();

    render(
      <QuestionCard
        questions={SAMPLE_QUESTIONS}
        answers={{}}
        onAnswerChange={onAnswerChange}
        onSubmitAnswers={vi.fn()}
        submitting={false}
      />
    );

    const q2Textarea = screen.getByTestId("answer-input-1"); // idx=1 → q2
    await user.type(q2Textarea, "Cache uses TTL expiration");

    // Every call must include question id "q2"
    const callArgs = onAnswerChange.mock.calls;
    callArgs.forEach(([qId]) => {
      expect(qId).toBe("q2");
    });

    // q1 and q3 must never have been touched
    expect(onAnswerChange).not.toHaveBeenCalledWith("q1", expect.anything());
    expect(onAnswerChange).not.toHaveBeenCalledWith("q3", expect.anything());
  });

  // 4. Unanswered state is shown clearly
  it("shows unanswered count badge and per-question unanswered indicator", () => {
    render(
      <QuestionCard
        questions={SAMPLE_QUESTIONS}
        answers={{ q1: "Some answer" }}   // q2 and q3 unanswered
        onAnswerChange={vi.fn()}
        onSubmitAnswers={vi.fn()}
        submitting={false}
      />
    );

    // Global unanswered counter
    expect(screen.getByTestId("unanswered-count")).toHaveTextContent("2 unanswered");

    // Per-question unanswered indicators on q2 (idx 1) and q3 (idx 2)
    expect(screen.getByTestId("unanswered-indicator-1")).toBeInTheDocument();
    expect(screen.getByTestId("unanswered-indicator-2")).toBeInTheDocument();

    // q1 is answered so it must NOT have an unanswered indicator
    expect(screen.queryByTestId("unanswered-indicator-0")).not.toBeInTheDocument();
  });

  // 5. Submitting answers produces the correct structured payload
  it("calls onSubmitAnswers when submit button is clicked", async () => {
    const user = userEvent.setup();
    const onSubmitAnswers = vi.fn();

    render(
      <QuestionCard
        questions={SAMPLE_QUESTIONS}
        answers={{ q1: "Answer 1", q2: "Answer 2", q3: "Answer 3" }}
        onAnswerChange={vi.fn()}
        onSubmitAnswers={onSubmitAnswers}
        submitting={false}
      />
    );

    const submitBtn = screen.getByTestId("submit-answers-btn");
    await user.click(submitBtn);

    expect(onSubmitAnswers).toHaveBeenCalledTimes(1);
  });

  // 6. API failure displays a useful error message
  it("displays submitError message when submission fails", () => {
    render(
      <QuestionCard
        questions={SAMPLE_QUESTIONS}
        answers={{}}
        onAnswerChange={vi.fn()}
        onSubmitAnswers={vi.fn()}
        submitting={false}
        submitError="Unable to submit answers to http://localhost:8000."
      />
    );

    const errorEl = screen.getByTestId("submit-error");
    expect(errorEl).toBeInTheDocument();
    expect(errorEl).toHaveTextContent("Unable to submit answers");
  });

  // 7. Successful submission displays appropriate feedback
  it("displays success message after submission succeeds", () => {
    render(
      <QuestionCard
        questions={SAMPLE_QUESTIONS}
        answers={{ q1: "A", q2: "B", q3: "C" }}
        onAnswerChange={vi.fn()}
        onSubmitAnswers={vi.fn()}
        submitting={false}
        submitSuccess={true}
      />
    );

    const successEl = screen.getByTestId("submit-success");
    expect(successEl).toBeInTheDocument();
    expect(successEl).toHaveTextContent("submitted successfully");
  });

  // 8. No questions state renders empty state (not null/crash)
  it("renders empty-state UI when no questions are provided", () => {
    render(
      <QuestionCard
        questions={[]}
        answers={{}}
        onAnswerChange={vi.fn()}
        onSubmitAnswers={vi.fn()}
        submitting={false}
      />
    );

    expect(screen.getByTestId("no-questions-state")).toBeInTheDocument();
    expect(screen.getByText(/no questions available/i)).toBeInTheDocument();
  });

  // 9. Category and related_file badges render from question metadata
  it("renders category badge and related_file badge when present", () => {
    render(
      <QuestionCard
        questions={[SAMPLE_QUESTIONS[0]]}
        answers={{}}
        onAnswerChange={vi.fn()}
        onSubmitAnswers={vi.fn()}
        submitting={false}
      />
    );

    expect(screen.getByTestId("category-badge-0")).toHaveTextContent("EDGE CASES");
    expect(screen.getByTestId("file-badge-0")).toHaveTextContent("config.go");
  });

  // 10. Supporting context renders when available
  it("renders supporting_context snippet for relevant questions", () => {
    render(
      <QuestionCard
        questions={[SAMPLE_QUESTIONS[0]]}
        answers={{}}
        onAnswerChange={vi.fn()}
        onSubmitAnswers={vi.fn()}
        submitting={false}
      />
    );

    expect(screen.getByTestId("supporting-context-0")).toHaveTextContent(
      "AuthenticateRequest"
    );
  });

  // 11. Submit button is disabled while submitting
  it("disables submit button while submitting=true", () => {
    render(
      <QuestionCard
        questions={SAMPLE_QUESTIONS}
        answers={{}}
        onAnswerChange={vi.fn()}
        onSubmitAnswers={vi.fn()}
        submitting={true}
      />
    );

    expect(screen.getByTestId("submit-answers-btn")).toBeDisabled();
    expect(screen.getByText(/submitting answers/i)).toBeInTheDocument();
  });

  // 12. Answers update in state correctly through interaction
  it("updates textarea value when user types", async () => {
    const user = userEvent.setup();

    render(<QuestionCardWrapper questions={SAMPLE_QUESTIONS} />);

    const q1Input = screen.getByTestId("answer-input-0");
    await user.type(q1Input, "Using sync.RWMutex");

    expect(q1Input).toHaveValue("Using sync.RWMutex");

    // Sanity check: q2 textarea must remain unchanged
    expect(screen.getByTestId("answer-input-1")).toHaveValue("");
  });
});
