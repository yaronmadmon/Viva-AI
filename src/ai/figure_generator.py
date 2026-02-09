"""
Figure Generator -- creates publication-quality matplotlib charts from
synthetic results data and returns them as base64-encoded PNG strings
for embedding into markdown content.

Pipeline position:  after Results text → generate figures → embed into
                    Results and Discussion sections.
"""

from __future__ import annotations

import base64
import io
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import get_settings

logger = logging.getLogger(__name__)


# ── Data structures ──────────────────────────────────────────────────

@dataclass
class FigureSpec:
    """Specification for a single figure."""
    figure_number: int
    figure_type: str          # "bar_chart", "confusion_matrix", "roc_curve", "loss_curve", "distribution"
    title: str
    caption: str
    data: Dict[str, Any]      # type-specific data payload
    width: float = 8.0        # inches
    height: float = 6.0       # inches


@dataclass
class GeneratedFigure:
    """A generated figure with its base64-encoded PNG."""
    figure_number: int
    title: str
    caption: str
    base64_png: str           # base64 encoded PNG data

    @property
    def markdown(self) -> str:
        """Return markdown image tag for embedding."""
        return f"![Figure {self.figure_number}: {self.caption}](data:image/png;base64,{self.base64_png})"


# ── Figure planning (GPT decides which figures are needed) ───────────

_FIGURE_PLAN_PROMPT = """\
You are a PhD dissertation figure planner. Given the synthetic results data below,
decide which figures should be included in the Results and Discussion chapters.

A typical STEM PhD includes 5-8 figures. Choose from these types:
- "bar_chart": Model comparison (accuracy, F1, etc.)
- "confusion_matrix": Classification confusion matrix for the best model
- "roc_curve": ROC curves comparing models
- "loss_curve": Training/validation loss over epochs
- "distribution": Dataset class distribution or feature distribution

Return a JSON array of figure specifications:
[
  {
    "figure_number": 1,
    "figure_type": "<type>",
    "title": "<concise title>",
    "caption": "<detailed academic caption>",
    "data": { <type-specific data, see below> }
  }
]

DATA FORMATS per type:

bar_chart:
  {"metric": "F1 Score", "models": ["Model A", "Model B"], "values": [0.85, 0.91]}

confusion_matrix:
  {"labels": ["Class A", "Class B", "Class C"], "matrix": [[90, 5, 5], [3, 87, 10], [7, 8, 85]]}

roc_curve:
  {"models": [{"name": "Model A", "fpr": [0, 0.1, 0.2, ..., 1.0], "tpr": [0, 0.4, 0.6, ..., 1.0], "auc": 0.89}]}

loss_curve:
  {"epochs": [1, 2, ..., 50], "train_loss": [2.1, 1.8, ...], "val_loss": [2.3, 2.0, ...]}

distribution:
  {"labels": ["Class A", "Class B", "Class C"], "counts": [3200, 2800, 2100]}

Generate 5-8 figures that tell a complete results story.
"""


async def plan_figures(
    topic: str,
    results_data: Dict[str, Any],
) -> List[FigureSpec]:
    """
    Use GPT to decide which figures are needed based on the results data.

    Args:
        topic: Dissertation topic
        results_data: Raw JSON from SyntheticResults

    Returns:
        List of FigureSpec objects
    """
    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    is_placeholder = not key or key.startswith("sk-your-")

    if is_placeholder:
        logger.warning("No API key; returning stub figure plan")
        return _stub_figure_plan(results_data)

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=key)

    user_prompt = (
        f"RESEARCH TOPIC: {topic}\n\n"
        f"SYNTHETIC RESULTS DATA:\n{json.dumps(results_data, indent=2)[:6000]}\n\n"
        "Plan the figures now. Return ONLY the JSON array."
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _FIGURE_PLAN_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4096,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw_text = (response.choices[0].message.content or "").strip()
        data = json.loads(raw_text)

        # Handle both {"figures": [...]} and bare [...]
        fig_list = data if isinstance(data, list) else data.get("figures", [])

        specs = []
        for item in fig_list:
            specs.append(FigureSpec(
                figure_number=item.get("figure_number", len(specs) + 1),
                figure_type=item.get("figure_type", "bar_chart"),
                title=item.get("title", f"Figure {len(specs) + 1}"),
                caption=item.get("caption", ""),
                data=item.get("data", {}),
            ))

        logger.info("Figure plan: %d figures planned", len(specs))
        return specs

    except Exception as exc:
        logger.error("Figure planning failed: %s", exc)
        return _stub_figure_plan(results_data)


def _stub_figure_plan(results_data: Dict[str, Any]) -> List[FigureSpec]:
    """Fallback figure plan using the results data directly."""
    specs = []
    fig_num = 1

    # Model comparison bar chart
    metrics = results_data.get("model_metrics", [])
    if metrics:
        specs.append(FigureSpec(
            figure_number=fig_num,
            figure_type="bar_chart",
            title="Model Performance Comparison",
            caption="Comparison of classification performance across all evaluated models. Error bars represent 95% confidence intervals.",
            data={
                "metric": "F1 Score",
                "models": [m.get("model_name", f"Model {i}") for i, m in enumerate(metrics)],
                "values": [m.get("f1_score", 0) for m in metrics],
            },
        ))
        fig_num += 1

        # AUC bar chart
        specs.append(FigureSpec(
            figure_number=fig_num,
            figure_type="bar_chart",
            title="AUC-ROC Comparison",
            caption="Area under the ROC curve for each model, indicating discriminative performance.",
            data={
                "metric": "AUC-ROC",
                "models": [m.get("model_name", f"Model {i}") for i, m in enumerate(metrics)],
                "values": [m.get("auc_roc", 0) for m in metrics],
            },
        ))
        fig_num += 1

    # Dataset distribution
    ds = results_data.get("dataset_stats", {})
    class_dist = ds.get("class_distribution", {})
    if class_dist:
        specs.append(FigureSpec(
            figure_number=fig_num,
            figure_type="distribution",
            title="Dataset Class Distribution",
            caption="Distribution of samples across classes in the complete dataset.",
            data={
                "labels": list(class_dist.keys()),
                "counts": list(class_dist.values()),
            },
        ))
        fig_num += 1

    # Confusion matrix (synthesized)
    if metrics:
        n_classes = ds.get("num_classes", 4)
        labels = list(class_dist.keys())[:n_classes] if class_dist else [f"Class {i+1}" for i in range(n_classes)]
        # Generate a plausible confusion matrix
        cm = _generate_plausible_cm(n_classes, best_acc=metrics[-1].get("accuracy", 0.85))
        specs.append(FigureSpec(
            figure_number=fig_num,
            figure_type="confusion_matrix",
            title="Confusion Matrix (Proposed Model)",
            caption="Confusion matrix for the proposed model on the test set, showing per-class classification performance.",
            data={
                "labels": labels,
                "matrix": cm,
            },
        ))
        fig_num += 1

    # Training loss curve (synthesized)
    specs.append(FigureSpec(
        figure_number=fig_num,
        figure_type="loss_curve",
        title="Training and Validation Loss",
        caption="Training and validation loss curves over 50 epochs, showing model convergence.",
        data={
            "epochs": list(range(1, 51)),
            "train_loss": _generate_loss_curve(50, start=2.1, end=0.15),
            "val_loss": _generate_loss_curve(50, start=2.3, end=0.28, noise=0.05),
        },
    ))
    fig_num += 1

    return specs


def _generate_plausible_cm(n_classes: int, best_acc: float) -> List[List[int]]:
    """Generate a plausible confusion matrix."""
    size = 200  # samples per class
    cm = []
    for i in range(n_classes):
        row = []
        correct = int(size * best_acc)
        remaining = size - correct
        for j in range(n_classes):
            if i == j:
                row.append(correct)
            else:
                share = remaining // (n_classes - 1)
                row.append(share)
        cm.append(row)
    return cm


def _generate_loss_curve(epochs: int, start: float, end: float, noise: float = 0.02) -> List[float]:
    """Generate a plausible loss curve with exponential decay."""
    t = np.linspace(0, 1, epochs)
    curve = start * np.exp(-3 * t) + end
    curve += np.random.normal(0, noise, epochs)
    return [round(max(0.01, float(v)), 4) for v in curve]


# ── Figure rendering ─────────────────────────────────────────────────

def generate_figure(spec: FigureSpec) -> GeneratedFigure:
    """
    Render a single figure using matplotlib and return as base64 PNG.

    Args:
        spec: FigureSpec with type-specific data

    Returns:
        GeneratedFigure with base64-encoded PNG
    """
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(spec.width, spec.height))

    try:
        renderers = {
            "bar_chart": _render_bar_chart,
            "confusion_matrix": _render_confusion_matrix,
            "roc_curve": _render_roc_curve,
            "loss_curve": _render_loss_curve,
            "distribution": _render_distribution,
        }
        renderer = renderers.get(spec.figure_type, _render_bar_chart)
        renderer(ax, spec)

        fig.tight_layout()

        # Encode to base64
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("ascii")

        logger.info("Figure %d rendered: %s (%d KB)",
                     spec.figure_number, spec.figure_type, len(b64) // 1024)

        return GeneratedFigure(
            figure_number=spec.figure_number,
            title=spec.title,
            caption=spec.caption,
            base64_png=b64,
        )
    finally:
        plt.close(fig)


def generate_all_figures(specs: List[FigureSpec]) -> List[GeneratedFigure]:
    """Render all figures and return as list of GeneratedFigure."""
    figures = []
    for spec in specs:
        try:
            fig = generate_figure(spec)
            figures.append(fig)
        except Exception as exc:
            logger.error("Failed to render figure %d: %s", spec.figure_number, exc)
    return figures


# ── Renderers ────────────────────────────────────────────────────────

def _render_bar_chart(ax, spec: FigureSpec):
    """Render a grouped bar chart."""
    import matplotlib.pyplot as plt

    data = spec.data
    models = data.get("models", [])
    values = data.get("values", [])
    metric = data.get("metric", "Score")

    colors = plt.cm.Set2(np.linspace(0, 1, max(len(models), 1)))
    bars = ax.bar(range(len(models)), values, color=colors, edgecolor="black", linewidth=0.5)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{val:.3f}", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel(metric, fontsize=11)
    ax.set_title(spec.title, fontsize=13, fontweight="bold")
    ax.set_ylim(0, max(values) * 1.15 if values else 1)
    ax.grid(axis="y", alpha=0.3)


def _render_confusion_matrix(ax, spec: FigureSpec):
    """Render a confusion matrix heatmap."""
    data = spec.data
    labels = data.get("labels", [])
    matrix = np.array(data.get("matrix", [[]]))

    im = ax.imshow(matrix, interpolation="nearest", cmap="Blues")
    ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)

    # Add text annotations
    thresh = matrix.max() / 2.0
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, format(matrix[i, j], "d"),
                    ha="center", va="center",
                    color="white" if matrix[i, j] > thresh else "black",
                    fontsize=10)

    ax.set_xlabel("Predicted Label", fontsize=11)
    ax.set_ylabel("True Label", fontsize=11)
    ax.set_title(spec.title, fontsize=13, fontweight="bold")


def _render_roc_curve(ax, spec: FigureSpec):
    """Render ROC curves for multiple models."""
    import matplotlib.pyplot as plt

    data = spec.data
    models = data.get("models", [])

    colors = plt.cm.Set1(np.linspace(0, 1, max(len(models), 1)))
    for i, model in enumerate(models):
        fpr = model.get("fpr", [0, 1])
        tpr = model.get("tpr", [0, 1])
        auc_val = model.get("auc", 0)
        ax.plot(fpr, tpr, color=colors[i], lw=2,
                label=f"{model.get('name', f'Model {i+1}')} (AUC = {auc_val:.3f})")

    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5, label="Random (AUC = 0.500)")
    ax.set_xlabel("False Positive Rate", fontsize=11)
    ax.set_ylabel("True Positive Rate", fontsize=11)
    ax.set_title(spec.title, fontsize=13, fontweight="bold")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.3)


def _render_loss_curve(ax, spec: FigureSpec):
    """Render training/validation loss curves."""
    data = spec.data
    epochs = data.get("epochs", [])
    train_loss = data.get("train_loss", [])
    val_loss = data.get("val_loss", [])

    ax.plot(epochs, train_loss, "b-", lw=2, label="Training Loss")
    ax.plot(epochs, val_loss, "r-", lw=2, label="Validation Loss")
    ax.set_xlabel("Epoch", fontsize=11)
    ax.set_ylabel("Loss", fontsize=11)
    ax.set_title(spec.title, fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)


def _render_distribution(ax, spec: FigureSpec):
    """Render a distribution bar chart."""
    import matplotlib.pyplot as plt

    data = spec.data
    labels = data.get("labels", [])
    counts = data.get("counts", [])

    colors = plt.cm.Pastel1(np.linspace(0, 1, max(len(labels), 1)))
    bars = ax.bar(range(len(labels)), counts, color=colors, edgecolor="black", linewidth=0.5)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(counts) * 0.01,
                f"{count:,}", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Count", fontsize=11)
    ax.set_title(spec.title, fontsize=13, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
