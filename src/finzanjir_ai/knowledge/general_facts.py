"""Small, curated offline general-knowledge fact pack.

These are source-backed fact cards, not a pretrained model or open-domain generator.
Unknown questions deliberately fall through to the configured provider or an
honest limitation message.
"""
from __future__ import annotations

from finzanjir_ai.language.normalization import normalize_multilingual_text


_SKY = {
    "uz": "Osmon ko'k ko'rinishining asosiy sababi — Rayleigh sochilishi: atmosfera molekulalari qisqa to'lqinli ko'k nurni qizil nurga qaraganda kuchliroq sochadi. Shu sochilgan ko'k yorug'lik turli yo'nalishlardan ko'zimizga yetib keladi. Binafsha nur ham kuchli sochiladi, ammo ko'zimiz ko'k rangga sezgirroq.",
    "kaa": "Aspannıń kók kóriniwiniń tiykarǵı sebebi — Rayleigh shashırawı: atmosfera molekulaları qısqa tolqınlı kók nurdı qızıl nurǵa qaraǵanda kúshlirek shashıratadı. Sol shashıraǵan kók jaqtılıq hár tárepten kózimizge jetip keledi. Kók hám binafsha nur shashırasa da, kózimiz kók reńge sezgirirek.",
    "kk": "Аспанның көк болып көрінуінің негізгі себебі — Рэлей шашырауы: атмосфера молекулалары қысқа толқынды көк жарықты қызыл жарыққа қарағанда күштірек шашыратады. Шашыраған көк жарық әр бағыттан көзімізге жетеді. Күлгін жарық та қатты шашырайды, бірақ көзіміз көк түске сезімталырақ.",
    "ru": "Небо кажется голубым главным образом из-за рэлеевского рассеяния: молекулы атмосферы рассеивают коротковолновый синий свет сильнее, чем красный. Рассеянный свет приходит к нам со многих направлений. Фиолетовый свет тоже рассеивается сильно, но человеческий глаз чувствительнее к синему.",
    "en": "The sky looks blue mainly because of Rayleigh scattering: molecules in the atmosphere scatter shorter-wavelength blue light more strongly than red light. The scattered blue light reaches our eyes from many directions. Violet light is also scattered strongly, but human vision is more sensitive to blue.",
}

_UZBEKISTAN = {
    "uz": "O‘zbekiston Markaziy Osiyoda joylashgan va dengizga bevosita chiqish yo‘li yo‘q davlat. U Qozog‘iston, Qirg‘iziston, Tojikiston, Turkmaniston va Afg‘oniston bilan chegaradosh. Poytaxti — Toshkent. Bu javob barqaror geografik ma’lumotlarga asoslangan; aholi soni kabi vaqt o‘tishi bilan o‘zgaradigan raqamlarni keltirmadim.",
    "kaa": "Ózbekstan Oraylıq Aziyada jaylasqan hám teńizge tikkeley shıǵıw jolı joq mámleket. Ol Qazaqstan, Qırǵızstan, Tájikstan, Túrkmenstan hám Awǵanstan menen shegaralas. Paytaxtı — Tashkent. Bul juwap turaqlı geografiyalıq maǵlıwmatlarǵa tiykarlanǵan; xalıq sanı sıyaqlı waqıt penen ózgeretuǵın sanlardı keltirmedim.",
    "kk": "Өзбекстан Орталық Азияда орналасқан және теңізге тікелей шығатын жолы жоқ мемлекет. Ол Қазақстан, Қырғызстан, Тәжікстан, Түрікменстан және Ауғанстанмен шектеседі. Астанасы — Ташкент. Бұл жауап тұрақты географиялық деректерге негізделген; халық саны сияқты уақыт өте өзгеретін сандарды қоспадым.",
    "ru": "Узбекистан расположен в Центральной Азии и не имеет прямого выхода к морю. Он граничит с Казахстаном, Кыргызстаном, Таджикистаном, Туркменистаном и Афганистаном. Столица — Ташкент. Здесь приведены устойчивые географические сведения; изменяющиеся со временем показатели, например численность населения, не приводятся.",
    "en": "Uzbekistan is in Central Asia and has no direct access to the sea. It borders Kazakhstan, Kyrgyzstan, Tajikistan, Turkmenistan, and Afghanistan. Its capital is Tashkent. This answer uses stable geographic facts and omits time-sensitive figures such as population.",
}

_TORTOISE = {
    "uz": "Toshbaqaning umri turiga va yashash sharoitiga bog‘liq. San Diego Zoo ma’lumotiga ko‘ra, ayrim suvda yashovchi turlar taxminan 70 yil, ayrim quruqlik toshbaqalari esa 150 yil yoki undan ko‘proq yashashi mumkin. Shuning uchun aniqroq javob uchun toshbaqaning turi kerak.",
    "kaa": "Tasbaqanıń ómiri túrine hám jasaw sharayatına baylanıslı. San Diego Zoo maǵlıwmatına kóre, ayırım suw tasbaqaları shama menen 70 jıl, ayırım qurǵaqlıq tasbaqaları bolsa 150 jıl yamasa onnan da kóp jasawı múmkin. Anıǵıraq juwap ushın tasbaqanıń túrin biliw kerek.",
    "kk": "Тасбақаның өмір сүру ұзақтығы оның түрі мен тіршілік жағдайына байланысты. San Diego Zoo дерегіне сай, кейбір су тасбақалары шамамен 70 жыл, ал кейбір құрлық тасбақалары 150 жыл немесе одан да ұзақ өмір сүре алады. Нақтырақ жауап беру үшін тасбақаның түрін білу қажет.",
    "ru": "Продолжительность жизни черепах зависит от вида и условий. По данным San Diego Zoo, некоторые водные виды живут около 70 лет, а отдельные сухопутные черепахи могут жить 150 лет и дольше. Для более точного ответа нужно знать вид черепахи.",
    "en": "A turtle's or tortoise's lifespan depends on its species and living conditions. San Diego Zoo says some aquatic species live about 70 years, while some land tortoises can live 150 years or more. The exact estimate depends on the species.",
}

def _language(language: str) -> str:
    return language if language in {"uz", "kaa", "kk", "ru", "en"} else "uz"


def _has_any(text: str, values: tuple[str, ...]) -> bool:
    return any(value in text for value in values)


def _fact_kind(query: str) -> str | None:
    text = normalize_multilingual_text(query)
    words = set(text.split())

    country = _has_any(text, (
        "o'zbekiston", "ozbekiston", "uzbekistan", "өзбекстан",
        "ózbekstan", "ozbekstan", "узбекистан",
    ))
    about = _has_any(text, (
        "haqida", "ma'lumot", "malumot", "about", "tell me", "расскажи",
        "об узбекистане", "туралы", "мәлімет", "ҳаққында", "haqqında",
        "maǵlıwmat",
    ))
    if country and about:
        return "uzbekistan"

    sky = _has_any(text, ("osmon", "sky", "небо", "aspan", "aspannıń", "aspanning"))
    blue = _has_any(text, ("ko'k", "kok", "көк", "голуб", "blue", "kók", "kоk"))
    if sky and blue:
        return "sky"

    animal = _has_any(text, (
        "toshbaqa", "toshvaqa", "tasbaqa", "tasbaq", "черепах",
        "turtle", "tortoise",
    ))
    lifespan = _has_any(text, (
        "umr", "yil", "yashay", "qancha", "necha", "lifespan", "live",
        "years", "long", "сколько", "лет", "живет", "жить", "жыл",
        "өмір", "жас", "ómir", "jıl",
    ))
    if animal and lifespan:
        return "tortoise"
    return None


def supports_local_general_fact(query: str) -> bool:
    """True only for narrowly scoped, source-backed offline fact cards."""
    return _fact_kind(query) is not None


_GENERAL_TOPIC_MARKERS = (
    "o'zbekiston", "ozbekiston", "uzbekistan", "узбекистан", "өзбекстан",
    "ózbekstan", "ozbekstan", "geografiya", "geography", "география",
    "iqtisodiyot", "economy", "экономика", "tarix", "history", "история",
    "fizika", "physics", "физика", "kimyo", "chemistry", "химия",
    "biologiya", "biology", "биология", "astronomiya", "astronomy", "астрономия",
    "sayyora", "planet", "планет", "mars", "earth", "yer", "земля",
    "quyosh", "sun", "солнц", "osmon", "sky", "небо", "aspan",
    "hayvon", "animal", "животн", "toshbaqa", "toshvaqa", "turtle",
    "tortoise", "черепах", "photosynthesis", "фотосинтез", "gravitatsiya",
    "gravity", "гравитац", "fan", "science", "наука",
)


def supports_general_knowledge_intent(query: str) -> bool:
    """Route clear non-project subject questions to general knowledge.

    This is a domain-routing heuristic, not a claim that the local fact pack
    contains an answer for every listed topic.
    """
    if supports_local_general_fact(query):
        return True
    text = normalize_multilingual_text(query)
    return any(marker in text for marker in _GENERAL_TOPIC_MARKERS)


def answer_local_general_fact(
    query: str, language: str
) -> tuple[str, tuple[str, ...], tuple[str, ...]] | None:
    """Return (answer, source IDs, source URLs), or None when no card matches."""
    kind = _fact_kind(query)
    if kind is None:
        return None
    lang = _language(language)
    if kind == "sky":
        return (
            _SKY[lang],
            ("general_sky_blue_noaa", "general_sky_blue_nasa"),
            (
                "https://www.weather.gov/fgz/SkyBlue",
                "https://spaceplace.nasa.gov/blue-sky/en/",
            ),
        )
    if kind == "uzbekistan":
        return (
            _UZBEKISTAN[lang],
            ("general_uzbekistan_geography_world_bank", "general_uzbekistan_geography_unfccc"),
            (
                "https://documents1.worldbank.org/curated/en/620601593145818606/pdf/Uzbekistan-Building-Blocks-for-Integrated-Transport-and-Logistics-Development-Policy-Paper.pdf",
                "https://unfccc.int/sites/default/files/resource/4NC_Uzbekistan_ENG_14%2010_SEC.pdf",
            ),
        )
    return (
        _TORTOISE[lang],
        ("general_tortoise_lifespan_sandiego_zoo", "general_aldabra_tortoise_smithsonian"),
        (
            "https://animals.sandiegozoo.org/animals/turtle-and-tortoise",
            "https://nationalzoo.si.edu/animals/aldabra-tortoise",
        ),
    )
