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
    "цегла рядова, вогнетривка, клінкерна, гіперпресована; "
    "гіпсокартон та комплектуючі (профілі, кріплення); "
    "штукатурка гіпсова; цементно-піщана суміш; шпаклівки; "
    "клей для гіпсокартону, клей плиточний, клей для газоблоку, клей монтажний; "
    "вата фасадна та внутрішня; пінопласт звичайний та екструдований; "
    "металопрофіль та металочерепиця; геотекстиль; "
    "фарба-емульсія, емаль, грунтовка, пластифікатори; "
    "цемент ПЦ-400 і ПЦ-500 (франківський та миколаївський); "
    "пісок, щебінь, відсів; піна монтажна, герметик, рідкі цвяхи; "
    "стрейч, рукавиці, саморізи, дюбелі"
)

# Тематичні тижні-парасольки за категоріями (тримається ~7 днів)
UMBRELLAS = [
    "стіни: блоки, цегла, що для чого",
    "дах і покрівля: металочерепиця, профіль",
    "утеплення: вата, пінопласт, фасад",
    "фінішні роботи: штукатурка, шпаклівка, фарба",
    "сипучі та суміші: цемент, пісок, щебінь, клеї",
    "монтаж і розхідники: піна, кріплення, інструмент",
]

# Воронка: 40% залучення, 30% довіра/експертність, 20% бажання, 10% продаж
FUNNEL = (
    ["залучення"] * 4 +
    ["довіра"] * 3 +
    ["бажання"] * 2 +
    ["продаж"] * 1
)

STAGE_INSTRUCTIONS = {
    "залучення": (
        "Тип: ЗАЛУЧЕННЯ. Дай корисну практичну пораду або розвінчай поширений міф у межах теми «{theme}». "
        "Щоб люди зберегли пост. Про магазин прямо не говори, максимум натяк наприкінці."
    ),
    "довіра": (
        "Тип: ДОВІРА/ЕКСПЕРТНІСТЬ. Поясни в межах теми «{theme}», що для якої задачі підходить "
        "(види, на що звертати увагу, типові помилки). НЕ протиставляй товари різного призначення як "
        "конкурентів — покажи, що для чого. Будь технічно коректним. Покажи, що в магазині розуміються на справі."
    ),
    "бажання": (
        "Тип: БАЖАННЯ. Покажи вигоду для клієнта в межах теми «{theme}»: зручність купити все в одному місці, "
        "допомога з вибором і розрахунком, наявність. Без тиску — через користь."
    ),
    "продаж": (
        "Тип: МʼЯКИЙ ПРОДАЖ. У межах теми «{theme}» запроси завітати в магазин. Дружньо, без тиску. "
        "Наприкінці природний заклик і контакти: «" + CONTACTS + "». Можна запропонувати безкоштовно "
        "прорахувати кількість матеріалу."
    ),
}


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


ANTISHABLON = (
    "\n\nСУВОРО ЗАБОРОНЕНО (ознаки штучного тексту):\n"
    "- звороти-шаблони: «Вона думала… а виявилось…», «Це не про…, це про…», «Уявіть собі…», "
    "«У сучасному світі», «Якісний ремонт — запорука…», «І ось тут починається найцікавіше», «Спойлер:»;\n"
    "- драматичні обриви короткими реченнями через крапку;\n"
    "- порожні гасла, пафос, штучний захват, надмірні знаки оклику;\n"
    "- будь-який стиль, що впізнається як ChatGPT.\n"
    "ЗАМІСТЬ ШАБЛОНІВ: конкретика — цифри, приклади, практичні дрібниці, жива мова.\n"
)


def generate_post(theme, stage):
    instr = STAGE_INSTRUCTIONS[stage].format(theme=theme)
    prompt = (
        f"Ти ведеш сторінку магазину будівельних матеріалів «{SHOP_NAME}» з міста {CITY}. "
        f"Асортимент магазину: {ASSORTMENT}. Згадуй лише товари з цього асортименту, не вигадуй зайвого. "
        "Пишеш для звичайних людей, які будують або роблять ремонт, простою зрозумілою мовою, на «ви».\n\n"
        + instr +
        "\n\nТОН: дружній, корисний, впевнений, без надмірного пафосу. Конкретика й користь."
        + ANTISHABLON +
        "\nОбсяг 400-700 символів. Живий перший рядок. 3-4 хештеги (будівництво, будматеріали, Мукачево). "
        "Без markdown, звичайний текст, емодзі помірно. Поверни ЛИШЕ готовий текст поста."
    )
    return ask_gemini(prompt)


def make_image_prompt(theme):
    try:
        scene = ask_gemini(
            "Опиши ОДНУ коротку англійською реалістичну сцену (макс 14 слів) для поста "
            f"магазину будматеріалів на тему: «{theme}». Будівництво, матеріали, інструменти, чисто. "
            "Без тексту й логотипів. Поверни лише англійський опис.",
            temperature=1.0, timeout=60,
        ).replace("\n", " ").strip()
    except Exception:
        scene = "construction materials, building blocks and tools, clean tidy site"
    realism = "photorealistic, real photograph, natural light, high quality, no text, no logo, no watermark"
    return f"{scene}, {realism}"


def generate_video_idea(theme):
    prompt = (
        f"Ти — контент-менеджер магазину будматеріалів «{SHOP_NAME}» ({CITY}). Асортимент: {ASSORTMENT}. "
        f"Тема тижня: «{theme}». Згадуй лише реальні товари, будь технічно коректним.\n\n"
        "Запропонуй ідею короткого ВЕРТИКАЛЬНОГО відео (Reels, 9:16, 15-40 сек), гачок у перші 3 секунди.\n\n"
        "Дай ДВА варіанти однієї ідеї (звичайний текст, без markdown):\n\n"
        "🎬 ІДЕЯ: (назва)\n\n"
        "🤖 ВАРІАНТ 1 — ПРОМТ ДЛЯ AI-ВІДЕО: готовий промт англійською (vertical 9:16, сцена, рух камери, "
        "світло), готовий до копіювання. + який текст накласти українською.\n\n"
        "📱 ВАРІАНТ 2 — ЗЙОМКА ТЕЛЕФОНОМ: прості кадри в магазині/на обʼєкті, телефон вертикально, "
        "що показати по кадрах + текст на екран.\n\n"
        "🎵 Музика: (настрій + з бібліотеки Facebook/Instagram)\n"
        "📲 Підпис: (1-2 живі речення + 3-4 хештеги)\n"
        + ANTISHABLON +
        "\nЖива людська українська, практично."
    )
    return ask_gemini(prompt)


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


def pick_theme_and_stage():
    day = int(time.time() // 86400)
    umbrella = UMBRELLAS[(day // 7) % len(UMBRELLAS)]
    stage = FUNNEL[day % len(FUNNEL)]
    return umbrella, stage


def main():
    print(">>> MAIN ПОЧАВСЯ", flush=True)
    theme, stage = pick_theme_and_stage()
    print("Парасолька:", theme, "| Стадія воронки:", stage, flush=True)

    post = generate_post(theme, stage)
    print("Пост:\n", post, flush=True)
    try:
        send_photo(get_image(make_image_prompt(theme)), post)
        print(">>> Надіслано пост.", flush=True)
    except Exception as e:
        print(">>> Без картинки:", e, file=sys.stderr, flush=True)
        send_text(post)

    time.sleep(2)
    try:
        idea = generate_video_idea(theme)
        send_text("💡 ВІДЕО-ІДЕЯ ДНЯ (вертикальне)\n\n" + idea)
        print(">>> Надіслано відео-ідею.", flush=True)
    except Exception as e:
        print(">>> Відео-ідея не вдалася:", e, file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
