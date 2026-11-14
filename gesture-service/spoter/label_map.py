"""
Gloss label mapping between Russian Slovo dataset glosses, Armenian sign glosses, and class indices.
Provides bidirectional lookup and serialization.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("gesture-service.spoter.label_map")

# Core Russian to Armenian sign gloss vocabulary mapping
RUSSIAN_TO_ARMENIAN_CORE: Dict[str, str] = {
    # Greetings & Politeness
    "привет": "ԲԱՐԵՎ",
    "здравствуйте": "ԲԱՐԵՎ ՁԵԶ",
    "до свидания": "ՑՏԵՍՈՒԹՅՈՒՆ",
    "пока": "ՑՏԵՍՈՒԹՅՈՒՆ",
    "спасибо": "ՇՆՈՐՀԱԿԱԼՈՒԹՅՈՒՆ",
    "пожалуйста": "ԽՆԴՐԵՄ",
    "извините": "ՆԵՐԵՑԵՔ",
    "простите": "ՆԵՐՈՂՈՒԹՅՈՒՆ",
    "да": "ԱՅՈ",
    "нет": "ՈՉ",
    "ладно": "ԼԱՎ",
    "хорошо": "ԼԱՎ",
    "плохо": "ՎԱՏ",
    # Pronouns & People
    "я": "ԵՍ",
    "ты": "ԴՈՒ",
    "он": "ՆԱ",
    "она": "ՆԱ",
    "мы": "ՄԵՆՔ",
    "вы": "ԴՈՒՔ",
    "они": "ՆՐԱՆՔ",
    "человек": "ՄԱՐԴ",
    "люди": "ՄԱՐԴԻԿ",
    "семья": "ԸՆՏԱՆԻՔ",
    "мама": "ՄԱՅՐԻԿ",
    "мать": "ՄԱՅՐ",
    "папа": "ՀԱՅՐԻԿ",
    "отец": "ՀԱՅՐ",
    "родители": "ԾՆՈՂՆԵՐ",
    "сын": "ՈՐԴԻ",
    "дочь": "ԴՈՒՍՏՐ",
    "брат": "ԵՂԲԱՅՐ",
    "сестра": "ՔՈՒՅՐ",
    "дедушка": "ՊԱՊԻԿ",
    "бабушка": "ՏԱՏԻԿ",
    "ребенок": "ԵՐԵԽԱ",
    "дети": "ԵՐԵԽԱՆԵՐ",
    "друг": "ԸՆԿԵՐ",
    "подруга": "ԸՆԿԵՐՈՒՀԻ",
    # Body & Health
    "голова": "ԳԼՈՒԽ",
    "рука": "ՁԵՌՔ",
    "нога": "ՈՏՔ",
    "глаз": "ԱՉՔ",
    "глаза": "ԱՉՔԵՐ",
    "ухо": "ԱԿԱՆՋ",
    "уши": "ԱԿԱՆՋՆԵՐ",
    "рот": "ԲԵՐԱՆ",
    "нос": "ՔԻԹ",
    "сердце": "ՍԻՐՏ",
    "боль": "ՑԱՎ",
    "болеть": "ՑԱՎԵԼ",
    "врач": "ԲԺԻՇԿ",
    "доктор": "ԲԺԻՇԿ",
    "больница": "ՀԻՎԱՆԴԱՆՈՑ",
    "лекарство": "ԴԵՂ",
    "аптека": "ԴԵՂԱՏՈՒՆ",
    "глухой": "ԽՈՒԼ",
    "жест": "ԺԵՍՏ",
    "язык": "ԼԵԶՈՒ",
    # Food & Drink
    "вода": "ՋՈՒՐ",
    "хлеб": "ՀԱՑ",
    "еда": "ՈՒՏԵԼԻՔ",
    "пища": "ԿԵՐԱԿՈՒՐ",
    "чай": "ԹԵՅ",
    "кофе": "ՍՈՒՐՃ",
    "молоко": "ԿԱԹ",
    "сок": "ՀՅՈՒԹ",
    "мясо": "ՄԻՍ",
    "рыба": "ՁՈՒԿ",
    "яблоко": "ԽՆՁՈՐ",
    "сахар": "ՇԱՔԱՐ",
    "соль": "ԱՂ",
    "завтрак": "ՆԱԽԱՃԱՇ",
    "обед": "ՃԱՇ",
    "ужин": "ԸՆԹՐԻՔ",
    # Common Actions & Verbs
    "хотеть": "ՈՒԶԵԼ",
    "мочь": "ԿԱՐՈՂԱՆԱԼ",
    "любить": "ՍԻՐԵԼ",
    "знать": "ԻՄԱՆԱԼ",
    "понимать": "ՀԱՍԿԱՆԱԼ",
    "помнить": "ՀԻՇԵԼ",
    "забыть": "ՄՈՌԱՆԱԼ",
    "думать": "ՄՏԱԾԵԼ",
    "видеть": "ՏԵՍՆԵԼ",
    "смотреть": "ՆԱՅԵԼ",
    "слышать": "ԼՍԵԼ",
    "слушать": "ԼՍԵԼ",
    "говорить": "ԽՈՍԵԼ",
    "сказать": "ԱՍԵԼ",
    "спросить": "ՀԱՐՑՆԵԼ",
    "ответить": "ՊԱՏԱՍԽԱՆԵԼ",
    "помощь": "ՕԳՆՈՒԹՅՈՒՆ",
    "помогать": "ՕԳՆԵԼ",
    "помоги": "ՕԳՆԻՐ",
    "идти": "ԳՆԱԼ",
    "ехать": "ԳՆԱԼ",
    "прийти": "ԳԱԼ",
    "стоять": "ԿԱՆԳՆԵԼ",
    "сидеть": "ՆՍՏԵԼ",
    "лежать": "ՊԱՌԿԵԼ",
    "спать": "ՔՆԵԼ",
    "проснуться": "ԱՐԹՆԱՆԱԼ",
    "кушать": "ՈՒՏԵԼ",
    "есть": "ՈՒՏԵԼ",
    "пить": "ԽՄԵԼ",
    "делать": "ԱՆԵԼ",
    "работать": "ԱՇԽԱՏԵԼ",
    "учиться": "ՍՈՎՈՐԵԼ",
    "читать": "ԿԱՐԴԱԼ",
    "писать": "ԳՐԵԼ",
    "купить": "ԳՆԵԼ",
    "продать": "ՎԱՃԱՌԵԼ",
    "дать": "ՏԱԼ",
    "взять": "ՎԵՐՑՆԵԼ",
    "жить": "ԱՊՐԵԼ",
    "ждать": "ՍՊԱՍԵԼ",
    "искать": "ՓՆՏՐԵԼ",
    "найти": "ԳՏՆԵԼ",
    # Questions
    "что": "ԻՆՉ",
    "кто": "ՈՎ",
    "где": "ՈՐՏԵՂ",
    "куда": "ՈՒՐ",
    "откуда": "ՈՐՏԵՂԻՑ",
    "когда": "ԵՐԲ",
    "почему": "ԻՆՉՈՒ",
    "зачем": "ԻՆՉԻ ՀԱՄԱՐ",
    "как": "ԻՆՉՊԵՍ",
    "какой": "ԻՆՉՊԻՍԻ",
    "сколько": "ՔԱՆԻ",
    "чей": "ՈՒՄ",
    # Time & Days
    "время": "ԺԱՄԱՆԱԿ",
    "час": "ԺԱՄ",
    "минута": "ՐՈՊԵ",
    "день": "ՕՐ",
    "ночь": "ԳԻՇԵՐ",
    "утро": "ԱՌԱՎՈՏ",
    "вечер": "ԵՐԵԿՈ",
    "сегодня": "ԱՅՍՕՐ",
    "завтра": "ՎԱՂԸ",
    "вчера": "ԵՐԵԿ",
    "сейчас": "ՀԻՄԱ",
    "потом": "ՀԵՏՈ",
    "раньше": "ԱՌԱՋ",
    "всегда": "ՄԻՇՏ",
    "никогда": "ԵՐԲԵՔ",
    "неделя": "ՇԱԲԱԹ",
    "месяц": "ԱՄԻՍ",
    "год": "ՏԱՐԻ",
    "понедельник": "ԵՐԿՈՒՇԱԲԹԻ",
    "вторник": "ԵՐԵՔՇԱԲԹԻ",
    "среда": "ՉՈՐԵՔՇԱԲԹԻ",
    "четверг": "ՀԻՆԳՇԱԲԹԻ",
    "пятница": "ՈՒՐԲԱԹ",
    "суббота": "ՇԱԲԱԹ",
    "воскресенье": "ԿԻՐԱԿԻ",
    # Places & Objects
    "дом": "ՏՈՒՆ",
    "квартира": "ԲՆԱԿԱՐԱՆ",
    "комната": "ՍԵՆՅԱԿ",
    "дверь": "ԴՈՒՌ",
    "окно": "ԼՈՒՍԱՄՈՒՏ",
    "стол": "ՍԵՂԱՆ",
    "стул": "ԱԹՈՌ",
    "кровать": "ՄԱՀՃԱԿԱԼ",
    "телефон": "ՀԵՌԱԽՈՍ",
    "компьютер": "ՀԱՄԱԿԱՐԳԻՉ",
    "книга": "ԳԻՐՔ",
    "письмо": "ՆԱՄԱԿ",
    "деньги": "ՓՈՂ",
    "город": "ՔԱՂԱՔ",
    "улица": "ՓՈՂՈՑ",
    "магазин": "ԽԱՆՈՒԹ",
    "школа": "ԴՊՐՈՑ",
    "университет": "ՀԱՄԱԼՍԱՐԱՆ",
    "работа": "ԱՇԽԱՏԱՆՔ",
    "машина": "ՄԵՔԵՆԱ",
    "автобус": "ԱՎՏՈԲՈՒՍ",
    "поезд": "ԳՆԱՑՔ",
    "самолет": "ԻՆՔՆԱԹԻՌ",
    # Numbers
    "один": "ՄԵԿ",
    "два": "ԵՐԿՈՒ",
    "три": "ԵՐԵՔ",
    "четыре": "ՉՈՐՍ",
    "пять": "ՀԻՆԳ",
    "шесть": "ՎԵՑ",
    "семь": "ՅՈԹ",
    "восемь": "ՈՒԹ",
    "девять": "ԻՆՆԸ",
    "десять": "ՏԱՍԸ",
    "сто": "ՀԱՐՅՈՒՐ",
    "тысяча": "ՀԱԶԱՐ",
}

# Cyrillic to Armenian phonetic transliteration fallback for glosses not in core dictionary
CYRILLIC_TO_ARMENIAN_PHONETIC = {
    'а': 'Ա', 'б': 'Բ', 'в': 'Վ', 'г': 'Գ', 'д': 'Դ', 'е': 'Ե', 'ё': 'ՅՈ',
    'ж': 'Ժ', 'з': 'Զ', 'и': 'Ի', 'й': 'Յ', 'к': 'Կ', 'л': 'Լ', 'м': 'Մ',
    'н': 'Ն', 'о': 'Օ', 'п': 'Պ', 'р': 'Ր', 'с': 'Ս', 'т': 'Տ', 'у': 'ՈՒ',
    'ф': 'Ֆ', 'х': 'Խ', 'ц': 'Ց', 'ч': 'Չ', 'ш': 'Շ', 'щ': 'ՇՉ', 'ъ': '',
    'ы': 'Ը', 'ь': '', 'э': 'Է', 'ю': 'ՅՈՒ', 'я': 'ՅԱ',
    ' ': ' ', '-': '-', '_': ' '
}


def russian_gloss_to_armenian(russian_gloss: str) -> str:
    """
    Map a Russian gloss to its Armenian gloss equivalent.
    Checks core sign dictionary first; falls back to phonetic Armenian representation.
    """
    clean = russian_gloss.strip().lower()
    if clean in RUSSIAN_TO_ARMENIAN_CORE:
        return RUSSIAN_TO_ARMENIAN_CORE[clean]

    # Fallback: Phonetic mapping so every gloss has an Armenian representation
    transliterated = "".join(CYRILLIC_TO_ARMENIAN_PHONETIC.get(ch, ch.upper()) for ch in clean)
    return transliterated.strip() or "ԱՆՀԱՅՏ"


class GlossLabelMap:
    """
    Bidirectional mapping between class indices (0..K-1) and Armenian sign glosses,
    with preservation of original Russian glosses and metadata.
    """

    def __init__(
        self,
        idx_to_gloss: Optional[Dict[int, str]] = None,
        russian_to_idx: Optional[Dict[str, int]] = None,
    ):
        if idx_to_gloss is None:
            self.idx_to_gloss: Dict[int, str] = {}
            self.gloss_to_idx: Dict[str, int] = {}
        else:
            self.idx_to_gloss = {int(k): str(v) for k, v in idx_to_gloss.items()}
            self.gloss_to_idx = {str(v): int(k) for k, v in idx_to_gloss.items()}

        self.russian_to_idx: Dict[str, int] = russian_to_idx or {}

    @property
    def num_classes(self) -> int:
        return len(self.idx_to_gloss)

    def encode(self, gloss: str) -> int:
        if gloss in self.gloss_to_idx:
            return self.gloss_to_idx[gloss]
        raise KeyError(f"Gloss '{gloss}' not found in label map.")

    def decode(self, idx: int) -> str:
        if idx in self.idx_to_gloss:
            return self.idx_to_gloss[idx]
        return f"UNKNOWN_{idx}"

    def to_dict(self) -> dict:
        return {
            "num_classes": self.num_classes,
            "idx_to_gloss": {str(k): v for k, v in self.idx_to_gloss.items()},
            "russian_to_idx": self.russian_to_idx,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GlossLabelMap:
        idx_to_gloss = {int(k): str(v) for k, v in data.get("idx_to_gloss", {}).items()}
        russian_to_idx = data.get("russian_to_idx", {})
        return cls(idx_to_gloss=idx_to_gloss, russian_to_idx=russian_to_idx)

    def save(self, file_path: str | Path):
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info("Saved label map (%d classes) to %s", self.num_classes, path)

    @classmethod
    def load(cls, file_path: str | Path) -> GlossLabelMap:
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_russian_glosses(cls, russian_glosses: List[str]) -> GlossLabelMap:
        """Create a label map from a list of unique Russian glosses."""
        unique_ru = sorted(list(set(russian_glosses)))
        idx_to_gloss: Dict[int, str] = {}
        ru_to_idx: Dict[str, int] = {}

        for idx, ru in enumerate(unique_ru):
            arm = russian_gloss_to_armenian(ru)
            idx_to_gloss[idx] = arm
            ru_to_idx[ru] = idx

        return cls(idx_to_gloss=idx_to_gloss, russian_to_idx=ru_to_idx)
