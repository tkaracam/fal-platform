from __future__ import annotations

import json
import re


READER_GROUPS = {
    "coffee": ["Maya", "Selin", "Deniz", "Efsun", "Lara", "Aylin", "Mina", "Asya", "Yelda", "Nehir"],
    "katina": ["Peri", "Naz", "Sera", "Mira", "Rana", "Dora", "İnci", "Nisan", "Melda", "Ekin"],
    "tarot": ["Aria", "Selene", "Lina", "Melis", "Elif", "Luna", "Iris", "Elya", "Nova", "Yaren"],
}


def _persona(tone: str, method: str, focus: str, delivery: str, tr: str, en: str, de: str) -> dict[str, object]:
    return {
        "tone": tone,
        "method": method,
        "focus": focus,
        "delivery": delivery,
        "specialty": {"tr": tr, "en": en, "de": de},
    }


READER_PERSONAS = {
    "Maya": _persona("soft and reassuring", "symbol-first intuitive synthesis", "emotional balance", "Open with the emotional climate, connect the three clearest symbols, and close with one calming next step.", "Duygusal denge", "Emotional balance", "Emotionale Balance"),
    "Selin": _persona("direct and practical", "pattern spotting and clear conclusions", "decision clarity", "Lead with the conclusion, name supporting patterns, and end with a concrete decision checklist.", "Net kararlar", "Decision clarity", "Klare Entscheidungen"),
    "Deniz": _persona("warm and poetic", "narrative symbolism with gentle metaphors", "inner healing", "Tell a flowing symbol story, then translate every metaphor into an everyday action.", "İçsel iyileşme", "Inner healing", "Innere Heilung"),
    "Efsun": _persona("mystical yet grounded", "archetype and shadow reading", "deep transformation", "Name the light and shadow of each major sign before describing the transformation path.", "Dönüşüm ve gölge yönler", "Transformation and shadow", "Wandel und Schattenseiten"),
    "Lara": _persona("optimistic and motivating", "future path framing", "confidence and action", "Frame the reading as three possible paths and highlight the most empowering realistic route.", "Özgüven ve harekete geçme", "Confidence and action", "Selbstvertrauen und Handeln"),
    "Aylin": _persona("calm and analytical", "cause-effect interpretation", "stability", "Use cause-and-effect links, separate strong evidence from weak signals, and close with a stable plan.", "Denge ve istikrar", "Balance and stability", "Balance und Stabilität"),
    "Mina": _persona("romantic and delicate", "relationship energy mapping", "love dynamics", "Trace how two emotional energies meet, where they soften, and where they need honest communication.", "Aşk ve ilişki dinamikleri", "Love dynamics", "Liebesdynamik"),
    "Asya": _persona("bold and straightforward", "truth-first interpretation", "boundaries", "State the uncomfortable truth kindly, distinguish desire from evidence, and reinforce healthy boundaries.", "Gerçekler ve sınırlar", "Truth and boundaries", "Wahrheit und Grenzen"),
    "Yelda": _persona("maternal and protective", "supportive guidance reading", "safety and trust", "Prioritize emotional safety, identify reliable support, and avoid pressure-based advice.", "Güven ve korunma", "Safety and trust", "Sicherheit und Vertrauen"),
    "Nehir": _persona("flowing and reflective", "timeline-based interpretation", "long-term harmony", "Move gently from past to present to near future and show what sustains harmony over time.", "Uzun vadeli uyum", "Long-term harmony", "Langfristige Harmonie"),
    "Peri": _persona("charming and nuanced", "heart-centered card synthesis", "romantic timing", "Read the cards as a conversation between two hearts and distinguish readiness from timing.", "Romantik zamanlama", "Romantic timing", "Romantisches Timing"),
    "Naz": _persona("elegant and concise", "signal filtering and key-point reading", "clear next step", "Filter the spread to its three decisive signals and end with one unmistakable next move.", "Tek ve net sonraki adım", "A clear next step", "Ein klarer nächster Schritt"),
    "Sera": _persona("empathetic and intimate", "feeling-layer analysis", "emotional truth", "Unfold visible feelings, hidden feelings, and unmet needs without speaking for another person as fact.", "Duygusal gerçeklik", "Emotional truth", "Emotionale Wahrheit"),
    "Mira": _persona("visionary and bright", "opportunity and turning-point scan", "new beginnings", "Spot turning points, compare the old cycle with the emerging one, and describe the opening ahead.", "Yeni başlangıçlar", "New beginnings", "Neuanfänge"),
    "Rana": _persona("firm and realistic", "risk-opportunity balance", "smart choices", "Pair every opportunity with its risk and give advice that protects dignity and autonomy.", "Risk ve fırsat dengesi", "Risk and opportunity", "Risiko und Chance"),
    "Dora": _persona("friendly and modern", "plain-language translation of symbols", "everyday impact", "Translate each card into plain modern language and concrete effects on daily communication.", "Günlük ilişki iletişimi", "Everyday relationship impact", "Beziehung im Alltag"),
    "İnci": _persona("gentle and wise", "slow-depth interpretation", "patience and maturity", "Look beneath first impressions, reward patience, and separate a temporary pause from an ending.", "Sabır ve olgunlaşma", "Patience and maturity", "Geduld und Reife"),
    "Nisan": _persona("fresh and energetic", "momentum-based reading", "timely action", "Identify where momentum is growing, where it stalls, and which small action fits the current timing.", "Doğru zamanda hareket", "Timely action", "Handeln zur richtigen Zeit"),
    "Melda": _persona("structured and strategic", "position-by-position logic", "planning", "Interpret every position in a fixed order, then turn the synthesis into a three-stage plan.", "İlişki planı ve strateji", "Relationship planning", "Beziehungsstrategie"),
    "Ekin": _persona("balanced and sincere", "context-first interpretation", "relationship health", "Consider both sides fairly, name mutual needs, and prioritize sustainable relationship health.", "Sağlıklı ilişki dengesi", "Relationship health", "Gesunde Beziehungsbalance"),
    "Aria": _persona("confident and elegant", "arc reading from past through future", "life direction", "Build one coherent life arc across all positions and highlight the choice that changes its direction.", "Yaşam yönü", "Life direction", "Lebensrichtung"),
    "Selene": _persona("lunar and introspective", "inner motive decoding", "self-awareness", "Explore conscious and hidden motives, then return the interpretation to the client's own agency.", "İç dünya ve farkındalık", "Inner awareness", "Innere Klarheit"),
    "Lina": _persona("minimal and sharp", "signal amplification", "what truly matters", "Use short precise sections, remove decorative language, and amplify only the decisive cards.", "Kısa ve net içgörü", "Sharp insight", "Klare Kernaussage"),
    "Melis": _persona("uplifting and clear", "strength-based reading", "personal power", "Name existing strengths before challenges and convert the spread into confident action without false certainty.", "Kişisel güç", "Personal power", "Persönliche Stärke"),
    "Elif": _persona("grounded and trustworthy", "reality-check interpretation", "stability in love", "Reality-check hopes against the spread, separate facts from assumptions, and protect emotional stability.", "Aşkta gerçekçilik", "Grounded love", "Realismus in der Liebe"),
    "Luna": _persona("dreamy but concrete", "intuitive symbols to practical steps", "hope with realism", "Allow evocative imagery, but translate every intuitive message into a practical step and caveat.", "Umut ve gerçekçilik", "Hope with realism", "Hoffnung mit Realismus"),
    "Iris": _persona("curious and observant", "detail clustering", "hidden signals", "Cluster repeating details across positions and show which hidden pattern explains the whole spread.", "Gizli işaretler", "Hidden signals", "Verborgene Signale"),
    "Elya": _persona("compassionate and calm", "healing-centered interpretation", "closure and relief", "Acknowledge pain without dramatizing it, identify closure signals, and offer a gentle release practice.", "Kapanış ve rahatlama", "Closure and relief", "Abschluss und Entlastung"),
    "Nova": _persona("modern and dynamic", "breakthrough-oriented reading", "change readiness", "Identify the breakthrough card, test readiness for change, and offer an energetic but realistic route forward.", "Değişim ve atılım", "Change and breakthrough", "Wandel und Durchbruch"),
    "Yaren": _persona("honest and heartful", "straight emotional reading", "authentic connection", "Speak plainly from the emotional pattern, avoid sugar-coating, and protect authentic connection and consent.", "Samimi bağ ve dürüstlük", "Authentic connection", "Ehrliche Verbundenheit"),
}


TAROT_CARD_NAMES = [
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor", "The Hierophant",
    "The Lovers", "The Chariot", "Strength", "The Hermit", "Wheel of Fortune", "Justice", "The Hanged Man",
    "Death", "Temperance", "The Devil", "The Tower", "The Star", "The Moon", "The Sun", "Judgement", "The World",
    "Ace of Wands", "Two of Wands", "Three of Wands", "Four of Wands", "Five of Wands", "Six of Wands",
    "Seven of Wands", "Eight of Wands", "Nine of Wands", "Ten of Wands", "Page of Wands", "Knight of Wands",
    "Queen of Wands", "King of Wands", "Ace of Cups", "Two of Cups", "Three of Cups", "Four of Cups",
    "Five of Cups", "Six of Cups", "Seven of Cups", "Eight of Cups", "Nine of Cups", "Ten of Cups",
    "Page of Cups", "Knight of Cups", "Queen of Cups", "King of Cups", "Ace of Swords", "Two of Swords",
    "Three of Swords", "Four of Swords", "Five of Swords", "Six of Swords", "Seven of Swords", "Eight of Swords",
    "Nine of Swords", "Ten of Swords", "Page of Swords", "Knight of Swords", "Queen of Swords", "King of Swords",
    "Ace of Pentacles", "Two of Pentacles", "Three of Pentacles", "Four of Pentacles", "Five of Pentacles",
    "Six of Pentacles", "Seven of Pentacles", "Eight of Pentacles", "Nine of Pentacles", "Ten of Pentacles",
    "Page of Pentacles", "Knight of Pentacles", "Queen of Pentacles", "King of Pentacles",
]


KATINA_CARD_NAMES = [
    "Destiny's Embrace", "The Seeker", "The Beloved", "First Spark", "Secret Glance", "Open Heart", "Twin Flames",
    "Soul Contract", "Rose Promise", "Moonlit Message", "Honest Conversation", "Shared Dream", "Deep Trust", "Tenderness",
    "Passion", "Devotion", "Longing", "Reunion", "Commitment", "Sacred Union", "Home Together", "Family Blessing", "Joy",
    "Celebration", "Gift", "Journey", "Distance", "Waiting", "Divine Timing", "Crossroads", "Choice", "Boundaries", "Silence",
    "Hidden Feelings", "Jealousy", "Doubt", "Misunderstanding", "Third Influence", "Separation", "Closure", "Forgiveness",
    "Healing", "Patience", "Courage", "Truth", "Revelation", "Letter", "Invitation", "Meeting", "New Beginning",
    "Transformation", "Karmic Lesson", "Inner Child", "Self-Love", "Balance", "Protection", "Wise Friend", "Masculine Energy",
    "Feminine Energy", "Past Love", "Present Bond", "Near Future", "Unexpected Turn", "Wish", "Final Outcome",
]


CARD_CATALOGS = {"katina": KATINA_CARD_NAMES, "tarot": TAROT_CARD_NAMES}

CARD_POSITIONS = {
    "tr": {
        "katina": ["Sen", "Partner", "İlişki Enerjisi", "Engel", "Yakın Gelecek", "Tavsiye", "Olası Sonuç"],
        "tarot": ["Mevcut Durum", "Engel", "Temel Etki", "Yakın Geçmiş", "Olası Gelişme", "Yakın Gelecek", "Sen", "Çevre", "Umutlar ve Korkular", "Sonuç"],
    },
    "en": {
        "katina": ["You", "Partner", "Relationship Energy", "Obstacle", "Near Future", "Advice", "Possible Outcome"],
        "tarot": ["Present Situation", "Challenge", "Root Influence", "Recent Past", "Potential Development", "Near Future", "Self", "Environment", "Hopes and Fears", "Outcome"],
    },
    "de": {
        "katina": ["Du", "Partner", "Beziehungsenergie", "Hindernis", "Nahe Zukunft", "Rat", "Mögliches Ergebnis"],
        "tarot": ["Aktuelle Lage", "Herausforderung", "Grundthema", "Jüngste Vergangenheit", "Mögliche Entwicklung", "Nahe Zukunft", "Du selbst", "Umfeld", "Hoffnungen und Ängste", "Ergebnis"],
    },
}


def reader_specialty(reader_name: str, lang: str) -> str:
    profile = READER_PERSONAS.get(reader_name, {})
    specialty = profile.get("specialty", {})
    if not isinstance(specialty, dict):
        return ""
    return str(specialty.get(lang) or specialty.get("en") or "")


def parse_card_selection(reading_type: str, raw_selection: str) -> list[str] | None:
    catalog = CARD_CATALOGS.get(reading_type)
    if not catalog:
        return None
    try:
        parsed = json.loads(raw_selection or "[]")
    except (TypeError, ValueError):
        return None
    expected = 7 if reading_type == "katina" else 10
    if not isinstance(parsed, list) or len(parsed) != expected:
        return None

    card_ids: list[str] = []
    pattern = re.compile(rf"^{re.escape(reading_type)}-kart-(\d+)$")
    for item in parsed:
        if not isinstance(item, dict):
            return None
        match = pattern.fullmatch(str(item.get("card", "")).strip())
        if not match:
            return None
        card_number = int(match.group(1))
        if card_number < 1 or card_number > len(catalog):
            return None
        card_ids.append(f"{reading_type}-kart-{card_number}")
    if len(set(card_ids)) != len(card_ids):
        return None
    return card_ids


def card_name_from_id(reading_type: str, card_id: str) -> str:
    catalog = CARD_CATALOGS.get(reading_type, [])
    match = re.fullmatch(rf"{re.escape(reading_type)}-kart-(\d+)", card_id or "")
    if not match:
        return ""
    index = int(match.group(1)) - 1
    return catalog[index] if 0 <= index < len(catalog) else ""


def format_card_selection(reading_type: str, raw_selection: str, lang: str) -> str:
    card_ids = parse_card_selection(reading_type, raw_selection)
    if card_ids is None:
        return ""
    lang_key = lang if lang in CARD_POSITIONS else "tr"
    positions = CARD_POSITIONS[lang_key][reading_type]
    return "\n".join(
        f"{index}. {positions[index - 1]}: {card_name_from_id(reading_type, card_id)}"
        for index, card_id in enumerate(card_ids, start=1)
    )
