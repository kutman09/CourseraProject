import os
from dotenv import load_dotenv
from google import genai

load_dotenv("mysite/.env")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# 1) какие модели доступны именно вашему ключу
for m in client.models.list():
    print(m.name)

# 2) тестовый запрос
r = client.models.generate_content(
    model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    contents="Ответь одним словом: привет",
)
print(r.text)