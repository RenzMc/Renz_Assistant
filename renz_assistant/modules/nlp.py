"""
Natural Language Processing functions for Renz Assistant
"""
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

class LanguageProcessor:
    """Handles language detection, mood detection, and other NLP tasks"""
    
    def __init__(self):
        """Initialize NLP components"""
        try:
            # Download required NLTK data
            nltk.download("stopwords", quiet=True)
            nltk.download("punkt", quiet=True)
            nltk.download("wordnet", quiet=True)
            
            # Initialize stopwords
            self.stop_id = set(stopwords.words("indonesian"))
            self.stop_en = set(stopwords.words("english"))
            self.stop_words = set(stopwords.words("english"))
            self.lemmatizer = WordNetLemmatizer()
            
            # Initialize sentiment words for mood detection
            self.positive_words = [
                "happy",
                "great",
                "awesome",
                "wonderful",
                "excited",
                "good",
                "amazing",
                "fantastic",
            ]
            self.negative_words = [
                "sad",
                "depressed",
                "tired",
                "bad",
                "awful",
                "terrible",
                "angry",
                "frustrated",
            ]
            
            print("✅ NLP components initialized")
        except Exception as e:
            print(f"⚠️ NLP setup warning: {e}")
            self.stop_id = set()
            self.stop_en = set()
            self.stop_words = set()
            self.lemmatizer = None
            self.positive_words = []
            self.negative_words = []
    
    def detect_lang(self, text):
        """Enhanced language detection"""
        text = text.strip().lower()

        # Count language-specific words
        id_count = sum(1 for word in text.split() if word in self.stop_id)
        en_count = sum(1 for word in text.split() if word in self.stop_en)

        # Indonesian keywords
        id_keywords = [
            "apa",
            "yang",
            "dari",
            "untuk",
            "dengan",
            "pada",
            "ini",
            "itu",
            "saya",
            "kamu",
        ]
        en_keywords = [
            "what",
            "the",
            "from",
            "for",
            "with",
            "on",
            "this",
            "that",
            "i",
            "you",
        ]

        id_keyword_count = sum(1 for word in id_keywords if word in text)
        en_keyword_count = sum(1 for word in en_keywords if word in text)

        total_id = id_count + id_keyword_count
        total_en = en_count + en_keyword_count

        return "id" if total_id > total_en else "en"
    
    def detect_mood(self, text, conversation_context=None):
        """Enhanced mood detection with context awareness"""
        text_lower = text.lower()

        # Count positive and negative sentiment words
        positive_count = sum(
            1 for word in self.positive_words if word in text_lower)
        negative_count = sum(
            1 for word in self.negative_words if word in text_lower)

        # Consider context from previous conversations
        context_mood = "neutral"
        if conversation_context:
            recent_moods = [conv.get("mood", "neutral")
                            for conv in conversation_context[-3:]]
            if recent_moods.count("sad") > 1:
                context_mood = "sad"
            elif recent_moods.count("happy") > 1:
                context_mood = "happy"

        # Determine mood
        if positive_count > negative_count:
            mood = "happy"
        elif negative_count > positive_count:
            mood = "sad"
        else:
            mood = context_mood

        return mood
    
    def process_wake_sleep_words(self, text, wake_words, sleep_words, is_active):
        """Enhanced wake/sleep word processing"""
        text_lower = text.lower().strip()

        # Check wake words
        for wake_word in wake_words:
            if wake_word in text_lower:
                if not is_active:
                    return "wake"

        # Check sleep words
        for sleep_word in sleep_words:
            if sleep_word in text_lower:
                if is_active:
                    return "sleep"

        return None
    
    def extract_app_name(self, text):
        """Enhanced app name extraction with extended aliases and regex for higher accuracy"""
        app_aliases = {
            "whatsapp":      ["whatsapp", r"\bwa\b", "chat", "whats app", "what's app"],
            "youtube":       ["youtube", r"\byt\b", "video", "tube"],
            "instagram":     ["instagram", r"\big\b", "insta", "foto", "image"],
            "tiktok":        ["tiktok", "tik tok", "tick tock"],
            "chrome":        ["chrome", "browser", "google", "google chrome", "web"],
            "telegram":      ["telegram", r"\btg\b"],
            "spotify":       ["spotify", "music", "songs", "spotify music"],
            "gmail":         ["gmail", "email", "mail", "google mail"],
            "maps":          ["maps", "navigation", "nav", "google maps", "map"],
            "camera":        ["camera", "kamera", "photo", "fotograph", "foto"],
            "settings":      ["settings", "pengaturan", "config", "configuration"],
            "facebook":      ["facebook", "fb", "face book"],
            "twitter":       ["twitter", "tw", "tweet"],
            "linkedin":      ["linkedin", "link in"],
            "snapchat":      ["snapchat", "snap"],
            "messenger":     ["messenger", "fb messenger", "facebook messenger"],
            "netflix":       ["netflix", "movie", "movies", "film"],
            "calculator":    ["calculator", "calc", "hitung"],
            "calendar":      ["calendar", "agenda", "jadwal"],
            "clock":         ["clock", "alarm", "timer"],
            "filemanager":   ["file manager", "files", "explorer"],
            "notes":         ["notes", "note", "catatan"],
            "skype":         ["skype"],
            "zoom":          ["zoom"],
            "drive":         ["drive", "googledrive", "google drive"],

            # ✅ Tambahan aplikasi populer Indonesia
            "dana":          ["dana", "dompet digital", "saldo dana"],
            "shopee":        ["shopee", "belanja online", "shopping"],
            "tokopedia":     ["tokopedia", "toped"],
            "lazada":        ["lazada"],
            "gojek":         ["gojek", "go ride", "go food", "go pay"],
            "grab":          ["grab", "grabfood", "grab ride"],
            "bca":           ["bca", "bca mobile"],
            "ovo":           ["ovo", "ovo pay"],
            "linkaja":       ["linkaja", "link aja"],
            "jenius":        ["jenius"],
            "bri":           ["bri", "brimo", "bri mobile"],
            "mandiri":       ["mandiri", "livin", "livin by mandiri"],
        }

        text_lower = text.lower()

        # First try: check aliases with regex word boundaries
        for app, aliases in app_aliases.items():
            for alias in aliases:
                if ("\&quot; in alias) or ("[" in alias) or ("?" in alias) or ("^" in alias) or ("$" in alias) or ("(" in alias):
                    if re.search(alias, text_lower):
                        return app
                else:
                    if alias in text_lower:
                        return app

        # Second try: extract from patterns like "open [app]" or "buka [app]"
        patterns = [
            r"open\s+([\w\s\.]+)",
            r"buka\s+([\w\s\.]+)",
            r"launch\s+([\w\s\.]+)",
            r"start\s+([\w\s\.]+)",
            r"jalankan\s+([\w\s\.]+)",
            r"aktifkan\s+([\w\s\.]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                possible_app = match.group(1).strip().split()[0]
                if possible_app not in {"the", "an", "a", "my", "app", "application"}:
                    return possible_app.lower()

        return None
    
    def extract_contact_name(self, text):
        """Enhanced contact extraction"""
        # Remove command words
        cleaned_text = re.sub(
            r"(call|telpon|telephone|phone)", "", text, flags=re.IGNORECASE
        ).strip()

        # Check for phone number patterns
        phone_patterns = [
            r"\+\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,9}",
            r"\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}",
        ]

        for pattern in phone_patterns:
            match = re.search(pattern, cleaned_text)
            if match:
                return match.group().strip()

        # Extract contact name
        words = cleaned_text.split()
        if words:
            return " ".join(words)

        return None