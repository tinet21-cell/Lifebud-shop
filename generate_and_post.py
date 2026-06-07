import os
import sys
import time
import random
import requests
from urllib.parse import quote

print(">>> СКРИПТ СТАРТУВАВ", flush=True)

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TARGET = os.environ["TELEGRAM_REVIEW_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

print(">>> СЕКРЕТИ ПРОЧИТАНО", flush=True)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
IMAGE_API = "https://image.pollinations.ai/prompt/"
IMAGE_MODEL = "gptimage"

# >>> ВПИШИ РЕАЛЬНІ ДАНІ <<<
SHOP_NAME = "Лайф Буд"
CITY = "Мукачево"
CONTACTS = "Адреса: вул. Прикладна, 1, Мукачево. Тел: 000 000 0000"  # ЗАМІНИ

ASSORTMENT = (
    "газоблоки; бетонні блоки (мучкоблоки); опалубні блоки; блоки на стовпчики; "
    "цегла рядова, вогнетривка, клінкерна, гіперпресована; гіпсокартон та комплектуючі (профілі, кріплення); "
    "штукатурка гіпсова; цементно-піщана суміш; шпаклівки; клей для гіпсокартону, плиточний, для газоблоку, монтажний; "
    "вата фасадна та внутрішня; пінопласт звичайний та екструдований; металопрофіль та металочерепиця; геотекстиль; "
    "фарба-емульсія, емаль, грунтовка, пластифікатори; цемент ПЦ-400 і ПЦ-500 (франківський та миколаївський); "
    "пісок, щебінь, відсів; піна монтажна, герметик, рідкі цвяхи; стрейч, рукавиці, саморізи, дюбелі"
)

UMBRELLAS = [
    [
        "газоблок: для яких стін підходить і чим зручний",
        "чим відрізняються газоблок, бетонний блок і цегла",
        "який клей для газоблоку обрати і як класти",
        "цегла: рядова, клінкерна, гіперпресована, вогнетривка — що для чого",
        "як розрахувати кількість блоків чи цегли на стіну",
        "типові помилки при кладці стін",
        "опалубні блоки й блоки на стовпчики: де застосувати",
    ],
    [
        "металочерепиця: як підібрати під дах",
        "металопрофіль: види й де застосовують",
        "що потрібно для монтажу покрівлі окрім черепиці",
        "як не помилитися з кількістю покрівельного матеріалу",
        "геотекстиль і його роль на даху та фундаменті",
        "типові помилки при покрівельних роботах",
        "підготовка даху: на що звернути увагу",
    ],
    [
        "вата фасадна та внутрішня: де яку застосовувати",
        "пінопласт звичайний і екструдований: для чого кожен",
        "як вибрати товщину утеплювача",
        "помилки при утепленні фасаду",
        "чим кріпити утеплювач до стіни",
        "утеплення й вентиляція: чому це важливо разом",
        "як розрахувати кількість утеплювача",
    ],
    [
        "штукатурка й шпаклівка: чим відрізняються та послідовність",
        "як підготувати стіну під фарбування",
        "грунтовка: навіщо й коли обовʼязкова",
        "фарба-емульсія та емаль: що для якої задачі",
        "скільки фарби потрібно й як не переплатити",
        "типові помилки при фінішних роботах",
        "інструмент для фінішу: валик, пензель, шпатель",
    ],
    [
        "цемент ПЦ-400 і ПЦ-500: для яких робіт який",
        "цементно-піщана суміш чи готова — коли що",
        "пісок, щебінь, відсів: чим відрізняються",
        "плиточний клей: як обрати під задачу",
        "пластифікатори: навіщо додавати в розчин",
        "як розрахувати сипучі на стяжку чи фундамент",
        "як зберігати цемент і суміші, щоб не зіпсувались",
    ],
    [
        "піна монтажна: види й коли яку брати",
        "герметик і рідкі цвяхи: для чого кожен",
        "саморізи й дюбелі: як не помилитися з вибором",
        "базовий набір розхідників для ремонту",
        "дрібниці, які часто забувають купити",
        "що тримати під рукою на будівництві",
        "як заощадити на розхідниках без втрати якості",
    ],
]

FUNNEL = ["залучення"] * 4 + ["довіра"] * 3 + ["бажання"] * 2 + ["продаж"] * 1

STAGE_INSTRUCTIONS = {
    "залучення": ("Тип: ЗАЛУЧЕННЯ. Корисна порада або розвінчання міфу в межах «{theme}». "
                  "Про магазин прямо не говори, максимум натяк."),
    "довіра": ("Тип: ДОВІРА. Поясни в межах «{theme}», що для якої задачі (види, на що звертати увагу, "
               "помилки). НЕ протиставляй товари різного призначення. Технічно коректно."),
    "бажання": ("Тип: БАЖАННЯ. Вигода для клієнта в межах «{theme}»: все в одному місці, допомога з "
                "вибором і розрахунком, наявність. Без тиску."),
    "продаж": ("Тип: МʼЯКИЙ ПРОДАЖ. У межах «{theme}» запроси завітати. Дружньо, без тиску. "
               "Контакти наприкінці: «" + CONTACTS + "». Можна запропонувати безкоштовний прорахунок кількості."),
}

# Банк візуальних прийомів для фейслес-відео (щоб не повторювались)
FACELESS_STYLES = [
    "крупний план матеріалу або інструмента в роботі",
    "процес: як кладуть блок, мішають розчин, кріплять профіль (руки майстра)",
    "до/після: було — стало на ділянці чи стіні",
    "порівняння поруч: два матеріали в кадрі, видно різницю",
    "текст-факт на фоні матеріалу, цифри зʼявляються по черзі",
    "огляд полиці/складу: асортимент, наявність",
    "слайди-картки з порадою, що змінюються під музику",
    "макрозйомка фактури матеріалу (поверхня блоку, фарби, утеплювача)",
]

ACCURACY = (
    "\n\nТОЧНІСТЬ (обовʼязково): будматеріали — технічно точно, не плутай призначення товарів і не "
    "протиставляй різнопризначені. НЕ вигадуй характеристик, марок, цифр, ДСТУ, властивостей. "
    "Не знаєш точно — формулюй загально. Поради практично коректні й безпечні. Сумнівне — прибери.\n"
)
ANTISHABLON = (
    "\n\nЗАБОРОНЕНО (ознаки ШІ): «Вона думала… а виявилось…», «Це не про…, це про…», «Уявіть собі…», "
    "«У сучасному світі», «Якісний ремонт — запорука…», «І ось тут найцікавіше», «Спойлер:»; "
    "драматичні обриви через крапку; порожні гасла, пафос, надмірні оклики; стиль ChatGPT.\n"
    "ЗАМІСТЬ ШАБЛОНІВ: конкретика — цифри, приклади, практичні дрібниці, жива мова.\n"
)
HOOK = ("\nГАЧОК: перший рядок чіпляє за секунду — конкретна користь, помилка або питання, не визначення.\n")
ENGAGE = ("\nЗАЛУЧЕННЯ: наприкінці мікрозаклик — питання в коментарі, зберегти, позначити того, кому треба.\n")


def ask_gemini(prompt, temperature=0.9, timeout=120):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    last = None
    for _ in range(3):
        try:
            r = requests.post(GEMINI_URL, params={"key": GEMINI_API_KEY}, json=body, timeout=timeout)
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            last = e
            time.sleep(6)
    raise last


def generate_video(theme):
    style = random.choice(FACELESS_STYLES)
    prompt = (
        f"Ти — власник магазину будматеріалів «{SHOP_NAME}» ({CITY}). Асортимент: {ASSORTMENT}. "
        f"Згадуй лише реальні товари. Тема: «{theme}». Ідея короткого ВЕРТИКАЛЬНОГО відео "
        "(Reels 9:16, 20-45 сек) — ГОЛОВНИЙ контент дня.\n"
        "ВІЗУАЛЬНИЙ ПРИЙОМ цього відео (використай саме його): " + style + ".\n"
        + ACCURACY + HOOK +
        "\nФормат (без markdown):\n🎬 ІДЕЯ:\n🪝 Гачок (перші 3 секунди):\n\n"
        "🗣 ВАРІАНТ А — ГОВОРИТИ В КАМЕРУ\nГотовий розмовний текст для зйомки в магазині (20-40 сек). Повний текст.\n\n"
        "📱 ВАРІАНТ Б — ЗЙОМКА БЕЗ СЕБЕ\nКадри САМЕ за вказаним прийомом, телефон вертикально, що показати по кадрах + текст на екран.\n\n"
        "🎵 Музика (бібліотека Facebook/Instagram):\n📲 Підпис (1-2 живі речення + 3-4 хештеги + заклик коментувати):"
        + ANTISHABLON + "\nЖива людська українська, практично."
    )
    return ask_gemini(prompt)


def generate_post(theme, stage):
    instr = STAGE_INSTRUCTIONS[stage].format(theme=theme)
    prompt = (
        f"Ти ведеш сторінку магазину «{SHOP_NAME}» ({CITY}). Асортимент: {ASSORTMENT}. Згадуй лише ці товари. "
        "Пишеш для людей, що будують/ремонтують, просто, на «ви». Це КОРОТКА підтримка до відео дня.\n\n"
        + instr + "\nКОРОТКО, конкретно, по користі." + ACCURACY + HOOK + ENGAGE + ANTISHABLON +
        "\nВАЖЛИВО: саме цей конкретний кут. 300-550 символів. 3-4 хештеги (будівництво, Мукачево). "
        "Без markdown, емодзі помірно. Поверни ЛИШЕ текст поста."
    )
    return ask_gemini(prompt)


def generate_carousel(theme):
    prompt = (
        f"Ти — магазин будматеріалів «{SHOP_NAME}» ({CITY}). Асортимент: {ASSORTMENT}. Згадуй лише реальні товари. "
        "Зроби КАРУСЕЛЬ для Instagram на тему «" + theme + "» (6 слайдів), мінімум тексту на слайді."
        + ACCURACY + HOOK +
        "\nФормат (без markdown):\n"
        "СЛАЙД 1 (обкладинка-гачок): сильний короткий заголовок (питання/помилка/факт).\n"
        "СЛАЙД 2: аспект + 1-2 рядки.\nСЛАЙД 3: аспект + 1-2 рядки.\nСЛАЙД 4: аспект + 1-2 рядки.\n"
        "СЛАЙД 5: головна порада/висновок.\n"
        "СЛАЙД 6 (CTA): зберегти, щоб не загубити; завітати в магазин по матеріали; "
        "контакти: «" + CONTACTS + "».\n\n"
        "📲 ПІДПИС ПІД ПОСТ: перші 2 рядки — гачок (Instagram показує лише їх!), далі розкриття, "
        "наприкінці заклик + 3-4 хештеги."
        + ANTISHABLON + "\nЖива людська українська, практично."
    )
    return ask_gemini(prompt)


def make_image_prompt(theme):
    try:
        scene = ask_gemini(
            "Опиши ОДНУ коротку англійською реалістичну сцену (макс 14 слів) для поста магазину будматеріалів "
            f"на тему: «{theme}». Будівництво, матеріали, чисто. Без тексту й логотипів. Поверни лише англійський опис.",
            temperature=1.0, timeout=60,
        ).replace("\n", " ").strip()
    except Exception:
        scene = "construction materials, building blocks and tools, clean tidy site"
    return f"{scene}, photorealistic, real photograph, natural light, high quality, no text, no logo, no watermark"


def get_image(image_prompt):
    url = IMAGE_API + quote(image_prompt)
    r = requests.get(url, params={"width": 1024, "height": 1024, "nologo": "true",
                                  "model": IMAGE_MODEL, "seed": random.randint(1, 999999),
                                  "enhance": "true"}, timeout=180)
    r.raise_for_status()
    return r.content


def split_text(text, limit=4000):
    text = text.strip()
    if len(text) <= limit:
        return [text]
    parts = []
    while len(text) > limit:
        chunk = text[:limit]
        cut = chunk.rfind("\n\n")
        if cut < limit * 0.5:
            cut = chunk.rfind("\n")
        if cut < limit * 0.5:
            cut = chunk.rfind(". ")
            if cut != -1:
                cut += 1
        if cut < limit * 0.5:
            cut = limit
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        parts.append(text)
    return parts


def send_photo(image_bytes, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    if len(caption) <= 1024:
        files = {"photo": ("post.jpg", image_bytes, "image/jpeg")}
        data = {"chat_id": TARGET, "caption": caption}
        r = requests.post(url, data=data, files=files, timeout=60)
        r.raise_for_status()
        return r.json()
    files = {"photo": ("post.jpg", image_bytes, "image/jpeg")}
    data = {"chat_id": TARGET}
    r = requests.post(url, data=data, files=files, timeout=60)
    r.raise_for_status()
    send_text(caption)
    return r.json()


def send_text(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    last = None
    for part in split_text(text, 4000):
        r = requests.post(url, json={"chat_id": TARGET, "text": part,
                                     "disable_web_page_preview": True}, timeout=30)
        r.raise_for_status()
        last = r.json()
    return last


def current_subtopic():
    day = int(time.time() // 86400)
    return UMBRELLAS[(day // 7) % len(UMBRELLAS)][day % 7]


def pick_theme_and_stage():
    day = int(time.time() // 86400)
    return current_subtopic(), FUNNEL[day % len(FUNNEL)]


def main():
    print(">>> MAIN ПОЧАВСЯ", flush=True)
    theme, stage = pick_theme_and_stage()
    day = int(time.time() // 86400)
    print("Кут:", theme, "| Стадія:", stage, flush=True)

    # ВІДЕО — головне, першим
    try:
        idea = generate_video(theme)
        send_text("🎥 ВІДЕО ДНЯ (головне) — тема: " + theme + "\n\n" + idea)
        print(">>> Надіслано відео.", flush=True)
    except Exception as e:
        print(">>> Відео не вдалося:", e, file=sys.stderr, flush=True)

    time.sleep(2)

    # Раз на 4 дні — карусель замість поста
    if day % 4 == 1:
        try:
            carousel = generate_carousel(theme)
            send_text("🎠 КАРУСЕЛЬ ДЛЯ INSTAGRAM/FB — тема: " + theme +
                      "\n(оформи слайди в Canva → постни в Instagram/Facebook)\n\n" + carousel)
            print(">>> Надіслано карусель.", flush=True)
        except Exception as e:
            print(">>> Карусель не вдалася:", e, file=sys.stderr, flush=True)
        return

    # Інші дні — пост-підтримка з картинкою
    post = generate_post(theme, stage)
    try:
        send_photo(get_image(make_image_prompt(theme)), post)
        print(">>> Надіслано пост.", flush=True)
    except Exception as e:
        print(">>> Без картинки:", e, file=sys.stderr, flush=True)
        send_text(post)


if __name__ == "__main__":
    main()
