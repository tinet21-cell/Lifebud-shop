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

# >>> ВПИШИ СВОЇ РЕАЛЬНІ ДАНІ <<<
SHOP_NAME = "Лайф Буд"
CITY = "Мукачево"
CONTACTS = "Адреса: вул. Прикладна, 1, Мукачево. Тел: 000 000 0000"  # ЗАМІНИ на справжні

# Типи постів: продаючі, поради, огляди — чергуються
POST_TYPES = [
    ("порада", "Дай практичну корисну пораду для людей, які роблять ремонт, на тему: «{topic}». Конкретно й по суті, без води."),
    ("огляд категорії", "Зроби короткий зрозумілий огляд категорії товару на тему «{topic}»: на що звертати увагу при виборі, типові помилки покупців."),
    ("продаючий", "Напиши короткий привабливий пост, що мотивує завітати в магазин по товар із теми «{topic}». Покажи вигоду для клієнта, без агресивного тиску."),
    ("сезонний", "Напиши пост, привʼязаний до сезону (зараз літо: дача, сад, ремонт у теплу пору), навколо теми «{topic}»."),
    ("міф і факт", "Візьми поширену помилку або міф про ремонт/будматеріали на тему «{topic}» і коротко розвій його, давши правильну пораду."),
]

TOPICS = [
    "як вибрати фарбу для стін: матова чи мийна",
    "скільки фарби потрібно на кімнату й як не переплатити",
    "грунтовка: навіщо вона і чи можна без неї",
    "як вибрати шпаклівку: стартова, фінішна, універсальна",
    "гіпсокартон: вологостійкий, звичайний, вогнестійкий — у чому різниця",
    "як рівно зашпаклювати стіну: покрокова порада новачку",
    "сухі будівельні суміші: як не помилитися з вибором",
    "інструменти для фарбування: валик, пензель, що краще",
    "як підготувати стіну під фарбування",
    "клей для плитки: який обрати для ванної",
    "як розрахувати кількість матеріалів для ремонту",
    "помилки при виборі фарби, через які псується ремонт",
    "профілі й кріплення для гіпсокартону: що до чого",
    "наливна підлога: коли потрібна і як працює",
    "чим утеплити стіни: огляд варіантів",
]


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


def generate_post(topic, type_instruction, add_contacts):
    contact_line = ""
    if add_contacts:
        contact_line = ("Наприкінці природно додай заклик завітати в магазин і вкажи контакти: "
                        f"«{CONTACTS}». ")
    prompt = (
        f"Ти ведеш сторінку магазину будівельних товарів «{SHOP_NAME}» з міста {CITY}. "
        "Пишеш для звичайних людей, які роблять ремонт удома, простою зрозумілою мовою. "
        + type_instruction.format(topic=topic) + " "
        + contact_line +
        "\n\nЯК ПИСАТИ:\n"
        "- Жива природна українська, дружній тон, звертайся на «ви».\n"
        "- Конкретика й користь: цифри, приклади, практичні дрібниці.\n"
        "- Без води, без канцеляриту, без надмірного пафосу.\n"
        "- Продавай мʼяко, через користь для клієнта.\n\n"
        "ЗАБОРОНЕНО: кліше «У сучасному світі», «Якісний ремонт — запорука…», порожні гасла, "
        "надмірні знаки оклику, штучний захват.\n\n"
        "Обсяг 400-700 символів. Живий перший рядок, що чіпляє. "
        "Додай 3-4 доречні хештеги (ремонт, будматеріали, магазин, місто). "
        "Без markdown, звичайний текст, емодзі помірно. Поверни ЛИШЕ готовий текст поста."
    )
    return ask_gemini(prompt)


def make_image_prompt(topic):
    try:
        scene = ask_gemini(
            "Опиши ОДНУ коротку англійською реалістичну сцену (макс 14 слів) для поста "
            f"магазину будматеріалів на тему: «{topic}». Ремонт, інструменти, матеріали, "
            "чисто й охайно. Без тексту й логотипів. Поверни лише англійський опис.",
            temperature=1.0, timeout=60,
        ).replace("\n", " ").strip()
    except Exception:
        scene = "clean modern home renovation, paint cans and roller, bright tidy room"
    realism = ("photorealistic, real photograph, natural light, high quality, "
               "no text, no logo, no watermark")
    return f"{scene}, {realism}"


def get_image(image_prompt):
    url = IMAGE_API + quote(image_prompt)
    r = requests.get(url, params={"width": 1024, "height": 1024, "nologo": "true",
                                  "model": IMAGE_MODEL, "seed": random.randint(1, 999999),
                                  "enhance": "true"}, timeout=180)
    r.raise_for_status()
    return r.content


def send_photo(image_bytes, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {"photo": ("post.jpg", image_bytes, "image/jpeg")}
    data = {"chat_id": TARGET, "caption": caption[:1024]}
    r = requests.post(url, data=data, files=files, timeout=60)
    r.raise_for_status()
    return r.json()


def send_text(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": TARGET, "text": text, "disable_web_page_preview": True}, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    print(">>> MAIN ПОЧАВСЯ", flush=True)
    topic = random.choice(TOPICS)
    type_name, type_instr = random.choice(POST_TYPES)
    add_contacts = random.random() < 0.5
    print("Тема:", topic, "| Тип:", type_name, "| Контакти:", add_contacts, flush=True)
    post = generate_post(topic, type_instr, add_contacts)
    print("Пост:\n", post, flush=True)
    try:
        image = get_image(make_image_prompt(topic))
        send_photo(image, post)
        print(">>> Надіслано з картинкою.", flush=True)
    except Exception as e:
        print(">>> Без картинки:", e, file=sys.stderr, flush=True)
        send_text(post)
        print(">>> Надіслано текстом.", flush=True)


if __name__ == "__main__":
    main()
