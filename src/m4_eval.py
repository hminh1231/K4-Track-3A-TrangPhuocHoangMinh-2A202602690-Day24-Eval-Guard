from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json, math
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation.

    Returns {<metric>: mean, "per_question": [EvalResult], "metadata": {"evaluator_models": [...]}}.
    Rows the evaluator LLM failed on (NaN) are re-scored up to NAN_RETRIES times; a score that is
    still NaN raises instead of being replaced by a made-up number.
    """
    if not (len(questions) == len(answers) == len(contexts) == len(ground_truths)):
        raise ValueError("questions/answers/contexts/ground_truths must have the same length")
    if not questions:
        return {**{m: 0.0 for m in METRICS}, "per_question": [],
                "metadata": {"evaluator_models": list(EVALUATOR_MODELS)}}

    per_question = _score_rows(questions, answers, contexts, ground_truths)
    for attempt in range(NAN_RETRIES):
        pending = [i for i, r in enumerate(per_question)
                   if any(math.isnan(getattr(r, m)) for m in METRICS)]
        if not pending:
            break
        print(f"  ↻ Re-scoring {len(pending)} rows with NaN metrics (attempt {attempt + 1}/{NAN_RETRIES})")
        rescored = _score_rows([questions[i] for i in pending], [answers[i] for i in pending],
                               [contexts[i] for i in pending], [ground_truths[i] for i in pending])
        for i, new in zip(pending, rescored):
            old = per_question[i]
            for m in METRICS:
                if math.isnan(getattr(old, m)) and not math.isnan(getattr(new, m)):
                    setattr(old, m, getattr(new, m))

    missing = [(i, m) for i, r in enumerate(per_question) for m in METRICS if math.isnan(getattr(r, m))]
    if missing:
        raise RuntimeError(f"RAGAS left {len(missing)} NaN scores after retries: {missing[:10]}")

    aggregate = {m: sum(getattr(r, m) for r in per_question) / len(per_question) for m in METRICS}
    return {**aggregate, "per_question": per_question,
            "metadata": {"evaluator_models": list(EVALUATOR_MODELS)}}


# Models actually passed to ragas.evaluate below (LLM for all 4 metrics, embeddings for answer_relevancy).
EVALUATOR_LLM_MODEL = "gpt-4o-mini"
EVALUATOR_EMBEDDING_MODEL = "text-embedding-3-small"
EVALUATOR_MODELS = (EVALUATOR_LLM_MODEL, EVALUATOR_EMBEDDING_MODEL)
NAN_RETRIES = 3


def _score_rows(questions, answers, contexts, ground_truths) -> list[EvalResult]:
    from datasets import Dataset
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    from ragas.run_config import RunConfig

    dataset = Dataset.from_dict({
        "question": questions, "answer": answers,
        "contexts": contexts, "ground_truth": ground_truths,
    })
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=ChatOpenAI(model=EVALUATOR_LLM_MODEL, temperature=0),
        embeddings=OpenAIEmbeddings(model=EVALUATOR_EMBEDDING_MODEL),
        run_config=RunConfig(max_workers=8, timeout=180, max_retries=5),
        raise_exceptions=False,
    )
    df = result.to_pandas()
    if len(df) != len(questions):
        raise RuntimeError(f"RAGAS returned {len(df)} rows for {len(questions)} questions")
    # RAGAS keeps input order; rows are rebuilt from the inputs so nothing is re-sorted.
    return [
        EvalResult(question=q, answer=a, contexts=list(c), ground_truth=g,
                   **{m: _to_float(row.get(m)) for m in METRICS})
        for (q, a, c, g), (_, row) in zip(zip(questions, answers, contexts, ground_truths), df.iterrows())
    ]


METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

DIAGNOSTIC_TREE = {
    "faithfulness": ("LLM tự bịa câu trả lời ngoài tài liệu (hallucination)",
                     "Thắt chặt system prompt, giảm temperature về 0"),
    "context_recall": ("Hệ thống tìm kiếm bỏ sót đoạn văn đúng",
                       "Cải thiện bước chunking hoặc bổ sung từ khóa BM25"),
    "context_precision": ("Đoạn văn không liên quan bị xếp lên đầu",
                          "Bổ sung Cross-Encoder reranking hoặc lọc theo metadata"),
    "answer_relevancy": ("Câu trả lời bị lệch trọng tâm câu hỏi",
                         "Viết lại prompt hướng dẫn mô hình trả lời trực tiếp hơn"),
}


def _to_float(value) -> float:
    """Convert a RAGAS cell to float; unscored cells stay NaN so they are not mistaken for 0."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    analyzed = []
    for r in eval_results:
        scores = {m: getattr(r, m) for m in METRICS}
        valid = {m: v for m, v in scores.items() if not math.isnan(v)}
        if not valid:
            continue
        avg = sum(valid.values()) / len(valid)
        worst_metric = min(valid, key=valid.get)
        diagnosis, suggested_fix = DIAGNOSTIC_TREE[worst_metric]
        analyzed.append({
            "question": r.question,
            "answer": r.answer,
            "ground_truth": r.ground_truth,
            "avg_score": round(avg, 4),
            "worst_metric": worst_metric,
            "score": round(valid[worst_metric], 4),
            "scores": {m: (None if math.isnan(v) else round(v, 4)) for m, v in scores.items()},
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })
    analyzed.sort(key=lambda x: x["avg_score"])
    return analyzed[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
