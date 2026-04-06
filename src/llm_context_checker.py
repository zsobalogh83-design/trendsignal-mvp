"""
TrendSignal MVP - LLM Context Checker v2
Meglepetes-alapu scoring GPT-4o-mini segitsegevel.

v2 valtozasok (2026-04):
  - Cikktipus szures: institutional_filing, opinion, tangential → score = 0
  - Meglepetes-detekció: "jobb/rosszabb a vartnal?" kérdés, nem "jo-e a hir?"
  - is_first_report bonus: breaking news 1.3x szorzó
  - directly_about check: indirekt/szektoros cikkek score = 0
  - Backward-compat propertyk: price_impact, catalyst_type, priced_in, impact_level

- Minden enum mezo: diszkret, elore definalt ertekek
- Float konverzio Python kodban - nem az LLM adja
- temperature=0, seed=42, response_format=json_object
- ThreadPoolExecutor a parhuzamos futashoz
- Fallback: ha LLM fail -> FinBERT score marad active_score-nak

Version: 2.0 | 2026-04
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
# SCORE CONVERSION (v2)
# ==========================================

# Surprise direction → base score irány
SURPRISE_DIRECTION_SCORE = {
    'beat':        +1.0,
    'miss':        -1.0,
    'in_line':      0.0,
    'no_baseline':  0.0,
    'na':           0.0,
}

# Confidence szorzó (változatlan)
CONFIDENCE_MAP = {'low': 0.50, 'medium': 0.75, 'high': 0.92}

# Breaking news bonus
FIRST_REPORT_MULTIPLIER = 1.3

# Cikktípusok amelyek nem érdemelnek score-t
NON_SCORING_ARTICLE_TYPES = {
    'filing',           # intézményi tartás-változás, SEC filing
    'opinion',          # "Should you buy?", elemzés, roundup
    'tangential',       # a cikk más cégről szól, csak megemlíti a tickert
}

# Valid enum értékek
VALID_SURPRISE_DIRECTION = {'beat', 'miss', 'in_line', 'no_baseline', 'na'}
VALID_ARTICLE_TYPE = {
    'earnings', 'guidance', 'product', 'regulatory',
    'macro', 'filing', 'opinion', 'tangential', 'other_event',
}
VALID_CONFIDENCE = {'low', 'medium', 'high'}

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Backward-compat: surprise_direction → régi llm_price_impact értékek
_SURPRISE_TO_PRICE_IMPACT = {
    'beat':        'up',
    'miss':        'down',
    'in_line':     'neutral',
    'no_baseline': 'neutral',
    'na':          'neutral',
}

# Backward-compat: article_type → régi llm_catalyst_type értékek
_ARTICLE_TO_CATALYST = {
    'earnings':    'earnings',
    'guidance':    'earnings',
    'product':     'corporate_action',
    'regulatory':  'regulatory',
    'macro':       'macro',
    'filing':      'other',
    'opinion':     'other',
    'tangential':  'other',
    'other_event': 'other',
}


# ==========================================
# RESULT DATACLASS
# ==========================================

@dataclass
class LLMCheckResult:
    """
    LLM Context Checker v2 eredmenye.
    Backward-compat propertyk biztositjak, hogy a news_collector.py
    valtozas nelkul mukodjon tovabb.
    """
    # --- v2 mezők ---
    score_worthy:       bool  = False        # False → score = 0.0 (pl. opinion, filing)
    article_type:       str   = 'other_event'
    directly_about:     bool  = False        # False → a cikk nem erről a cégről szól
    is_first_report:    bool  = False        # True → breaking news (1.3x)
    surprise_direction: str   = 'no_baseline'
    surprise_magnitude: int   = 1            # 1-5, csak beat/miss esetén értelmes
    confidence:         str   = 'low'
    reason:             str   = ''

    # --- Számított ---
    llm_score:   float = 0.0
    latency_ms:  int   = 0
    success:     bool  = False

    # --- Backward-compat propertyk (news_collector.py olvassa ezeket) ---

    @property
    def price_impact(self) -> str:
        """Régi llm_price_impact értékre mappolás."""
        return _SURPRISE_TO_PRICE_IMPACT.get(self.surprise_direction, 'neutral')

    @property
    def catalyst_type(self) -> str:
        """Régi llm_catalyst_type értékre mappolás."""
        return _ARTICLE_TO_CATALYST.get(self.article_type, 'other')

    @property
    def priced_in(self) -> bool:
        """score_worthy=False → priced_in=True (backward compat)."""
        return not self.score_worthy

    @property
    def impact_level(self) -> int:
        return self.surprise_magnitude

    @property
    def impact_duration(self) -> str:
        return 'hours' if self.is_first_report else 'days'

    @property
    def relevant(self) -> bool:
        return self.score_worthy and self.directly_about


# ==========================================
# SYSTEM PROMPT (v2)
# ==========================================

_SYSTEM_PROMPT = """\
You are a financial news event classifier for SHORT-TERM stock price impact (1-4 hours).

CRITICAL RULE: Stock prices move on SURPRISES — information the market did NOT already expect.
Your job is NOT to judge if news is "good" or "bad". Your job is to detect whether
this article contains a QUANTIFIABLE SURPRISE for the specific ticker.

STEP 1 — Decide if this article is worth scoring (score_worthy):
  Set score_worthy=false if the article is ANY of these:
    - Institutional/fund ownership change (bought/sold shares, SEC 13F filing, stake change)
    - Opinion, analysis, "should you buy", "top stocks", roundup, listicle
    - ETF analysis or distribution announcement
    - The article is primarily about a DIFFERENT company (set article_type="tangential")
    - No new information — summary of already-known facts
    - Sector/industry trend piece with no specific company event

  Set score_worthy=true ONLY if:
    - The article reports a specific NEW event directly involving this company
    - AND it contains information not yet fully reflected in the price

STEP 2 — If score_worthy=true, classify the surprise:
  surprise_direction:
    "beat"        = better than market expectations (earnings beat, raised guidance, positive surprise)
    "miss"        = worse than market expectations (earnings miss, lowered guidance, negative surprise)
    "in_line"     = event happened but met expectations (no surprise)
    "no_baseline" = event with no clear expectation to compare against
  surprise_magnitude: 1-5 (only meaningful for beat/miss; 1=tiny, 5=massive)
  is_first_report: true if this appears to be BREAKING NEWS, false if commentary on known event

ALLOWED VALUES:
  score_worthy:       true | false
  article_type:       "earnings" | "guidance" | "product" | "regulatory" | "macro" |
                      "filing" | "opinion" | "tangential" | "other_event"
  directly_about:     true | false
  is_first_report:    true | false
  surprise_direction: "beat" | "miss" | "in_line" | "no_baseline" | "na"
  surprise_magnitude: integer 1-5
  confidence:         "low" | "medium" | "high"
  reason:             string, max 10 words

Answer ONLY with a JSON object. No markdown, no explanations outside JSON."""

_FEW_SHOT_EXAMPLES = """\
EXAMPLES:

[SCORE-WORTHY — earnings beat]
Ticker: AAPL, Title: "Apple Q1 revenue $124B, beats $121B consensus estimate"
→ {"score_worthy":true,"article_type":"earnings","directly_about":true,"is_first_report":true,
   "surprise_direction":"beat","surprise_magnitude":3,"confidence":"high","reason":"revenue beat by 2.5%, clear positive surprise"}

[SCORE-WORTHY — guidance cut]
Ticker: MSFT, Title: "Microsoft lowers Q2 guidance below Wall Street estimates"
→ {"score_worthy":true,"article_type":"guidance","directly_about":true,"is_first_report":true,
   "surprise_direction":"miss","surprise_magnitude":4,"confidence":"high","reason":"guidance cut below consensus, negative surprise"}

[SCORE-WORTHY — product launch]
Ticker: NVDA, Title: "Nvidia announces Blackwell B200 GPU, 30x faster than H100"
→ {"score_worthy":true,"article_type":"product","directly_about":true,"is_first_report":true,
   "surprise_direction":"beat","surprise_magnitude":4,"confidence":"medium","reason":"major performance leap, exceeds expectations"}

[SCORE-WORTHY — regulatory action]
Ticker: TSLA, Title: "Tesla recalls 200k vehicles over unexpected autopilot defect"
→ {"score_worthy":true,"article_type":"regulatory","directly_about":true,"is_first_report":true,
   "surprise_direction":"miss","surprise_magnitude":4,"confidence":"high","reason":"unexpected recall, reputational and cost risk"}

[SCORE-WORTHY — in_line event]
Ticker: AAPL, Title: "Fed holds rates at 5.25% as widely expected"
→ {"score_worthy":true,"article_type":"macro","directly_about":false,"is_first_report":true,
   "surprise_direction":"in_line","surprise_magnitude":1,"confidence":"high","reason":"fully priced in, no surprise"}

[NOT SCORE-WORTHY — institutional filing]
Ticker: GOOGL, Title: "49 Wealth Management LLC Lowers Holdings in Alphabet Inc. by 16%"
→ {"score_worthy":false,"article_type":"filing","directly_about":true,"is_first_report":false,
   "surprise_direction":"na","surprise_magnitude":1,"confidence":"high","reason":"minor fund position change, no price impact"}

[NOT SCORE-WORTHY — opinion/analysis]
Ticker: NVDA, Title: "Should You Buy Nvidia Stock Right Now? Our Analysis"
→ {"score_worthy":false,"article_type":"opinion","directly_about":true,"is_first_report":false,
   "surprise_direction":"na","surprise_magnitude":1,"confidence":"high","reason":"opinion piece, no new information"}

[NOT SCORE-WORTHY — tangential mention]
Ticker: NVDA, Title: "Lumentum Holdings stock hits all-time high at $557"
→ {"score_worthy":false,"article_type":"tangential","directly_about":false,"is_first_report":true,
   "surprise_direction":"na","surprise_magnitude":1,"confidence":"high","reason":"about Lumentum, not NVIDIA"}

[NOT SCORE-WORTHY — sector roundup]
Ticker: META, Title: "Influencer Marketing Market to Reach $107B by 2030 at 30% CAGR"
→ {"score_worthy":false,"article_type":"opinion","directly_about":false,"is_first_report":false,
   "surprise_direction":"na","surprise_magnitude":1,"confidence":"medium","reason":"sector trend piece, no specific META event"}

[NOT SCORE-WORTHY — already known commentary]
Ticker: TSLA, Title: "Alphabet's stock had its best quarter in two decades thanks to AI"
→ {"score_worthy":false,"article_type":"tangential","directly_about":false,"is_first_report":false,
   "surprise_direction":"na","surprise_magnitude":1,"confidence":"high","reason":"about Alphabet, not Tesla"}

"""


# ==========================================
# MAIN CLASS
# ==========================================

class LLMContextChecker:
    """
    LLM-alapu arfolyamhatas scorer (v2 - meglepetes-alapu).

    Parhuzamos futtas (ThreadPoolExecutor), OpenRouter API-n keresztul.
    FinBERT fallback: ha LLM call fail, active_score = finbert_score marad.

    Backward-kompatibilis: a news_collector.py valtozas nelkul mukodik.
    """

    def __init__(
        self,
        api_key: str,
        model: str = 'openai/gpt-4o-mini',
        timeout: float = 8.0,
        max_concurrent: int = 5,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_concurrent = max_concurrent

    # ------------------------------------------------------------------
    # PUBLIC API (változatlan interfész)
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
    # SCORE COMPUTATION (v2)
    # ------------------------------------------------------------------

    def compute_llm_score(self, result: LLMCheckResult) -> float:
        """
        v2 score szamitas: meglepetes-irany × nagysag × breaking_bonus × confidence.

        Nem score-worthy vagy indirekt cikk → 0.0
        beat/miss + magnitude + is_first_report → [-1.0, +1.0]
        """
        if not result.success:
            return 0.0

        # Cikktípus szűrés
        if not result.score_worthy or result.article_type in NON_SCORING_ARTICLE_TYPES:
            return 0.0

        # Indirekt cikk: a score-t lecsökkentjük, de nem nullázzuk
        # (pl. macro event közvetve hat minden tickerre)
        direct_mult = 1.0 if result.directly_about else 0.3

        base = SURPRISE_DIRECTION_SCORE.get(result.surprise_direction, 0.0)
        if base == 0.0:
            return 0.0

        # Magnitude: 1 → 0.20, 2 → 0.40, 3 → 0.60, 4 → 0.80, 5 → 1.00
        base *= result.surprise_magnitude / 5.0

        # Breaking news bónusz
        if result.is_first_report:
            base *= FIRST_REPORT_MULTIPLIER

        # Clamp [-1, +1] még confidence előtt
        base = max(-1.0, min(1.0, base))

        # Confidence szorzó
        base *= CONFIDENCE_MAP.get(result.confidence, 0.50)

        # Direkt relevancia szorzó
        base *= direct_mult

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
        # 'description' (live news) vagy 'summary' (archive) - mindkettőt próbáljuk
        description = (
            getattr(news_item, 'description', None)
            or getattr(news_item, 'summary', None)
            or ''
        )

        price_context = ''
        if current_price:
            price_context = f"  Current price: {current_price:.2f}\n"

        user_content = (
            f"{_FEW_SHOT_EXAMPLES}"
            f"NOW CLASSIFY:\n"
            f"  Ticker: {ticker_symbol} ({ticker_name})\n"
            f"{price_context}"
            f"  Title: {title}\n"
            f"  Summary: {description[:400] if description else '(none)'}\n"
        )

        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    # ------------------------------------------------------------------
    # INTERNAL: API CALL
    # ------------------------------------------------------------------

    def _call_api(self, messages: list) -> str:
        """OpenRouter API hivas. 3x retry SSL/network hibara."""
        if not self.api_key:
            raise ValueError("LLM API key (OPENROUTER_API_KEY) not set")

        is_openai = self.model.startswith("openai/")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 256,
            "stream": False,
        }
        if is_openai:
            payload["seed"] = 42
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_exc = None
        for attempt in range(3):
            try:
                response = requests.post(
                    OPENROUTER_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                last_exc = e
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
        raise last_exc

    # ------------------------------------------------------------------
    # INTERNAL: RESPONSE PARSING
    # ------------------------------------------------------------------

    def _parse_response(self, response_text: str) -> LLMCheckResult:
        """
        JSON parse + enum validacio + score szamitas (v2 schema).
        Parse/validacio hiba eseten success=False.
        """
        text = response_text.strip()
        # Markdown code block eltávolítása (pl. Gemini visszaadja)
        if text.startswith("```"):
            text = text[3:]
            if text.startswith("json"):
                text = text[4:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"[LLM] JSON parse error: {e} | raw: {response_text[:200]}")
            return LLMCheckResult(success=False)

        try:
            score_worthy    = bool(data.get('score_worthy', False))
            article_type    = str(data.get('article_type', 'other_event'))
            directly_about  = bool(data.get('directly_about', False))
            is_first_report = bool(data.get('is_first_report', False))
            surprise_dir    = str(data.get('surprise_direction', 'na'))
            surprise_mag_raw= data.get('surprise_magnitude', 1)
            confidence      = str(data.get('confidence', 'low'))
            reason          = str(data.get('reason', ''))[:100]

            # Magnitude int clamp
            try:
                surprise_mag = max(1, min(5, int(surprise_mag_raw)))
            except (TypeError, ValueError):
                surprise_mag = 1

            # Enum validáció
            if article_type not in VALID_ARTICLE_TYPE:
                article_type = 'other_event'
            if surprise_dir not in VALID_SURPRISE_DIRECTION:
                logger.warning(f"[LLM] Invalid surprise_direction: {surprise_dir}")
                surprise_dir = 'na'
                score_worthy = False
            if confidence not in VALID_CONFIDENCE:
                confidence = 'low'

            # Ha score_worthy=False, iránya legyen 'na'
            if not score_worthy:
                surprise_dir = 'na'
                surprise_mag = 1

        except Exception as e:
            logger.warning(f"[LLM] Field extraction error: {e}")
            return LLMCheckResult(success=False)

        result = LLMCheckResult(
            score_worthy       = score_worthy,
            article_type       = article_type,
            directly_about     = directly_about,
            is_first_report    = is_first_report,
            surprise_direction = surprise_dir,
            surprise_magnitude = surprise_mag,
            confidence         = confidence,
            reason             = reason,
            success            = True,
        )
        result.llm_score = self.compute_llm_score(result)
        return result


# ==========================================
# MODULE TEST
# ==========================================

if __name__ == "__main__":
    print("[OK] LLM Context Checker v2 module loaded")
    print(f"  Model: openai/gpt-4o-mini")
    print(f"  Non-scoring article types: {NON_SCORING_ARTICLE_TYPES}")
    print(f"  First-report multiplier: {FIRST_REPORT_MULTIPLIER}x")

    checker = LLMContextChecker(api_key="test")

    # Teszt 1: earnings beat
    r1 = LLMCheckResult(score_worthy=True, article_type='earnings', directly_about=True,
                        is_first_report=True, surprise_direction='beat', surprise_magnitude=4,
                        confidence='high', success=True)
    r1.llm_score = checker.compute_llm_score(r1)
    print(f"  earnings beat lv4 first_report high: {r1.llm_score}")   # ~0.92

    # Teszt 2: institutional filing (score_worthy=False)
    r2 = LLMCheckResult(score_worthy=False, article_type='filing', directly_about=True,
                        surprise_direction='na', surprise_magnitude=1,
                        confidence='high', success=True)
    r2.llm_score = checker.compute_llm_score(r2)
    print(f"  institutional filing: {r2.llm_score}")                  # 0.0

    # Teszt 3: guidance miss
    r3 = LLMCheckResult(score_worthy=True, article_type='guidance', directly_about=True,
                        is_first_report=True, surprise_direction='miss', surprise_magnitude=3,
                        confidence='medium', success=True)
    r3.llm_score = checker.compute_llm_score(r3)
    print(f"  guidance miss lv3 first_report medium: {r3.llm_score}") # ~-0.585

    # Backward-compat test
    print(f"  r1.price_impact = {r1.price_impact}")        # 'up'
    print(f"  r2.priced_in = {r2.priced_in}")              # True (score_worthy=False)
    print(f"  r1.catalyst_type = {r1.catalyst_type}")      # 'earnings'
