# sdet_assessment

Strategy: The Hybrid AI Validation Framework
1. Executive Strategy: "Cheap Math" vs. "Expensive Reasoning"
Testing an LLM is fundamentally different from testing a traditional API. We cannot rely on deterministic string matching (assert output == "refund processed") because the output varies in tone, length, and phrasing every time.
For a high-scale platform like Swiggy, a "one-size-fits-all" testing strategy is inefficient. We cannot afford to burn expensive GPU resources or pay GPT-4 API costs for trivial queries, nor can we rely on simple keywords for complex escalations.
To solve this, I designed a Hybrid Validation Framework that routes tests based on complexity:
Tier A: Deterministic Validation (The "Preset" Flow) Target: 80-90% of traffic (e.g., "Where is my order?", "Missing Item") These queries have a known "Golden Intent." We use lightweight, high-speed mathematical checks:
Regex Guardrails: Instant, zero-cost checks for mandatory data (e.g., ensuring an Order ID is requested) and safety (e.g., banning "coupon" offers during safety incidents).
Vector Similarity (Bi-Encoders): We compare the meaning of the response to a reference answer using Cosine Similarity. If the score is > 0.75, the bot is on-script.
Logic Audits (NLI): To fix the "Negation Blind Spot" (where "I can help" and "I cannot help" look mathematically similar), we use a Cross-Encoder to detect logical contradictions.
Tier B: Probabilistic Reasoning (The "Others" Flow) Target: 10-20% of traffic (e.g., complex rants, multi-intent complaints) Math fails here because user inputs are unpredictable. We use LLM-as-a-Judge (GPT-4) to act as a semantic grader, evaluating the response against a rubric of empathy, policy compliance, and resolution logic.
2. Ops Optimization: "Statistical Audit" Approach
The Challenge: The Cost of Intelligence Running a Cross-Encoder (NLI) or GPT-4 for every single test case in a regression suite of 5,000+ tests would explode our CI/CD runtime from minutes to hours and drastically increase API costs.
The Solution: Probabilistic Sampling To balance Confidence vs. Velocity, I implemented a tiered execution strategy controlled by environment variables (PIPELINE_MODE):
The "Fast Path" (Commit-Time Pipeline):
Goal: Instant feedback for developers (~2 min runtime).
Method: Runs deterministic checks (Regex + Cosine) on all tests.
Sampling: We employ a 10% Probabilistic Audit. For every 10 tests, 1 is randomly selected for a "Deep Logic Check" (NLI). This provides statistical confidence that no major logical regressions are being introduced without stalling the build.
The "Deep Path" (Nightly/Offline Pipeline):
Goal: Maximum quality assurance before release.
Execution: Runs with PIPELINE_MODE=OFFLINE. Every single test case undergoes the full battery of evaluations, including Cross-Encoder NLI logic checks and GPT-4 qualitative grading.
3. Engineering Limitations & Trade-offs
A. The "Who Watches the Watchmen?" Problem Using GPT-4 to judge GPT-3.5 introduces a layer of non-determinism. If the Judge model hallucinates or misinterprets the rubric, we get a "False Positive" failure. We mitigate this by setting the Judge's temperature to 0.0, but this makes the CI pipeline inherently "flakier" than traditional code pipelines.
B. Maintenance Overhead The Deterministic Tier relies on specific keywords and intents. If the Product team rebrands "Swiggy Money" to "Swiggy Wallet," our regex rules will break even if the bot is working perfectly. This creates a tighter coupling between Test Data and Product Copy than is ideal, requiring the QA team to be in sync with Product updates.
C. The "Negation" Blind Spot (Vector Limitation) Standard vector embeddings are excellent at matching topics but struggle with logic. Mathematically, "The refund is processed" and "The refund is not processed" are nearly identical vectors. While our NLI (Natural Language Inference) check fixes this, it is computationally expensive, which is why we only apply it probabilistically in the fast pipeline.
4. Conclusion
This framework prioritizes Safety and Speed for the bulk of our users while reserving Intelligence for the complex edge cases. It moves Swiggy's QA from fragile string matching to a robust, semantic-aware quality gate, accepting the trade-off of slightly higher maintenance for significantly higher confidence in AI behavior.


