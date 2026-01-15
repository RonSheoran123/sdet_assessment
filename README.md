# Swiggy Chatbot AI Validation Framework

This repository contains a hybrid Quality Assurance framework designed to validate AI-powered customer support interactions within a CI/CD environment. It addresses the specific challenge of testing Large Language Models (LLMs) by balancing computational efficiency with semantic accuracy.



## Architecture Overview

Traditional assertion-based testing is insufficient for LLMs due to the non-deterministic nature of generative text. This framework utilizes a **Hybrid Routing Strategy** that categorizes user intent into two tiers, applying the most appropriate validation method for each.

### Tier A: Deterministic Validation (Preset Queries)
* **Scope:** High-volume, repetitive queries (e.g., Order Status, Missing Items).
* **Methodology:** Uses lightweight, deterministic heuristics to ensure speed and low cost.
* **Components:**
    * **Regex Assertions:** Enforces strict compliance for mandatory data fields (e.g., Order IDs) and safety guardrails.
    * **Cosine Similarity:** Validates semantic intent against a golden reference using Bi-Encoder embeddings.
    * **Logical Consistency (NLI):** Probabilistically checks for logical contradictions (e.g., negation errors) using Cross-Encoders.

### Tier B: Probabilistic Validation (Complex Queries)
* **Scope:** Low-volume, open-ended queries (e.g., Behavioral complaints, complex escalations).
* **Methodology:** Uses LLM-based evaluation to assess reasoning and tone.
* **Components:**
    * **LLM-as-a-Judge:** Utilizes GPT-4 to grade responses based on a specific rubric (Empathy, Policy Adherence, Resolution Logic).

| Feature | Tier A: Preset Queries | Tier B: Complex Queries |
| :--- | :--- | :--- |
| **Primary Use Case** | "Where is my order?", "Missing Item" | "Rude delivery partner", "App errors" |
| **Validation Logic** | Deterministic (Math-based) | Probabilistic (Reasoning-based) |
| **Technique** | Regex + Cosine Similarity + NLI | LLM-as-a-Judge (GPT-4) |
| **Cost Profile** | Negligible | High (Per-token API cost) |
| **Latency** | Milliseconds | Seconds |

## Operational Features

### Pipeline Optimization (Ops Strategy)
To optimize CI/CD runtime and API costs, the framework operates in two distinct modes:

1.  **Online Mode (Commit-Time):**
    * Designed for rapid feedback loops.
    * Executes deterministic checks (Regex/Cosine) on all cases.
    * Performs a **10% random sample** of heavy Logic Audits (NLI) to catch regressions without stalling the build.
    * Skips LLM Judge calls.

2.  **Offline Mode (Nightly Regression):**
    * Designed for maximum coverage before release.
    * Executes the full test suite, including 100% of NLI Logic Audits and GPT-4 Judge evaluations.

### Safety & Guardrails
The framework enforces strict regex patterns to prevent critical failures in high-risk scenarios, such as safety incidents or fraud reporting. This ensures the model does not hallucinate inappropriate resolutions (e.g., offering coupons during a harassment report).

## Repository Structure

```text
.
├── test_swiggy_final.py    # Main Test Runner (Pytest implementation)
├── test_data.json          # Data-Driven Test Cases (Mapped to UI Options)
├── requirements.txt        # Python Dependencies
└── README.md               # Documentation
