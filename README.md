# Course Project

Backend онлайн-курсов: Python 3.12, FastAPI, SQLAlchemy 2.x, SQLite, Pydantic v2.

## Запуск

Команды выполняются из корня проекта. Существующая `.venv` при доработке не изменялась.

```powershell
python -m pip install -r req.txt
# Только если mysite/.env ещё нет:
Copy-Item mysite/.env.example mysite/.env
# Замените SECRET_KEY в mysite/.env случайным секретом длиной от 32 символов.
python seed.py
python main.py
# Альтернативный запуск:
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

База `database.db` всегда находится в корне проекта, независимо от рабочего каталога.
Таблицы создаются в lifespan; seed тоже создаёт их перед заполнением.
Для старой несовместимой схемы остановите сервер, удалите только корневой `database.db`, затем выполните seed заново. Миграции не используются.
Seed идемпотентный: повторный запуск сохраняет существующие записи и их пароли.

- Swagger: http://127.0.0.1:8001/docs
- Админка: http://127.0.0.1:8001/admin
- В Swagger нажмите **Authorize**, в поле **username** введите email, затем пароль. `client_id` и `client_secret` оставьте пустыми.
- Токен передаётся как `Authorization: Bearer <access_token>`.

## Тестовые аккаунты

Пароль у всех: `Test12345!`.

| Email | Роль | is_active |
| --- | --- | --- |
| admin@test.kg | admin | true |
| teacher@test.kg | teacher | true |
| manager@test.kg | manager | true |
| student@test.kg | student | true |
| student_inactive@test.kg | student | false |

Регистрация принимает `full_name`, `email`, `password`; роль всегда student. Неизвестные поля отклоняются с 422.
Email нормализуется в нижний регистр. Пароли хранятся только как bcrypt-хеши, допустимы от 8 символов до 72 байт UTF-8.
Неактивный студент может войти: его `is_active` ограничивает заявки на plus, а не аутентификацию.

## ТЗ → эндпоинт → роль

Во всех проверках ролей admin имеет доступ. Ошибки: 401 — нужен токен, 403 — недостаточно прав, 404 — объект отсутствует или скрыт queryset.

| ТЗ | Эндпоинт | Допуск |
| --- | --- | --- |
| Регистрация / вход | POST /auth/register/, /auth/login/, /auth/token/ | Все |
| Свой профиль | GET, PUT /users/me/ | Любой с токеном |
| Пользователи | GET /users/, GET, PUT /users/{id}/ | admin |
| Категории: чтение | GET /category/, /category/{id}/ | Все, без токена |
| Категории: изменение | POST /category/, PUT, DELETE /category/{id}/ | admin |
| Курсы: чтение | GET /course/, /course/{id}/ | Все, без токена |
| Курсы: изменение | POST /course/, PUT, DELETE /course/{id}/ | teacher, admin |
| Группы: чтение | GET /group/, /group/{id}/ | Все, без токена |
| Группы: создание | POST /group/ | teacher, admin |
| Группы: изменение | PUT, DELETE /group/{id}/ | teacher-владелец, admin |
| Заявка | POST /application/ | student, admin; student_id из JWT |
| Работа с заявками | GET /application/, GET, PUT, DELETE /application/{id}/ | manager, admin |
| Участие в группе | POST /enrollment/ | student, admin; student_id из JWT |
| Участия: чтение | GET /enrollment/, /enrollment/{id}/ | student: свои; teacher: свои группы; manager/admin: все |
| Участия: изменение | PUT /enrollment/{id}/ | Тот же queryset; student может только cancelled |
| Участия: удаление | DELETE /enrollment/{id}/ | Тот же queryset |
| AI | POST /ai/search/, /ai/answer/, /ai/analyze/ | Все, без токена |
| Админка | /admin | Только admin по email/паролю |

`POST /group/` и `PUT /group/{id}/` принимают `name`, `course_id`, `starts_on`, `ends_on`, `status`, `capacity`.
Для teacher `teacher_id` всегда берётся из JWT; для admin его необходимо указать, и выбранный пользователь должен иметь роль teacher.
`ends_on > starts_on`, `capacity > 0`. Нельзя уменьшить capacity ниже числа active-участий.

«Студент создаёт участие в группе» означает `POST /enrollment/` с `{"group_id":1}`.
Группа должна быть recruiting; учитываются только active-участия, активные дубли запрещены.
SQLite `BEGIN IMMEDIATE` сериализует проверку мест и создание записи. Повторная активация менеджером/учителем также проверяет места и набор.
Для записи не требуется принятая заявка: такого условия в ТЗ нет. `is_active` студента не ограничивает enrollment.
Заявка принимает только `course_id`, `comment`; менеджер меняет только `status`, `comment`, а `manager_id` определяется токеном.

## AI

По умолчанию `AI_MODE=rules`: без внешних запросов. Поиск учитывает активность курса, категорию, цену, статус и список уровней.
Поиск текста выполняется в Python через casefold; несколько оставшихся значимых слов объединяются условием «все слова найдены».
В AI-выдаче level — строка; в обычном CRUD — JSON-список.
`text` и `facts` ограничены 5000 символами, `question` — 500. Пустой текст и одни пробелы дают 422.

Примеры для bash (в Windows можно сохранить JSON в UTF-8-файл и передать `curl.exe --data-binary @request.json`):

```bash
curl -X POST http://127.0.0.1:8001/ai/search/ -H 'Content-Type: application/json' -d '{"question":"Python среднего уровня"}'
curl -X POST http://127.0.0.1:8001/ai/answer/ -H 'Content-Type: application/json' -d '{"text":"Верните деньги","facts":"Оплата прошла 3 дня назад"}'
curl -X POST http://127.0.0.1:8001/ai/answer/ -H 'Content-Type: application/json' -d '{"text":"Когда начнётся набор?"}'
curl -X POST http://127.0.0.1:8001/ai/analyze/ -H 'Content-Type: application/json' -d '{"text":"Не могу зайти в личный кабинет, пишет неверный пароль"}'
```

Опционально: установите `langchain[openai]`, задайте `AI_MODE=llm` и `LLM_API_KEY` в `.env`.
Провайдер — OpenAI через LangChain, модель gpt-4o-mini. Общий таймаут 20 секунд, повторных попыток нет.
LLM получает вход и эталон rules; результат принимается только при полном совпадении с эталоном.
Это намеренно строгий режим: факты, фильтры и дословные шаблоны ТЗ не могут быть изменены моделью.
При отсутствии ключа, пакета, сетевой ошибке, таймауте, некорректном JSON или отличии ответа возвращается rules.
С реальным ключом внешние вызовы не проверялись; fallback проверен имитацией провайдера.

## Проверки

```powershell
python -m pytest -q -W error
python -W error -m compileall -q main.py seed.py mysite tests scripts
python -W error -c "import main; print('main import OK')"
# При работающем python main.py:
python scripts/verify_live.py
```

Тесты используют отдельную in-memory SQLite, StaticPool, foreign_keys=ON и dependency_overrides.
Живой сценарий вызывает curl, регистрирует отдельного тестового студента, создаёт и обрабатывает заявку, записывает в группу, проверяет AI и освобождает тестовое место.
JWT скрываются в сохранённых результатах. Seed-аккаунты и курсы сценарий не меняет.

Доказательства: `verification/pytest.txt`, `verification/checks.txt`, `verification/server_startup.txt`, `verification/live_responses.json`, `verification/swagger_authorized.png`, `verification/admin_users.png`; полный отчёт — `IMPLEMENTATION_REPORT.md`.
Дополнительно к перечню ТЗ нужны itsdangerous (подпись сессий sqladmin) и pin AnyIO 4.9.0 (совместимость TestClient без предупреждений).

`pytest.ini` ограничивает сборку каталогом `tests/`, поэтому отдельный ручной `mysite/test_gemini.py` не запускается автоматически и не требует установки google-genai для backend.
