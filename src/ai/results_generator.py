"""
Synthetic Results Generator -- produces internally-consistent experimental
data that feeds into both the Results prose and figure generation.

The generator uses GPT-4o to create a structured JSON blob of plausible
experimental results (metrics, tables, statistical tests) for a given
research topic and methodology.  This ensures that numbers in the text,
tables, and figures all agree.

Pipeline position:  after Methodology text → generate_synthetic_results()
                    → feed into Results subsections + figure_generator
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.config import get_settings

logger = logging.getLogger(__name__)


# ── Data structures ──────────────────────────────────────────────────

@dataclass
class SyntheticResults:
    """Container for all synthetic experimental data."""
    dataset_stats: Dict[str, Any] = field(default_factory=dict)
    model_metrics: List[Dict[str, Any]] = field(default_factory=list)
    statistical_tests: List[Dict[str, Any]] = field(default_factory=list)
    comparison_tables: List[Dict[str, Any]] = field(default_factory=list)
    unexpected_findings: List[Dict[str, Any]] = field(default_factory=list)
    raw_json: Dict[str, Any] = field(default_factory=dict)

    def as_context_string(self) -> str:
        """Format results as a context string for the subsection generator."""
        lines = ["SYNTHETIC RESULTS DATA (use these exact numbers in your prose):\n"]

        # Dataset statistics
        if self.dataset_stats:
            lines.append("DATASET STATISTICS:")
            for k, v in self.dataset_stats.items():
                lines.append(f"  {k}: {v}")
            lines.append("")

        # Model metrics
        if self.model_metrics:
            lines.append("MODEL PERFORMANCE METRICS:")
            header = "| Model | " + " | ".join(
                k for k in self.model_metrics[0] if k != "model_name"
            ) + " |"
            sep = "|" + "|".join("---" for _ in header.split("|")[1:-1]) + "|"
            lines.append(header)
            lines.append(sep)
            for m in self.model_metrics:
                name = m.get("model_name", "Unknown")
                vals = " | ".join(
                    str(m[k]) for k in m if k != "model_name"
                )
                lines.append(f"| {name} | {vals} |")
            lines.append("")

        # Statistical tests
        if self.statistical_tests:
            lines.append("STATISTICAL TEST RESULTS:")
            for t in self.statistical_tests:
                lines.append(
                    f"  {t.get('test_name', 'Test')}: "
                    f"statistic={t.get('statistic', 'N/A')}, "
                    f"p={t.get('p_value', 'N/A')}, "
                    f"effect_size={t.get('effect_size', 'N/A')}, "
                    f"CI={t.get('confidence_interval', 'N/A')}"
                )
            lines.append("")

        # Unexpected findings
        if self.unexpected_findings:
            lines.append("UNEXPECTED FINDINGS:")
            for i, f in enumerate(self.unexpected_findings, 1):
                lines.append(f"  {i}. {f.get('description', '')}")
                if "metric" in f:
                    lines.append(f"     Metric: {f['metric']} = {f.get('value', 'N/A')}")
            lines.append("")

        return "\n".join(lines)


_RESULTS_SCHEMA_PROMPT = """\
You are a PhD-level research data analyst. Given the research topic, methodology,
and research questions below, generate REALISTIC, internally-consistent synthetic
experimental results.

CRITICAL RULES:
1. All numbers must be PLAUSIBLE for the research domain.
2. All numbers must be INTERNALLY CONSISTENT (totals must add up, percentages
   must sum correctly, performance metrics must be in valid ranges).
3. The proposed model should outperform baselines but NOT by an implausible margin.
4. p-values should vary: some significant, some borderline, some non-significant.
5. Include 2-3 unexpected findings that add realism.

Return a JSON object with EXACTLY this structure:
{
  "dataset_stats": {
    "total_samples": <int>,
    "training_samples": <int>,
    "validation_samples": <int>,
    "test_samples": <int>,
    "num_classes": <int>,
    "class_distribution": {"class_name": <int>, ...},
    "missing_data_rate": <float 0-1>,
    "feature_dimensions": <int or description>
  },
  "model_metrics": [
    {
      "model_name": "<name>",
      "accuracy": <float>,
      "precision": <float>,
      "recall": <float>,
      "f1_score": <float>,
      "auc_roc": <float>,
      "training_time_minutes": <float>
    }
  ],
  "statistical_tests": [
    {
      "test_name": "<e.g. paired t-test, McNemar's test, Wilcoxon>",
      "comparison": "<model A vs model B>",
      "statistic": <float>,
      "p_value": <float>,
      "effect_size": <float>,
      "effect_size_type": "<Cohen's d, eta-squared, etc>",
      "confidence_interval": [<lower>, <upper>],
      "significant": <bool>
    }
  ],
  "comparison_tables": [
    {
      "title": "<table title>",
      "headers": ["<col1>", "<col2>", ...],
      "rows": [["<val1>", "<val2>", ...], ...]
    }
  ],
  "unexpected_findings": [
    {
      "description": "<what was unexpected>",
      "metric": "<metric name>",
      "value": "<observed value>",
      "expected": "<what was expected>"
    }
  ]
}

Include at least:
- 3-5 models in model_metrics (1 proposed + 2-4 baselines)
- 3-5 statistical tests
- 2-3 comparison tables
- 2-3 unexpected findings
"""


async def generate_synthetic_results(
    topic: str,
    methodology_text: str,
    research_questions: List[str],
) -> SyntheticResults:
    """
    Generate internally-consistent synthetic experimental results.

    Args:
        topic: Dissertation topic
        methodology_text: The generated methodology section text (for context)
        research_questions: List of research questions/hypotheses

    Returns:
        SyntheticResults with all data populated
    """
    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    is_placeholder = not key or key.startswith("sk-your-")

    if is_placeholder:
        logger.warning("No API key; returning stub synthetic results")
        return _stub_results()

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=key)

    # Truncate methodology to avoid exceeding context window
    method_snippet = methodology_text[:4000] if methodology_text else "(not yet generated)"
    rq_text = "\n".join(f"- {rq}" for rq in research_questions) if research_questions else "(none specified)"

    user_prompt = (
        f"RESEARCH TOPIC: {topic}\n\n"
        f"RESEARCH QUESTIONS:\n{rq_text}\n\n"
        f"METHODOLOGY SUMMARY:\n{method_snippet}\n\n"
        "Generate the synthetic results JSON now."
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _RESULTS_SCHEMA_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4096,
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        raw_text = (response.choices[0].message.content or "").strip()
        data = json.loads(raw_text)

        results = SyntheticResults(
            dataset_stats=data.get("dataset_stats", {}),
            model_metrics=data.get("model_metrics", []),
            statistical_tests=data.get("statistical_tests", []),
            comparison_tables=data.get("comparison_tables", []),
            unexpected_findings=data.get("unexpected_findings", []),
            raw_json=data,
        )

        logger.info(
            "Synthetic results generated: %d models, %d tests, %d tables",
            len(results.model_metrics),
            len(results.statistical_tests),
            len(results.comparison_tables),
        )
        return results

    except Exception as exc:
        logger.error("Synthetic results generation failed: %s", exc)
        return _stub_results()


def _stub_results() -> SyntheticResults:
    """Fallback stub when no API key is available."""
    return SyntheticResults(
        dataset_stats={
            "total_samples": 10000,
            "training_samples": 7000,
            "validation_samples": 1500,
            "test_samples": 1500,
            "num_classes": 4,
            "class_distribution": {"Class A": 3200, "Class B": 2800, "Class C": 2100, "Class D": 1900},
            "missing_data_rate": 0.023,
            "feature_dimensions": 512,
        },
        model_metrics=[
            {"model_name": "Baseline (Logistic Regression)", "accuracy": 0.742, "precision": 0.718, "recall": 0.731, "f1_score": 0.724, "auc_roc": 0.812, "training_time_minutes": 2.3},
            {"model_name": "Random Forest", "accuracy": 0.801, "precision": 0.789, "recall": 0.796, "f1_score": 0.792, "auc_roc": 0.867, "training_time_minutes": 8.7},
            {"model_name": "Proposed Model", "accuracy": 0.873, "precision": 0.861, "recall": 0.879, "f1_score": 0.870, "auc_roc": 0.934, "training_time_minutes": 45.2},
        ],
        statistical_tests=[
            {"test_name": "Paired t-test", "comparison": "Proposed vs Baseline", "statistic": 4.82, "p_value": 0.0003, "effect_size": 1.24, "effect_size_type": "Cohen's d", "confidence_interval": [0.078, 0.184], "significant": True},
            {"test_name": "McNemar's test", "comparison": "Proposed vs Random Forest", "statistic": 12.45, "p_value": 0.012, "effect_size": 0.67, "effect_size_type": "Cohen's d", "confidence_interval": [0.031, 0.113], "significant": True},
        ],
        comparison_tables=[],
        unexpected_findings=[
            {"description": "The baseline model outperformed the proposed model on Class D samples", "metric": "F1 (Class D)", "value": "0.891 vs 0.856", "expected": "Proposed model to dominate all classes"},
        ],
    )
