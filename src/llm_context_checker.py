"""
TrendSignal MVP - LLM Context Checker
Arfolyamhatas-alapu scoring GPT-4o-mini segitsegevel.

- Minden enum mezo: diszkret, elore definalt ertekek
- Float konverzio Python kodban (IMPACT_SCORE_MAP) - nem az LLM adja
- temperature=0, seed=42, response_format=json_object
- ThreadPoolExecutor a parhuzamos futashoz
- Fallback: ha LLM fail -> FinBERT score marad active_score-nak

Version: 1.0 | 2026-03-02
Spec: TrendSignal_LLM_Context_Checker_v2.1.docx
"""

import json
import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)


# ==========================================
# SCORE CONVERSION MAPS (spec 2.3)
# ==========================================

IMPACT_SCORE_MAP = {
    # strong_up: teljes skála (1-5)
    ('strong_up',   5): +1.00,  ('strong_up',   4): +0.85,
    ('strong_up',   3): +0.70,  ('strong_up',   2): +0.55,
    ('strong_up',   1): +0.40,
    # up: teljes skála (1-5)
    ('up',          5): +0.75,  ('up',          4): +0.60,
    ('up',          3): +0.45,  ('up',          2): +0.32,
    ('up',          1): +0.20,
    # neutral: teljes skála (1-5), szimmetrikus 0 körül
    ('neutral',     5): +0.10,  ('neutral',     4): +0.05,
    ('neutral',     3):  0.00,
    ('neutral',     2): -0.05,  ('neutral',     1): -0.10,
    # down: teljes skála (1-5), up tükörképe
    ('down',        5): -0.75,  ('down',        4): -0.60,
    ('down',        3): -0.45,  ('down',        2): -0.32,
    ('down',        1): -0.20,
    # strong_down: teljes skála (1-5), strong_up tükörképe
    ('strong_down', 5): -1.00,  ('strong_down', 4): -0.85,
    ('strong_down', 3): -0.70,  ('strong_down', 2): -0.55,
    ('strong_down', 1): -0.40,
}

CONFIDENCE_MAP = {'low': 0.50, 'medium': 0.75, 'high': 0.92}

PRICED_IN_PENALTY = 0.55    # score * 0.55 ha priced_in=True

# Valid enum values for validation
VALID_PRICE_IMPACT = {'strong_up', 'up', 'neutral', 'down', 'strong_down'}
VALID_IMPACT_DURATION = {'hours', 'days', 'weeks', 'permanent'}
VALID_CATALYST_TYPE = {'earnings', 'macro', 'regulatory', 'corporate_action', 'analyst', 'sector', 'other'}
VALID_CONFIDENCE = {'low', 'medium', 'high'}

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


# ==========================================
# RESULT DATACLASS
# ==========================================

@dataclass
class LLMCheckResult:
    """LLM Context Checker eredmenye egy hir itemre."""
    relevant: bool = False
    price_impact: str = 'neutral'       # enum
    impact_level: int = 3               # 1-5
    impact_duration: str = 'days'       # enum
    catalyst_type: str = 'other'        # enum
    priced_in: bool = False
    confidence: str = 'low'             # enum
    reason: str = ''                    # max 10 szo
    llm_score: float = 0.0              # compute_llm_score() eredmenye
    latency_ms: int = 0
    success: bool = False               # False = API hiba -> fallback FinBERT-re


# ==========================================
# SYSTEM PROMPT (spec 3.2)
# ==========================================

_SYSTEM_PROMPT = """\
You are a short-term stock price impact analyst (2-6 hour horizon).
Answer ONLY with a JSON object matching EXACTLY this schema.
ALLOWED VALUES:
  price_impact:    "strong_up"|"up"|"neutral"|"down"|"strong_down"
  impact_level:    integer 1-5  (1=minimal, 5=extreme)
  impact_duration: "hours"|"days"|"weeks"|"permanent"
  catalyst_type:   "earnings"|"macro"|"regulatory"|"corporate_action"|"analyst"|"sector"|"other"
  confidence:      "low"|"medium"|"high"
  relevant:        true or false
  priced_in:       true or false
  reason:          string, max 10 words
Do NOT use any other values. Do NOT add markdown. Do NOT include explanations outside the JSON."""

# Few-shot examples (spec 3.2)
_FEW_SHOT_EXAMPLES = """\
EXAMPLES:
  Title: "Apple Q1 revenue $124B, beats $121B estimate"
  -> {"relevant":true,"price_impact":"up","impact_level":3,"impact_duration":"days","catalyst_type":"earnings","priced_in":false,"confidence":"high","reason":"earnings beat, moderate surprise"}

  Title: "Fed holds rates at 5.25%, as expected by markets"
  -> {"relevant":false,"price_impact":"neutral","impact_level":1,"impact_duration":"hours","catalyst_type":"macro","priced_in":true,"confidence":"high","reason":"fully priced in, no surprise"}

  Title: "Tesla recalls 200k vehicles over autopilot defect"
  -> {"relevant":true,"price_impact":"down","impact_level":4,"impact_duration":"weeks","catalyst_type":"regulatory","priced_in":false,"confidence":"high","reason":"unexpected recall, reputational risk"}

  Title: "OTP Bank Q3 profit +12%, estimate was +15%"
  -> {"relevant":true,"price_impact":"down","impact_level":2,"impact_duration":"days","catalyst_type":"earnings","priced_in":false,"confidence":"medium","reason":"miss vs expectation despite positive headline"}

"""


# ==========================================
# MAIN CLASS
# ==========================================

class LLMContextChecker:
    """
    LLM-alapu arfolyamhatas scorer.

    Parhuzamos futtas (ThreadPoolExecutor), OpenRouter API-n keresztul.
    FinBERT fallback: ha LLM call fail, active_score = finbert_score marad.
    """

    def __init__(
        self,
        api_key: str,
        model: str = 'openai/gpt-4o-mini',
        timeout: float = 3.0,
        max_concurrent: int = 5,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_concurrent = max_concurrent

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def check_single(
        self,
        news_item,
        ticker_symbol: str,
        ticker_name: str,
        current_price: Optional[float] = None,
    ) -> LLMCheckResult:
        """Egy hir LLM scoring-ja."""
        messages = self._build_messages(news_item, ticker_symbol, ticker_name, current_price)
        t_start = time.time()
        try:
            raw = self._call_api(messages)
            latency_ms = int((time.time() - t_start) * 1000)
            result = self._parse_response(raw)
            result.latency_ms = latency_ms
            return result
        except Exception as e:
            latency_ms = int((time.time() - t_start) * 1000)
            logger.warning(f"[LLM] check_single failed: {e}")
            return LLMCheckResult(success=False, latency_ms=latency_ms)

    def check_batch(
        self,
        news_items: List,
        ticker_symbol: str,
        ticker_name: str,
        current_price: Optional[float] = None,
    ) -> List[LLMCheckResult]:
        """
        Batch LLM scoring ThreadPoolExecutor-ral.
        Sorrendet megorizve adja vissza az eredmenyeket.
        """
        if not news_items:
            return []

        workers = min(self.max_concurrent, len(news_items))
        results = [None] * len(news_items)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_idx = {
                executor.submit(
                    self.check_single,
                    item,
                    ticker_symbol,
                    ticker_name,
                    current_price,
                ): idx
                for idx, item in enumerate(news_items)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    logger.warning(f"[LLM] batch item {idx} failed: {e}")
                    results[idx] = LLMCheckResult(success=False)

        return results

    # ------------------------------------------------------------------
    # SCORE COMPUTATION (spec 2.4)
    # ------------------------------------------------------------------

    def compute_llm_score(self, result: LLMCheckResult) -> float:
        """
        Enum ertekekbol float score szamitasa (spec 2.4).
        Az LLM soha nem ad float-ot - ez Python konverzio.
        """
        if not result.relevant:
            return 0.0
        base = IMPACT_SCORE_MAP.get((result.price_impact, result.impact_level), 0.0)
        if result.priced_in:
            base *= PRICED_IN_PENALTY
        return round(base, 4)

    # ------------------------------------------------------------------
    # INTERNAL: PROMPT BUILDING
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        news_item,
        ticker_symbol: str,
        ticker_name: str,
        current_price: Optional[float] = None,
    ) -> list:
        """OpenAI-format messages lista epitese."""
        title = getattr(news_item, 'title', '') or ''
        description = getattr(news_item, 'description', '') or ''

        price_context = ''
        if current_price:
            price_context = f"  Current price: {current_price:.2f}\n"

        user_content = (
            f"{_FEW_SHOT_EXAMPLES}"
            f"NOW ANALYZE:\n"
            f"  Ticker: {ticker_symbol} ({ticker_name})\n"
            f"{price_context}"
            f"  Title: {title}\n"
            f"  Description: {description[:300] if description else '(none)'}\n"
        )

        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    # ------------------------------------------------------------------
    # INTERNAL: API CALL
    # ------------------------------------------------------------------

    def _call_api(self, messages: list) -> str:
        """OpenRouter API hivas. Visszaad raw JSON stringet."""
        if not self.api_key:
            raise ValueError("LLM API key (OPENROUTER_API_KEY) not set")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "seed": 42,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            OPENROUTER_API_URL,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        return content

    # ------------------------------------------------------------------
    # INTERNAL: RESPONSE PARSING
    # ------------------------------------------------------------------

    def _parse_response(self, response_text: str) -> LLMCheckResult:
        """
        JSON parse + enum validacio + score szamitas.
        Parse/validacioa hiba eseten success=False.
        """
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.warning(f"[LLM] JSON parse error: {e} | raw: {response_text[:200]}")
            return LLMCheckResult(success=False)

        # Validate and extract fields
        try:
            relevant = bool(data.get('relevant', False))
            price_impact = str(data.get('price_impact', 'neutral'))
            impact_level_raw = data.get('impact_level', 3)
            impact_duration = str(data.get('impact_duration', 'days'))
            catalyst_type = str(data.get('catalyst_type', 'other'))
            priced_in = bool(data.get('priced_in', False))
            confidence = str(data.get('confidence', 'low'))
            reason = str(data.get('reason', ''))[:100]

            # Convert impact_level to int (LLM might return string)
            impact_level = int(impact_level_raw) if str(impact_level_raw).isdigit() else 3
            impact_level = max(1, min(5, impact_level))  # clamp 1-5

            # Enum validation
            if price_impact not in VALID_PRICE_IMPACT:
                logger.warning(f"[LLM] Invalid price_impact: {price_impact}")
                return LLMCheckResult(success=False)
            if impact_duration not in VALID_IMPACT_DURATION:
                logger.warning(f"[LLM] Invalid impact_duration: {impact_duration}")
                return LLMCheckResult(success=False)
            if catalyst_type not in VALID_CATALYST_TYPE:
                catalyst_type = 'other'  # soft fallback
            if confidence not in VALID_CONFIDENCE:
                confidence = 'low'  # soft fallback

        except Exception as e:
            logger.warning(f"[LLM] Field extraction error: {e}")
            return LLMCheckResult(success=False)

        result = LLMCheckResult(
            relevant=relevant,
            price_impact=price_impact,
            impact_level=impact_level,
            impact_duration=impact_duration,
            catalyst_type=catalyst_type,
            priced_in=priced_in,
            confidence=confidence,
            reason=reason,
            success=True,
        )
        result.llm_score = self.compute_llm_score(result)
        return result


# ==========================================
# MODULE TEST
# ==========================================

if __name__ == "__main__":
    print("[OK] LLM Context Checker module loaded")
    print(f"  Model: openai/gpt-4o-mini")
    print(f"  IMPACT_SCORE_MAP entries: {len(IMPACT_SCORE_MAP)}")
    print(f"  Valid price_impact values: {VALID_PRICE_IMPACT}")
    print(f"  Valid impact_duration values: {VALID_IMPACT_DURATION}")

    # Test score computation
    from dataclasses import replace
    test = LLMCheckResult(relevant=True, price_impact='strong_up', impact_level=5,
                          impact_duration='days', catalyst_type='earnings',
                          priced_in=False, confidence='high', success=True)
    checker = LLMContextChecker(api_key="test")
    score = checker.compute_llm_score(test)
    print(f"  Test score (strong_up, level=5, not priced_in): {score}")  # expected: 1.0

    test_priced = LLMCheckResult(relevant=True, price_impact='up', impact_level=3,
                                  impact_duration='hours', catalyst_type='macro',
                                  priced_in=True, confidence='high', success=True)
    score2 = checker.compute_llm_score(test_priced)
    print(f"  Test score (up, level=3, priced_in=True): {score2}")  # expected: 0.45*0.55 = 0.2475
