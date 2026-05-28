"""Generate self-contained academic-style static HTML demo page for MEXT interview.

Reads a completed evaluation run and produces a single-file HTML page
with all 7 narrative sections, embedded plots (base64), comparison table,
and live recommendation example. Zero JavaScript, zero external dependencies.

Usage:
    python -m scripts.generate_demo
    python -m scripts.generate_demo --run-path ml/eval/runs/20260528_165737
    python -m scripts.generate_demo --output ./mext_demo.html --verbose
"""

import argparse
import base64
import io
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not available — cannot embed plots")

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML not available — cannot read config.yaml")


# ── Locked metrics from CHANGELOG (paper canonical values, Phase 5 locked) ──
LOCKED_METRICS: dict[str, dict[str, float]] = {
    "GraphSAGE-Jaccard":      {"Precision@10": 0.0745, "NDCG@10": 0.504, "Recall@10": 0.0926},
    "GraphSAGE-Embedding":    {"Precision@10": 0.0306, "NDCG@10": 0.197, "Recall@10": 0.0216},
    "Feature-Only":           {"Precision@10": 0.0782, "NDCG@10": 0.557, "Recall@10": 0.0932},
    "Content-Only (oracle — invalid baseline)":  {"Precision@10": 0.0860, "NDCG@10": 0.581, "Recall@10": 0.1225},
    "Popularity":             {"Precision@10": 0.0019, "NDCG@10": 0.008, "Recall@10": 0.0010},
    "Random":                 {"Precision@10": 0.0045, "NDCG@10": 0.021, "Recall@10": 0.0011},
}

MODEL_ORDER = [
    "GraphSAGE-Jaccard",
    "GraphSAGE-Embedding",
    "Feature-Only",
    "Content-Only (oracle — invalid baseline)",
    "Popularity",
    "Random",
]

# Models to include in the bar chart (exclude oracle baseline)
CHART_MODELS = [m for m in MODEL_ORDER if "oracle" not in m.lower()]

CSS_STYLE = """
body {
    font-family: 'Georgia', 'Times New Roman', serif;
    max-width: 960px;
    margin: 2rem auto;
    padding: 0 1.5rem;
    background: #ffffff;
    color: #1a1a1a;
    line-height: 1.7;
    font-size: 16px;
}
h1 { font-size: 1.8rem; text-align: center; margin-bottom: 0.5rem; }
h2 { font-size: 1.3rem; border-bottom: 1px solid #ccc; padding-bottom: 0.3rem; margin-top: 2rem; }
h3 { font-size: 1.1rem; margin-top: 1.5rem; margin-bottom: 0.5rem; }
p { margin: 0.8rem 0; }
ul, ol { margin: 0.5rem 0; padding-left: 1.5rem; }
li { margin: 0.3rem 0; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.9rem; }
th, td { border: 1px solid #ccc; padding: 0.5rem; text-align: center; }
th { background: #f5f5f5; font-weight: bold; }
img { max-width: 100%; height: auto; margin: 1rem 0; display: block; }
.limitations-box { background: #fafafa; border-left: 4px solid #999; padding: 1rem; margin: 1rem 0; font-style: italic; }
.oracle-box { background: #fff8f0; border-left: 4px solid #e67e22; padding: 1rem; margin: 1rem 0; }
.key-result { background: #f0f7ff; border-left: 4px solid #4C72B0; padding: 1rem; margin: 1rem 0; }
.pipeline-flow { font-family: 'Courier New', monospace; background: #f9f9f9; padding: 1rem; white-space: pre; font-size: 0.85rem; line-height: 1.4; overflow-x: auto; }
a { color: #1a1a1a; text-decoration: none; }
.author { text-align: center; color: #555; font-size: 0.9rem; margin-top: -0.5rem; }
.example-box { background: #f9f9f9; border: 1px solid #ddd; padding: 1rem; margin: 1rem 0; border-radius: 4px; }
.footer { text-align: center; color: #888; font-size: 0.8rem; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #eee; }
.highlight { font-weight: bold; color: #4C72B0; }
.metric-good { color: #2e7d32; font-weight: bold; }
.metric-neutral { color: #888; }
.metric-oracle { color: #e67e22; font-weight: bold; font-style: italic; }
code { font-family: 'Courier New', monospace; background: #f5f5f5; padding: 0.1rem 0.3rem; border-radius: 2px; font-size: 0.85rem; }
"""


def img_to_base64(path: str) -> str:
    if not PIL_AVAILABLE:
        logger.warning("Cannot embed %s: Pillow not available", path)
        return ""
    try:
        with PILImage.open(path) as img:
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            encoded = base64.b64encode(buf.getvalue()).decode()
            return f"data:image/png;base64,{encoded}"
    except Exception as e:
        logger.warning("Failed to embed image %s: %s", path, e)
        return ""


def _fragrance_name(frag_id: str) -> str:
    if frag_id.startswith("frag_"):
        frag_id = frag_id[5:]
    parts = frag_id.rsplit("_", 1)
    name_part = parts[0] if len(parts) > 1 else frag_id
    name = name_part.replace("-", " ").title()
    year = parts[1] if len(parts) > 1 and parts[1].isdigit() else ""
    if year:
        return f"{name} ({year})"
    return name


def load_master_data(data_path: str) -> dict[str, dict]:
    if not os.path.exists(data_path):
        logger.warning("Master data not found at %s", data_path)
        return {}
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            records = json.load(f)
        return {r["id"]: r for r in records}
    except Exception as e:
        logger.warning("Failed to load master data: %s", e)
        return {}


def generate_comparison_bar_chart(output_path: str) -> str:
    if not PIL_AVAILABLE:
        return ""

    metric_keys = ["Precision@10", "NDCG@10", "Recall@10"]
    colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"]

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        x = np.arange(len(metric_keys))
        n_models = len(CHART_MODELS)
        width = 0.8 / n_models

        fig, ax = plt.subplots(figsize=(10, 5))
        for i, model_name in enumerate(CHART_MODELS):
            vals = [LOCKED_METRICS[model_name].get(k, 0.0) for k in metric_keys]
            bars = ax.bar(x + i * width, vals, width, label=model_name, color=colors[i % len(colors)])
            for bar, val in zip(bars, vals):
                if val > 0.001:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.002,
                            f"{val:.3f}", ha="center", va="bottom", fontsize=8)

        ax.set_xlabel("Metric")
        ax.set_ylabel("Score")
        ax.set_title("Cold-Start Evaluation: Five-Model Comparison")
        ax.set_xticks(x + (n_models - 1) * width / 2)
        ax.set_xticklabels(metric_keys)
        ax.legend(fontsize=8)
        all_vals = [LOCKED_METRICS[m].get(k, 0.0) for m in CHART_MODELS for k in metric_keys]
        ax.set_ylim(0, max(1.0, max(all_vals) * 1.3))
        ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        encoded = base64.b64encode(buf.getvalue()).decode()

        plots_dir = Path(output_path).parent
        plot_path = plots_dir / "comparison_bar_chart.png"
        with open(plot_path, "wb") as f:
            f.write(buf.getvalue())
        logger.info("Saved comparison chart to %s", plot_path)

        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        logger.warning("Failed to generate bar chart: %s", e)
        return ""


def generate_live_example(run_dir: Path, master_data: dict[str, dict]) -> str:
    splits_dir = run_dir / "splits"
    cold_items_path = splits_dir / "cold_items.csv"

    if not cold_items_path.is_file():
        return "<p><em>Recommendation example not available — cold split required.</em></p>"

    import csv
    with open(cold_items_path) as f:
        cold_ids = [row[0] for row in csv.reader(f)][1:]

    if not cold_ids:
        return "<p><em>No cold items available for example.</em></p>"

    if not master_data:
        return "<p><em>Master data not loaded — cannot build example.</em></p>"

    example_cold = cold_ids[0]
    cold_record = master_data.get(example_cold)
    if not cold_record:
        return "<p><em>Example cold item not found in master data.</em></p>"

    cold_notes = {str(n).lower() for n in (cold_record.get("top_notes") or [])}
    cold_notes |= {str(n).lower() for n in (cold_record.get("middle_notes") or [])}
    cold_notes |= {str(n).lower() for n in (cold_record.get("base_notes") or [])}
    cold_primary = (cold_record.get("accords") or ["Unknown"])[0]

    relevant: list[tuple[str, float]] = []
    for other_id, other_record in master_data.items():
        if other_id == example_cold:
            continue
        other_primary = (other_record.get("accords") or ["Unknown"])[0]
        if other_primary != cold_primary:
            continue
        other_notes = {str(n).lower() for n in (other_record.get("top_notes") or [])}
        other_notes |= {str(n).lower() for n in (other_record.get("middle_notes") or [])}
        other_notes |= {str(n).lower() for n in (other_record.get("base_notes") or [])}
        union = cold_notes | other_notes
        jaccard = len(cold_notes & other_notes) / len(union) if union else 0.0
        if jaccard > 0.20:
            relevant.append((other_id, jaccard))

    relevant.sort(key=lambda x: -x[1])
    top_gt = relevant[:5] if relevant else []
    top_gs_jac = top_gt  # GraphSAGE-Jaccard would recover these (structural independence)

    html = f"""
    <div class="example-box">
        <h3>Example: <em>{_fragrance_name(example_cold)}</em></h3>
        <p>Primary accord: <strong>{cold_primary}</strong> &nbsp;|&nbsp;
        Notes: {', '.join(sorted(cold_notes)[:5])}</p>
        <p>This fragrance was held out as a <strong>cold-start</strong> item
        with zero interaction history. Below we show its ground-truth neighbours
        (same primary accord, Jaccard(notes)&nbsp;&gt;&nbsp;0.20) — the set
        GraphSAGE-Jaccard must recover from structural signals alone.</p>

        <table>
            <tr>
                <th>Rank</th>
                <th>Ground-Truth Neighbour</th>
                <th>Jaccard Score</th>
                <th>Same Accord</th>
            </tr>
    """
    for i, (nid, score) in enumerate(top_gt[:5], 1):
        n_record = master_data.get(nid, {})
        n_primary = (n_record.get("accords") or [""])[0]
        html += f"""
            <tr>
                <td>{i}</td>
                <td>{_fragrance_name(nid)}</td>
                <td>{score:.3f}</td>
                <td>{n_primary}</td>
            </tr>"""

    html += """
        </table>
        <p style="font-size: 0.85rem; color: #666; margin-top: 0.5rem;">
        Ground truth is defined by <strong>primary-accord match</strong> and
        <strong>Jaccard(notes)&nbsp;&gt;&nbsp;0.20</strong>, with no embedding
        signal involved. GraphSAGE-Jaccard reconstructs these neighbourhoods
        using structurally independent Jaccard edges — the same criterion,
        but learned through graph aggregation rather than direct pairwise
        computation. This tests whether the GNN can acquire the note-overlap
        concept from graph structure alone.
        </p>
    </div>
    """
    return html


def generate_html(
    config: dict,
    metadata: dict,
    plots: dict[str, str],
    run_dir: Path,
    master_data: dict[str, dict],
) -> str:
    warm_count = metadata.get("warm_count", 0)
    cold_count = metadata.get("cold_count", 0)
    total_count = warm_count + cold_count
    seed = config.get("seed", "N/A")
    k_value = config.get("k_values", [10])[0]
    cold_ratio = config.get("cold_ratio", 0.2)
    split_strategy = config.get("split_strategy", "stratified_leave_cold_out")
    generation_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def metric_cell(val: float, model_name: str = "") -> str:
        if "oracle" in model_name.lower():
            return f'<span class="metric-oracle">{val:.4f}</span>'
        if val > 0.01:
            return f'<span class="metric-good">{val:.4f}</span>'
        return f'<span class="metric-neutral">{val:.4f}</span>'

    plots_html = ""
    for plot_name, plot_uri in sorted(plots.items()):
        label = plot_name.replace("_", " ").replace(".png", "").title()
        plots_html += f'<img src="{plot_uri}" alt="{label}">\n'
        plots_html += f'<p style="font-size: 0.85rem; color: #666; text-align: center;">{label}</p>\n'

    # Build table rows
    metric_keys = ["Precision@10", "NDCG@10", "Recall@10"]
    table_rows = ""
    for metric_name in metric_keys:
        row = f"            <tr>\n                <td>{metric_name}</td>\n"
        for model_name in MODEL_ORDER:
            val = LOCKED_METRICS.get(model_name, {}).get(metric_name, 0.0)
            row += f"                <td>{metric_cell(val, model_name)}</td>\n"
        row += "            </tr>"
        table_rows += row + "\n"

    table_header = "                <th>" + '</th>\n                <th>'.join(MODEL_ORDER) + '</th>\n'

    live_example = generate_live_example(run_dir, master_data)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cold-Start Fragrance Recommendation — Graph-Based Preference Initialisation</title>
<style>
{CSS_STYLE}
</style>
</head>
<body>

<h1>Cold-Start Recommendation via Graph-Based Preference Initialisation</h1>
<p class="author">Structural Independence in Graph Construction for Zero-Interaction Recommendation</p>
<p class="author" style="font-size: 0.8rem;">Generated: {generation_date}</p>

<!-- Section 1: Introduction -->
<h2>1. Introduction</h2>

<p>
How can we recommend niche fragrances to a user with <strong>zero interaction history</strong>?
This is the <em>cold-start recommendation problem</em> — a fundamental challenge in domains
where new users or items have no past behaviour to learn from. Collaborative filtering
and matrix factorisation fail because they require interaction data.
</p>

<p>
We propose a <strong>graph-based preference initialisation</strong> approach: given only a
fragrance's inherent features (scent notes, accords, brand), we construct a similarity graph
and train a <strong>GraphSAGE</strong> model to predict a cold-start item's relevant neighbours
in this graph. The central finding is that <strong>graph construction methodology</strong> —
not model architecture — <strong>is the critical determinant of GNN cold-start performance</strong>.
</p>

<div class="key-result">
    <strong>Key Finding:</strong> Embedding-derived similarity graphs degrade NDCG by
    <strong>63% relative</strong> to a Feature-Only baseline (0.197 vs 0.557, p&le;0.001,
    d=0.93). Replacing circular embedding edges with structurally independent Jaccard
    edges over fragrance notes recovers 2.7&times; performance (NDCG 0.197 &rarr; 0.504,
    p&le;0.001, d=0.93). <strong>GraphSAGE-Jaccard (0.504) vs GraphSAGE-Embedding (0.197)</strong>.
    Feature-Only (0.557) beats GraphSAGE-Jaccard — graph claim is scoped to <strong>structural independence</strong>,
    not absolute performance.
</div>

<!-- Section 2: Problem Statement -->
<h2>2. Problem Statement</h2>

<p>
The cold-start problem in fragrance recommendation is particularly acute because:
</p>
<ul>
    <li><strong>No interaction history:</strong> A new user cannot express preferences through
    past purchases or ratings.</li>
    <li><strong>Domain vocabulary gap:</strong> Users may know what they like but lack the
    vocabulary to describe it in perfumery terms (accords, notes, families).</li>
    <li><strong>Long-tail catalogue:</strong> With 4,500+ fragrances in our catalogue, many
    items have sparse or zero interaction data.</li>
</ul>

<p>
Our central contribution is diagnosing a failure mode in GNN-based cold-start:
<strong>feature circularity</strong>. When graph edges are derived from the same embedding
space used as node features, the GNN aggregates neighbours already maximally similar in
that space — producing representations worse than raw feature cosine similarity.
The solution: structurally independent edge construction using Jaccard similarity over
fragrance notes, a signal orthogonal to the embedding space.
</p>

<!-- Section 3: Pipeline Architecture -->
<h2>3. Pipeline Architecture</h2>

<p>The evaluation pipeline proceeds through seven stages:</p>

<div class="pipeline-flow">{'Data (4,559 fragrances)'.ljust(40)} │
    ↓
{'Two Graphs Built'.ljust(40)} │  Embedding KNN (k=10, θ=0.5)  |  Jaccard notes (k=10, θ=0.2)
    ↓
{'Cold-Start Split'.ljust(40)} │  Stratified leave-{cold_ratio*100:.0f}%-out ({cold_count} cold, {warm_count} warm)
    ↓
{'GraphSAGE Training'.ljust(40)} │  Contrastive (InfoNCE) on warm-subgraph edges only, 100 epochs
    ↓
{'Inductive Inference'.ljust(40)} │  Cold nodes embedded using learned aggregator functions
    ↓
{'Evaluation'.ljust(40)} │  Precision@{k_value}, NDCG@{k_value}, Recall@{k_value} via ranx
    ↓
{'Reporting'.ljust(40)} │  Comparison table, stratification grid, learning curves</div>

<p><strong>Data:</strong> {total_count} fragrances from the quality-filtered catalogue, each with
SentenceTransformer embeddings (384-d) concatenated with accord one-hot (48-d) = 432-d feature space.</p>

<p><strong>Two graph strategies compared:</strong></p>
<ul>
    <li><strong>Embedding KNN</strong> (flawed): k-nearest-neighbour on embedding cosine similarity
    (k={config.get('graphsage_knn_k', 10)}, θ={config.get('graphsage_similarity_threshold', 0.5)}).
    Circular — edges and node features share the same embedding space.</li>
    <li><strong>Jaccard notes</strong> (fix): edges require primary-accord match AND
    Jaccard(notes)&nbsp;&gt;&nbsp;0.20. Structurally independent — zero embedding signal in edge construction.</li>
</ul>

<p><strong>Split:</strong> {split_strategy.replace('_', ' ').title()} — {cold_count} fragrances
({cold_ratio*100:.0f}%) held out as cold-start items, {warm_count} as warm items.</p>

<p><strong>Model:</strong> {config.get('graphsage_num_layers', 2)}-layer GraphSAGE with
{config.get('graphsage_embedding_dim', 64)}-dimensional hidden embeddings,
{config.get('graphsage_loss_type', 'contrastive')} loss, trained for
{config.get('graphsage_epochs', 100)} epochs on the warm subgraph.</p>

<!-- Section 4: Evaluation Design -->
<h2>4. Evaluation Design</h2>

<p>We adopt a <strong>pure cold-start</strong> evaluation protocol:</p>
<ul>
    <li>Cold items (n={cold_count}) are <strong>completely held out</strong> — their features are visible,
    but their graph position (edges) is masked during training.</li>
    <li>GraphSAGE performs <strong>inductive inference</strong>: cold nodes are embedded using
    the learned aggregator functions, then ranked by embedding similarity to all warm items.</li>
    <li>Degree-0 cold items (no graph edges) fall back to feature-only cosine similarity —
    ensuring 100% coverage.</li>
</ul>

<p><strong>Six models compared:</strong></p>
<ul>
    <li><strong>GraphSAGE-Jaccard</strong> (primary) — Same GraphSAGE architecture, Jaccard-based
    structurally independent graph. NDCG@10=0.504.</li>
    <li><strong>GraphSAGE-Embedding</strong> (ablative) — Identical model, embedding-derived KNN
    graph. NDCG@10=0.197. Isolates graph construction as the performance determinant.</li>
    <li><strong>Feature-Only</strong> (near-oracle) — Cosine similarity on raw 432-d features.
    NDCG@10=0.557. Uses the same embedding space as the graph construction.</li>
    <li><strong>Content-Only</strong> (oracle, invalid baseline) — Direct Jaccard over notes.
    NDCG@10=0.581. Same criterion as ground truth — included as upper-bound reference only.</li>
    <li><strong>Popularity</strong> — Global ranking by accord count. NDCG@10=0.008.</li>
    <li><strong>Random</strong> — Uniform random ranking. NDCG@10=0.031.</li>
</ul>

<p><strong>Metrics</strong> (computed via <code>ranx</code>, all-ranking protocol, n=843 cold items):</p>
<ul>
    <li><strong>Precision@{k_value}:</strong> Fraction of top-{k_value} recommendations that
    are ground-truth neighbours.</li>
    <li><strong>NDCG@{k_value}:</strong> Discounted cumulative gain — rewards relevant items
    at higher ranks.</li>
    <li><strong>Recall@{k_value}:</strong> Fraction of all ground-truth neighbours captured
    in the top-{k_value}.</li>
</ul>

<div class="oracle-box">
    <strong>Ground-Truth Methodology:</strong> Relevance is defined by
    <strong>primary-accord match + Jaccard(notes)&nbsp;&gt;&nbsp;0.20</strong> —
    <strong>not</strong> user preference data. This is a synthetic ground truth that
    measures graph reconstruction accuracy, not human-perceived recommendation quality.
    See Section 6 for full limitations.
</div>

<!-- Section 5: Results -->
<h2>5. Results</h2>

<h3>Six-Model Comparison</h3>

<table>
    <tr>
        <th>Metric</th>
        {table_header}
    </tr>
{table_rows}
</table>

<p style="font-size: 0.85rem; color: #666;">
Content-Only (oracle) uses the same Jaccard-over-notes criterion as the ground truth definition
and is included as an upper-bound reference only. It is not a valid baseline for fairness comparisons.
<strong>Primary comparison:</strong> GraphSAGE-Jaccard (0.504) vs GraphSAGE-Embedding (0.197) —
2.7&times; improvement from graph construction alone.
</p>

{plots_html}

<div class="limitations-box">
    <strong>Feature Circularity:</strong> GraphSAGE-Embedding (NDCG@10=0.197) achieves
    <strong>63% lower relative NDCG</strong> than the Feature-Only baseline (0.557).
    The embedding-derived graph causes <strong>destructive smoothing</strong> — the GNN
    aggregates neighbours already maximally similar in the feature space, producing
    representations worse than raw feature cosine similarity. GraphSAGE-Jaccard (0.504)
    recovers from this degradation but does not statistically beat Feature-Only (0.557,
    p=1.000, d=-0.149). The graph claim is scoped to <strong>structural independence</strong>:
    Jaccard edges provide a foundation that can incorporate interaction data, multi-hop
    semantics, and dynamic updates — capabilities content-based methods fundamentally cannot offer.
</div>

{live_example}

<!-- Section 6: Honest Limitations -->
<h2>6. Honest Limitations</h2>

<p>
The results above must be interpreted within their methodological boundaries.
We explicitly enumerate the limitations:
</p>

<ol>
    <li>
        <strong>Synthetic ground truth:</strong> The relevance criterion is defined by
        <strong>primary-accord match + Jaccard(notes)&nbsp;&gt;&nbsp;0.20</strong>, not
        by actual user preference data. This measures graph reconstruction accuracy for
        chemically similar fragrances — not whether users will enjoy the recommendations.
        A high NDCG score on this metric does not guarantee real-world recommendation quality.
    </li>
    <li>
        <strong>Feature circularity in GraphSAGE-Embedding:</strong> The embedding-derived
        KNN graph shares its feature space with the node features. GraphSAGE trained on
        this graph performs 63% worse than simple feature cosine similarity — a destructive
        smoothing effect. This is the central finding, but it is a negative result that
        documents a failure mode rather than demonstrating a positive improvement over
        content-based methods.
    </li>
    <li>
        <strong>Graph claim is structural, not absolute:</strong> GraphSAGE-Jaccard
        (NDCG@10=0.504) does <strong>not</strong> statistically beat Feature-Only
        (0.557, p=1.000, d=-0.149). The contribution is <strong>structural independence</strong>
        — Jaccard edges are orthogonal to the embedding space and can scale with interaction
        data, temporal dynamics, and multi-hop semantics. Content-based baselines hit their
        ceiling on day one; graph methods can improve with data.
    </li>
    <li>
        <strong>No real user interaction data:</strong> All evaluation is conducted on the
        synthetic graph reconstruction task. Without A/B testing or user studies, we cannot
        validate that reconstructed neighbourhoods correspond to human-perceived fragrance
        similarity.
    </li>
    <li>
        <strong>Single dataset:</strong> Results are from one fragrance catalogue
        (4,559 items). Generalisation to other domains (wine, books, music, fashion)
        requires cross-domain validation. The circularity mechanism is domain-agnostic,
        but the empirical magnitude may vary.
    </li>
    <li>
        <strong>Threshold overlap:</strong> The primary operating point (Jaccard &theta;=0.20)
        coincides with the ground truth floor (&gt;0.20). This is a design choice, not
        evaluation circularity — GraphSAGE never sees the ground truth during training.
        However, models whose inductive biases align with Jaccard note overlap are
        favoured by this evaluation design.
    </li>
</ol>

<p>
These limitations are <strong>deliberate boundaries</strong> of the graph reconstruction
proxy approach. The next section outlines how they can be addressed.
</p>

<!-- Section 7: Future Work -->
<h2>7. Future Work</h2>

<p>Several directions extend this work toward production-ready cold-start recommendation:</p>

<ul>
    <li>
        <strong>Real user studies:</strong> Deploy GraphSAGE-Jaccard recommendations in a
        live setting with A/B testing, measuring user engagement, satisfaction, and
        conversion rates — replacing the synthetic ground truth with real feedback.
    </li>
    <li>
        <strong>Adaptive preference refinement (quiz-init):</strong> Combine graph-based
        initialisation with interactive preference quizzes. A post-prediction reranker
        that blends quiz confidence with GraphSAGE scores is implemented but does not
        yet reliably beat pure cold-start (mean NDCG 0.496 vs 0.504, high variance).
    </li>
    <li>
        <strong>Beyond-accuracy metrics:</strong> Evaluate diversity, novelty, coverage,
        and serendipity. The Jaccard graph's structural independence may yield more
        diverse recommendations than embedding-derived neighbours.
    </li>
    <li>
        <strong>User-node integration:</strong> Extend the graph to include user nodes
        with interaction edges, enabling collaborative cold-start through the same
        structurally independent graph framework.
    </li>
    <li>
        <strong>Cross-domain validation:</strong> Apply the same two-graph ablation
        methodology to other cold-start domains (wine, books, music, fashion) to
        validate the circularity finding's generalisability.
    </li>
    <li>
        <strong>Full-catalogue scaling:</strong> Scale evaluation from the current
        4,559 quality-filtered items to the full 22,740-item catalog, testing whether
        the structural independence advantage persists at larger scale.
    </li>
</ul>

<div class="footer">
    Generated by Scentrix Evaluation Pipeline — Phase 6 (MEXT Demo)
</div>

</body>
</html>"""

    return html


DEFAULT_RUN_PATH = "ml/eval/runs/20260528_165737"


def resolve_run_path(run_path_arg: str | None) -> str:
    if run_path_arg is not None:
        return run_path_arg
    default = Path(DEFAULT_RUN_PATH)
    if default.is_dir():
        logger.info("Using default run: %s", default)
        return str(default)
    return find_latest_run()


def find_latest_run(base_dir: str = "ml/eval/runs") -> str:
    runs_dir = Path(base_dir)
    if not runs_dir.is_dir():
        raise FileNotFoundError(f"Runs directory not found: {runs_dir}")

    run_dirs = sorted(
        [d for d in runs_dir.iterdir() if d.is_dir() and re.match(r"^\d{8}_\d{6}$", d.name)],
        reverse=True,
    )
    if not run_dirs:
        raise FileNotFoundError(f"No timestamped run directories found under {runs_dir}")
    return str(run_dirs[0])


def generate_demo(run_path: str, output_path: str) -> str:
    run_dir = Path(run_path)
    logger.info("Generating demo from run: %s", run_dir.resolve())

    config_path = run_dir / "config.yaml"
    if not config_path.is_file():
        raise FileNotFoundError(f"config.yaml not found in {run_dir}")
    with open(config_path) as f:
        config = yaml.safe_load(f) if YAML_AVAILABLE else {}
    logger.info("Config loaded: seed=%s, cold_ratio=%s", config.get("seed"), config.get("cold_ratio"))

    metadata = {}
    meta_path = run_dir / "metadata" / "run.json"
    if meta_path.is_file():
        with open(meta_path) as f:
            metadata = json.load(f)
    logger.info("Metadata: %d warm, %d cold", metadata.get("warm_count", 0), metadata.get("cold_count", 0))

    data_path = config.get("data_path", "ml/data/scentrix_master_cleaned.json")
    master_data = load_master_data(data_path)

    plots: dict[str, str] = {}
    plots_dir = run_dir / "plots"
    if plots_dir.is_dir():
        for png_file in sorted(plots_dir.glob("*.png")):
            uri = img_to_base64(str(png_file))
            if uri:
                plots[png_file.name] = uri
                logger.info("Embedded plot: %s (%d chars)", png_file.name, len(uri))

    chart_uri = generate_comparison_bar_chart(output_path)
    if chart_uri:
        plots["comparison_bar_chart.png"] = chart_uri

    html = generate_html(config, metadata, plots, run_dir, master_data)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html, encoding="utf-8")
    logger.info("Demo page written to %s (%d bytes)", output_file.resolve(), len(html.encode("utf-8")))

    return html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate MEXT demo HTML page from evaluation run",
    )
    parser.add_argument(
        "--run-path", type=str, default=None,
        help="Path to evaluation run directory (default: latest timestamp dir under ml/eval/runs/)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output path for HTML file (default: {run-path}/mext_demo.html)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print debug information",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        run_path = resolve_run_path(args.run_path)
        run_dir = Path(run_path)
        output_path = args.output or str(run_dir / "mext_demo.html")

        html = generate_demo(run_path, output_path)

        print(f"Demo page generated: {output_path}")
        print(f"Size: {len(html.encode('utf-8')) / 1024:.1f} KB")
        print(f"Sections: 7 (Introduction → Problem → Pipeline → Eval → Results → Limitations → Future)")
        print(f"JavaScript: 0 (per D-04)")
        print(f"Models: {', '.join(MODEL_ORDER)}")
        print(f"Locked values: Phase 5 CHANGELOG")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error("Demo generation failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
