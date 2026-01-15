import pytest
import json
import re
import os
import random
from openai import OpenAI
from sentence_transformers import SentenceTransformer, CrossEncoder
from sklearn.metrics.pairwise import cosine_similarity

# --- CONFIGURATION & SETUP ---
client = OpenAI() # Assumes env var OPENAI_API_KEY is set

# Pipeline Control:
# "ONLINE" => Fast Mode (Commit-time). Runs cheap tests + 10% random logic audit.
# "OFFLINE" => Deep Mode (Nightly). Runs ALL tests including full NLI & Judge.
PIPELINE_MODE = os.getenv("PIPELINE_MODE", "ONLINE")
AUDIT_SAMPLE_RATE = 0.10 

# Loading Fast Model (Bi-Encoder) - Always needed for Cosine Similarity
print("[System] Loading Fast Embedding Model...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Lazy Load Variable for Heavy Model (Cross-Encoder)
_nli_model = None

def get_nli_model():
    """Lazy loader for the heavy NLI model to save startup time in Online mode."""
    global _nli_model
    if _nli_model is None:
        print("\n[System] 🐢 Loading Heavy NLI Model for Audit (This takes a moment)...")
        _nli_model = CrossEncoder('cross-encoder/nli-distilroberta-base')
    return _nli_model

# Load Test Data
with open('test_data.json', 'r') as f:
    TEST_CASES = json.load(f)


# --- Dummy Chatbot ---
def get_bot_response(query, context_type):
    """Simulates the Swiggy Chatbot Logic"""
    system_prompt = "You are Swiggy Support."
    
    # Agent Handoff
    system_prompt += " CRITICAL: If the user asks for an 'Agent', 'Human', or 'Person', strictly say: 'Transferring you to a support agent now. Please wait.'"
    
    if context_type == "preset":
        system_prompt += " Follow standard SOPs. Be concise. If safety issue, escalate immediately."
    else:
        system_prompt += " Be empathetic and try to de-escalate the situation."
        
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        temperature=0.7 
    )
    return response.choices[0].message.content


# --- Validator Functions ---
def check_keywords(text, required, forbidden):
    """Tier 1: Fast Deterministic Regex Check -> First check to mark obvious errors"""
    errors = []
    for word in required:
        if not re.search(word, text, re.IGNORECASE):
            errors.append(f"Missing mandatory keyword: '{word}'")
    
    for word in forbidden:
        if re.search(word, text, re.IGNORECASE):
            errors.append(f"Found forbidden keyword: '{word}'")
            
    return len(errors) == 0, errors

def check_similarity(actual, expected_text, threshold=0.75):
    """Tier 2: Vector Semantic Similarity (Cheap Math) -> Second check"""
    vec_actual = embedding_model.encode([actual])
    vec_expected = embedding_model.encode([expected_text])
    score = cosine_similarity(vec_actual, vec_expected)[0][0]
    return score >= threshold, score

def check_logical_consistency(actual_response, expected_intent):
    """Tier 2.5: Deep Logic Audit (Expensive NLI)"""
    model = get_nli_model() # Trigger lazy load
    scores = model.predict([(actual_response, expected_intent)])
    
    # Labels: 0=Contradiction, 1=Entailment, 2=Neutral
    label_mapping = ['contradiction', 'entailment', 'neutral']
    predicted_label = label_mapping[scores[0].argmax()]
    
    if predicted_label == 'contradiction':
        return False, f"Logical Contradiction detected! (Score: {scores[0][0]:.2f})"
    return True, "Logic Pass"

def check_with_judge(query, response):
    """Tier 3: LLM Judge (Most Expensive, Slow)"""
    prompt = f"""
    Evaluate this Swiggy support interaction.
    "pass": true only if ALL rubric items are satisfied. Otherwise false.
    User: {query}
    Bot: {response}
    
    Rubric:
    1. Did the bot understand the core frustration?
    2. Was the tone appropriate?
    3. Did it offer a valid path forward?
    
    Return JSON: {{"pass": true/false, "reason": "..."}}
    """
    
    res = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    # Sanitizing Output
    raw_content = res.choices[0].message.content
    clean_json = raw_content.replace("```json", "").replace("```", "").strip()
    
    # Parsing
    try:
        return json.loads(clean_json)
    except json.JSONDecodeError:
        return {"pass": False, "reason": f"Judge returned invalid JSON: {raw_content}"}


# --- Probabistic Test Runner ---

@pytest.mark.parametrize("test_case", TEST_CASES)
def test_swiggy_support_flow(test_case):
    print(f"\nRunning {test_case['id']} - {test_case['intent']}")
    
    # A) Generate Response
    actual_response = get_bot_response(test_case['user_query'], test_case['category'])
    
    # B) Select Strategy
    if test_case['category'] == 'preset':
        # --- PATH 1: PRESET (Fast & Deterministic, Covers majority cases) ---
        
        # 1) Keywords
        kw_pass, kw_errors = check_keywords(
            actual_response, 
            test_case['required_keywords'], 
            test_case['forbidden_keywords']
        )
        assert kw_pass, f"Keyword Fail: {kw_errors}"
        
        # 2) Semantic Similarity (Fast)
        sim_pass, score = check_similarity(actual_response, test_case['expected_semantic_meaning'])
        assert sim_pass, f"Semantic Fail (Score: {score:.2f})."

        # 3) Logic Audit (NLI) - Random Sample or Offline Only
        should_audit = False
        if PIPELINE_MODE == "OFFLINE":
            should_audit = True
        elif random.random() < AUDIT_SAMPLE_RATE:
            should_audit = True
            
        if should_audit:
            print(f"   [AUDIT - Running NLI Logic Check...")
            logic_pass, logic_msg = check_logical_consistency(actual_response, test_case['expected_semantic_meaning'])
            assert logic_pass, f"NLI Logic Fail: {logic_msg}"
        else:
            print(f"   [SKIP - NLI Check skipped for speed.")

    elif test_case['category'] == 'others':
        # --- PATH 2: OTHERS (Complex & Expensive) ---
        
        # Optimization - Only run expensive Judge in Offline mode or if specifically required
        if PIPELINE_MODE == "OFFLINE":
             eval_result = check_with_judge(test_case['user_query'], actual_response)
             assert eval_result['pass'], f"Judge Fail: {eval_result['reason']}"
        else:
            pytest.skip("Skipping LLM Judge in ONLINE mode to save costs.")
