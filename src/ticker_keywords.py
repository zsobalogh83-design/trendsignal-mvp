"""
TrendSignal MVP - Ticker-Specific Keywords Database
Enhanced relevance matching and sentiment analysis for specific tickers

Version: 1.0
Date: 2024-12-27
"""

from typing import Dict, List


# ==========================================
# TICKER METADATA
# ==========================================

TICKER_INFO = {
    # US Blue-Chips
    'AAPL': {
        'name': 'Apple Inc.',
        'sector': 'technology',
        'industry': 'consumer_electronics',
        'market': 'NASDAQ',
        'currency': 'USD'
    },
    'TSLA': {
        'name': 'Tesla Inc.',
        'sector': 'automotive',
        'industry': 'electric_vehicles',
        'market': 'NASDAQ',
        'currency': 'USD'
    },
    'MSFT': {
        'name': 'Microsoft Corporation',
        'sector': 'technology',
        'industry': 'software',
        'market': 'NASDAQ',
        'currency': 'USD'
    },
    'NVDA': {
        'name': 'NVIDIA Corporation',
        'sector': 'technology',
        'industry': 'semiconductors',
        'market': 'NASDAQ',
        'currency': 'USD'
    },
    
    # Hungarian BÉT
    'OTP.BD': {
        'name': 'OTP Bank Nyrt',
        'sector': 'financial',
        'industry': 'banking',
        'market': 'BÉT',
        'currency': 'HUF'
    },
    'MOL.BD': {
        'name': 'MOL Magyar Olaj- és Gázipari Nyrt',
        'sector': 'energy',
        'industry': 'oil_gas',
        'market': 'BÉT',
        'currency': 'HUF'
    },
}


# ==========================================
# TICKER-SPECIFIC KEYWORDS (Relevance Matching)
# ==========================================

TICKER_KEYWORDS = {
    # Apple
    'AAPL': {
        'primary': ['apple', 'iphone', 'ipad', 'mac', 'tim cook', 'cupertino'],
        'products': ['iphone 16', 'macbook', 'apple watch', 'airpods', 'vision pro', 'app store'],
        'services': ['apple tv', 'icloud', 'apple music', 'apple pay'],
        'events': ['wwdc', 'apple event', 'keynote'],
        'competitors': ['samsung', 'google pixel', 'android'],
        'hu_keywords': ['apple', 'iphone', 'tim cook', 'cupertino']
    },
    
    # Tesla
    'TSLA': {
        'primary': ['tesla', 'elon musk', 'ev', 'electric vehicle'],
        'products': ['model 3', 'model y', 'model s', 'model x', 'cybertruck', 'semi'],
        'technology': ['fsd', 'full self-driving', 'autopilot', 'supercharger', 'battery'],
        'facilities': ['gigafactory', 'fremont', 'berlin', 'shanghai', 'texas'],
        'competitors': ['rivian', 'lucid', 'byd', 'ford ev', 'gm ev'],
        'hu_keywords': ['tesla', 'elon musk', 'elektromos autó', 'villanyautó']
    },
    
    # Microsoft
    'MSFT': {
        'primary': ['microsoft', 'msft', 'satya nadella', 'redmond'],
        'products': ['windows', 'office 365', 'azure', 'xbox', 'surface'],
        'services': ['teams', 'linkedin', 'github', 'bing', 'edge'],
        'ai': ['copilot', 'openai', 'chatgpt partnership', 'azure ai'],
        'cloud': ['azure', 'cloud computing', 'enterprise'],
        'competitors': ['google cloud', 'aws', 'amazon', 'meta'],
        'hu_keywords': ['microsoft', 'windows', 'azure', 'satya nadella']
    },
    
    # NVIDIA
    'NVDA': {
        'primary': ['nvidia', 'nvda', 'jensen huang'],
        'products': ['geforce', 'rtx', 'gtx', 'h100', 'a100', 'grace hopper'],
        'technology': ['gpu', 'cuda', 'ai chip', 'graphics card', 'datacenter'],
        'sectors': ['gaming', 'ai', 'datacenter', 'automotive', 'professional visualization'],
        'competitors': ['amd', 'intel', 'qualcomm'],
        'hu_keywords': ['nvidia', 'jensen huang', 'videókártya', 'gpu', 'mesterséges intelligencia chip']
    },
    
    # OTP Bank
    'OTP.BD': {
        'primary': ['otp', 'otp bank', 'otp group'],
        'leadership': ['csányi sándor', 'bencsik lászló'],
        'products': ['bankszámla', 'hitel', 'jelzálog', 'otp mobil'],  # 'takarék' removed (too generic)
        'markets': ['magyarország', 'bulgária', 'románia', 'szerbia', 'közép-kelet-európa'],
        'financial': ['éves jelentés', 'osztalék', 'tőkemegfelelés', 'hitelportfólió'],
        'en_keywords': ['otp', 'otp bank', 'otp group', 'hungarian bank'],
        'hu_keywords': ['otp', 'otp bank', 'csányi sándor', 'magyar bank', 'retail bank']
    },
    
    # MOL
    'MOL.BD': {
        'primary': ['mol', 'mol nyrt', 'mol group', 'mol magyar'],
        'leadership': ['hernádi zsolt'],
        'products': ['benzin', 'gázolaj', 'üzemanyag', 'fresh corner'],
        'operations': ['iná refinery', 'slovnaft', 'mol petrol', 'kúthálózat'],
        'sectors': ['olaj', 'gáz', 'kémia', 'petrolkémia', 'upstream', 'downstream'],
        'sustainability': ['electric', 'hidrogén', 'megújuló', 'zöld átállás'],
        'en_keywords': ['mol', 'mol group', 'hungarian oil', 'mol petrol'],
        'hu_keywords': ['mol', 'mol nyrt', 'hernádi zsolt', 'olaj', 'benzin', 'üzemanyag']
    },
}


# ==========================================
# SENTIMENT KEYWORDS (Enhanced)
# ==========================================

TICKER_SENTIMENT_KEYWORDS = {
    # Apple
    'AAPL': {
        'positive': [
            # Sales & Financial
            'record sales', 'revenue beat', 'earnings beat', 'profit surge',
            'strong demand', 'sold out', 'pre-order success',
            # Products
            'innovative', 'groundbreaking', 'revolutionary', 'game-changer',
            'premium', 'ecosystem strength', 'user loyalty',
            # Services
            'subscription growth', 'services revenue', 'app store revenue',
            # Hungarian
            'rekord eladások', 'erős kereslet', 'innovatív', 'árbevétel növekedés'
        ],
        'negative': [
            # Sales & Financial
            'sales decline', 'revenue miss', 'margin pressure', 'guidance cut',
            'supply constraint', 'production issue',
            # Competition
            'market share loss', 'losing to samsung', 'android gains',
            # Products
            'delayed launch', 'quality issue', 'battery problem', 'recall',
            # Hungarian
            'eladások csökkenése', 'piaci részesedés vesztés', 'késleltetés'
        ]
    },
    
    # Tesla
    'TSLA': {
        'positive': [
            # Deliveries & Production
            'delivery record', 'production ramp', 'gigafactory expansion',
            'delivery beat', 'production target met',
            # Technology
            'fsd approval', 'autonomous milestone', 'battery breakthrough',
            'supercharger expansion', 'range improvement',
            # Market
            'ev leader', 'market share gain', 'demand strong',
            # Hungarian
            'szállítási rekord', 'gyártás bővítés', 'erős kereslet'
        ],
        'negative': [
            # Deliveries & Production
            'delivery miss', 'production halt', 'factory shutdown',
            'recall', 'quality issue',
            # Safety
            'autopilot crash', 'safety investigation', 'nhtsa probe',
            'accident', 'fire incident',
            # Competition
            'competition intensifies', 'chinese ev threat', 'byd gains',
            # Hungarian
            'visszahívás', 'termelés leállás', 'baleset', 'vizsgálat'
        ]
    },
    
    # Microsoft
    'MSFT': {
        'positive': [
            # Cloud & AI
            'azure growth', 'cloud revenue', 'ai leadership', 'copilot adoption',
            'openai partnership', 'enterprise win', 'contract win',
            # Products
            'windows 11 success', 'office 365 growth', 'xbox sales',
            # Financial
            'margin expansion', 'operating leverage', 'cash flow',
            # Hungarian
            'felhő növekedés', 'mesterséges intelligencia vezető', 'bevétel növekedés'
        ],
        'negative': [
            # Competition
            'cloud market share loss', 'aws competition', 'google threat',
            # Products
            'windows bug', 'security breach', 'outage', 'downtime',
            # Regulatory
            'antitrust', 'regulatory scrutiny', 'eu fine',
            # Hungarian
            'piaci részesedés vesztés', 'biztonsági rés', 'kiesés'
        ]
    },
    
    # NVIDIA
    'NVDA': {
        'positive': [
            # AI & Datacenter
            'ai chip demand', 'datacenter growth', 'h100 demand', 'ai boom',
            'gpu shortage', 'sold out', 'backlog',
            # Gaming
            'gaming strength', 'rtx adoption', 'gaming revenue',
            # Partnerships
            'cloud partnership', 'automotive design win',
            # Hungarian
            'ai chip kereslet', 'adatközpont növekedés', 'gpu hiány'
        ],
        'negative': [
            # Competition & Regulation
            'china export ban', 'export restriction', 'amd competition',
            'intel threat', 'custom chip threat',
            # Demand
            'demand slowdown', 'order cancellation', 'inventory buildup',
            # Hungarian
            'export tilalom', 'kínai korlátozás', 'kereslet lassulás'
        ]
    },
    
    # OTP Bank
    'OTP.BD': {
        'positive': [
            # Financial Performance
            'profit growth', 'nettó nyereség', 'eredmény növekedés',
            'strong quarter', 'erős negyedév', 'bevétel emelkedés',
            'hitelportfólió bővülés', 'betétállomány növekedés',
            # Ratings & Market
            'felminősítés', 'upgrade', 'pozitív kilátás', 'piaci részesedés növekedés',
            'díjak', 'legjobb bank', 'innovatív szolgáltatás',
            # Expansion
            'akvizíció', 'felvásárlás', 'terjeszkedés', 'új piacok'
        ],
        'negative': [
            # Financial Performance
            'profit decline', 'nyereség csökkenés', 'veszteség',
            'rossz negyedév', 'bevétel visszaesés', 'margins压低',
            # Risk & Quality
            'non-performing loans', 'npl növekedés', 'rossz hitelek',
            'céltartalék emelés', 'provision increase',
            # Regulatory & Market
            'leminősítés', 'downgrade', 'negatív kilátás',
            'mnb bírság', 'szabályozói vizsgálat', 'compliance issue'
        ]
    },
    
    # MOL
    'MOL.BD': {
        'positive': [
            # Pricing & Demand
            'olajár emelkedés', 'oil price rise', 'strong demand',
            'refining margin', 'finomítói marzsok', 'kereslet növekedés',
            # Operations
            'termelés növekedés', 'production increase', 'új kút',
            'ina growth', 'slovnaft profit', 'petrochemical strength',
            # Investment
            'beruházás', 'investment', 'expansion', 'bővítés',
            'green energy', 'megújuló energia', 'electric charging'
        ],
        'negative': [
            # Pricing & Market
            'olajár zuhanás', 'oil price crash', 'oversupply',
            'weak demand', 'kereslet gyenge', 'refining losses',
            # Operations
            'termelés csökkenés', 'production cut', 'kút bezárás',
            'facility shutdown', 'üzemleállás', 'maintenance',
            # Costs & Risks
            'cost inflation', 'költség emelkedés', 'geopolitical risk',
            'environment fine', 'környezetvédelmi bírság', 'spill', 'szennyezés'
        ]
    },
}


# ==========================================
# SECTOR-SPECIFIC KEYWORDS
# ==========================================

SECTOR_KEYWORDS = {
    'technology': {
        'positive': ['innovation', 'ai', 'cloud', 'digital transformation', 'disruption',
                    'market leader', 'patent', 'r&d breakthrough'],
        'negative': ['obsolete', 'legacy', 'disrupted', 'outdated', 'security breach',
                    'data leak', 'hack', 'cyberattack'],
        'hu_positive': ['innováció', 'digitális', 'áttörés', 'piacvezető'],
        'hu_negative': ['elavult', 'biztonsági rés', 'adatszivárgás']
    },
    
    'financial': {
        'positive': ['profit', 'revenue growth', 'loan growth', 'deposit growth',
                    'npl decrease', 'capital strength', 'dividend increase'],
        'negative': ['credit loss', 'npl increase', 'provision', 'capital shortage',
                    'bad loans', 'regulatory fine', 'money laundering'],
        'hu_positive': ['nyereség', 'hitel növekedés', 'tőkeerő', 'osztalék emelés'],
        'hu_negative': ['hitelezési veszteség', 'rossz hitelek', 'bírság', 'céltartalék']
    },
    
    'energy': {
        'positive': ['oil discovery', 'production increase', 'refining margin',
                    'energy transition', 'renewable', 'efficiency gain'],
        'negative': ['oil spill', 'production cut', 'refinery shutdown',
                    'environmental fine', 'accident', 'opec cut'],
        'hu_positive': ['olajfelfedezés', 'termelés növekedés', 'finomítói marzs',
                       'megújuló energia', 'hatékonyság'],
        'hu_negative': ['olajszennyezés', 'termelés csökkentés', 'üzemleállás',
                       'környezetvédelmi bírság', 'baleset']
    },
    
    'automotive': {
        'positive': ['delivery record', 'production ramp', 'sales growth',
                    'new model', 'technology leadership', 'autonomous'],
        'negative': ['recall', 'safety issue', 'production delay',
                    'supply chain', 'chip shortage', 'accident'],
        'hu_positive': ['szállítási rekord', 'eladás növekedés', 'új modell'],
        'hu_negative': ['visszahívás', 'biztonsági probléma', 'késleltetés', 'baleset']
    },
}


# ==========================================
# EXECUTIVE/LEADERSHIP KEYWORDS
# ==========================================

LEADERSHIP_KEYWORDS = {
    'AAPL': ['tim cook', 'jeff williams', 'luca maestri'],
    'TSLA': ['elon musk'],
    'MSFT': ['satya nadella', 'amy hood'],
    'NVDA': ['jensen huang', 'colette kress'],
    'OTP.BD': ['csányi sándor', 'bencsik lászló', 'völker jános'],
    'MOL.BD': ['hernádi zsolt', 'simola józsef'],
}


# ==========================================
# COMPETITOR KEYWORDS (for context)
# ==========================================

COMPETITOR_KEYWORDS = {
    'AAPL': ['samsung', 'google', 'huawei', 'xiaomi', 'android'],
    'TSLA': ['rivian', 'lucid', 'byd', 'nio', 'xpeng', 'ford', 'gm'],
    'MSFT': ['google', 'amazon aws', 'meta', 'salesforce', 'oracle'],
    'NVDA': ['amd', 'intel', 'qualcomm', 'broadcom'],
    'OTP.BD': ['erste', 'k&h', 'raiffeisen', 'unicredit', 'mkb'],
    'MOL.BD': ['omv', 'pkn orlen', 'lukoil', 'shell', 'total'],
}


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def get_ticker_keywords(ticker_symbol: str) -> Dict[str, List[str]]:
    """Get all keywords for a ticker"""
    return TICKER_KEYWORDS.get(ticker_symbol, {
        'primary': [ticker_symbol.split('.')[0].lower()],
        'products': [],
        'services': [],
        'hu_keywords': []
    })


def get_sector_keywords(ticker_symbol: str) -> Dict[str, List[str]]:
    """Get sector-specific keywords for a ticker"""
    ticker_info = TICKER_INFO.get(ticker_symbol, {})
    sector = ticker_info.get('sector', 'general')
    return SECTOR_KEYWORDS.get(sector, {})


def get_all_relevant_keywords(ticker_symbol: str) -> List[str]:
    """
    Get comprehensive keyword list for relevance matching
    
    Returns: Flat list of all relevant keywords
    """
    keywords = []
    
    # Ticker-specific
    ticker_kw = get_ticker_keywords(ticker_symbol)
    for key, values in ticker_kw.items():
        keywords.extend(values)
    
    # Leadership
    leadership = LEADERSHIP_KEYWORDS.get(ticker_symbol, [])
    keywords.extend(leadership)
    
    # Ticker base
    ticker_base = ticker_symbol.split('.')[0].lower()
    keywords.append(ticker_base)
    
    # Company name
    ticker_info = TICKER_INFO.get(ticker_symbol, {})
    if 'name' in ticker_info:
        keywords.append(ticker_info['name'].lower())
    
    # Remove duplicates
    return list(set(keywords))


def get_sentiment_boost_keywords(ticker_symbol: str) -> Dict[str, List[str]]:
    """
    Get ticker-specific sentiment keywords for boosted scoring
    
    These are highly significant events that should amplify sentiment
    """
    return TICKER_SENTIMENT_KEYWORDS.get(ticker_symbol, {
        'positive': [],
        'negative': []
    })


# ==========================================
# RELEVANCE SCORING
# ==========================================

def calculate_relevance_score(
    text: str,
    ticker_symbol: str,
    use_sector_context: bool = True
) -> float:
    """
    Calculate relevance score (0.0 to 1.0)
    
    Args:
        text: News text (title + description)
        ticker_symbol: Stock ticker
        use_sector_context: Include sector keywords
    
    Returns:
        Relevance score (0.0 = irrelevant, 1.0 = highly relevant)
    """
    text_lower = text.lower()
    score = 0.0
    
    # 0. FILTER: Irrelevant topics (auto-reject)
    irrelevant_topics = [
        'időjárás', 'időjárás előrejelzés', 'weather forecast', 'climate',
        'sport', 'football', 'soccer', 'foci', 'labdarúgás', 'meccs',
        'celebrity', 'celeb', 'sztár', 'híresség', 'színész',
        'recipe', 'recept', 'főzés', 'gasztro', 'étterem',
        'horoscope', 'horoszkóp', 'asztrológia',
        'astrology', 'zodiac', 'csillagjegy'
    ]
    
    # If contains irrelevant topic, return 0.0 immediately
    for topic in irrelevant_topics:
        if topic in text_lower:
            return 0.0
    
    # 1. Direct ticker mention (1.0)
    ticker_base = ticker_symbol.split('.')[0].lower()
    if ticker_base in text_lower:
        return 1.0
    
    # 2. Company name mention (0.95)
    ticker_info = TICKER_INFO.get(ticker_symbol, {})
    if ticker_info.get('name', '').lower() in text_lower:
        return 0.95
    
    # 3. Leadership mention (0.90)
    leadership = LEADERSHIP_KEYWORDS.get(ticker_symbol, [])
    for leader in leadership:
        if leader.lower() in text_lower:
            score = max(score, 0.90)
    
    # 4. Primary keywords (0.85)
    ticker_kw = get_ticker_keywords(ticker_symbol)
    primary = ticker_kw.get('primary', [])
    for kw in primary:
        if kw.lower() in text_lower:
            score = max(score, 0.85)
    
    # 5. Product/Service keywords (0.70)
    products = ticker_kw.get('products', []) + ticker_kw.get('services', [])
    for kw in products:
        if kw.lower() in text_lower:
            score = max(score, 0.70)
    
    # 6. Sector context (0.50-0.60)
    if use_sector_context:
        sector_kw = get_sector_keywords(ticker_symbol)
        sector_pos = sector_kw.get('positive', []) + sector_kw.get('hu_positive', [])
        sector_neg = sector_kw.get('negative', []) + sector_kw.get('hu_negative', [])
        
        for kw in sector_pos + sector_neg:
            if kw.lower() in text_lower:
                score = max(score, 0.55)
    
    # 7. Competitor mention (0.40 - indirect relevance)
    competitors = COMPETITOR_KEYWORDS.get(ticker_symbol, [])
    for comp in competitors:
        if comp.lower() in text_lower:
            score = max(score, 0.40)
    
    return score


# ==========================================
# USAGE EXAMPLE
# ==========================================

if __name__ == "__main__":
    print("✅ Ticker Keywords Database Loaded")
    print(f"\n📊 Supported Tickers: {len(TICKER_INFO)}")
    for ticker, info in TICKER_INFO.items():
        print(f"  • {ticker:10s} - {info['name']:30s} ({info['market']})")
    
    print(f"\n🎯 Example: OTP.BD keywords")
    otp_kw = get_ticker_keywords('OTP.BD')
    print(f"  Primary: {', '.join(otp_kw['primary'])}")
    print(f"  Hungarian: {', '.join(otp_kw['hu_keywords'])}")
    
    print(f"\n🧪 Relevance scoring test:")
    test_cases = [
        "OTP Bank reports strong Q4 earnings",
        "Csányi Sándor talks about digital banking",
        "Hungarian banking sector outlook",
        "Tesla announces new Gigafactory"
    ]
    
    for text in test_cases:
        score = calculate_relevance_score(text, 'OTP.BD')
        print(f"  '{text[:40]}...' → {score:.2f}")
