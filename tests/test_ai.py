import asyncio
import pytest
from mysite.config import settings
from mysite.chains import llm
from mysite.chains.ai_search import extract_filters
from mysite.database.models import Course

PAYMENT = 'Здравствуйте! Приносим извинения за неудобства. По нашим данным: Оплата прошла 3 дня назад. Мы передали обращение менеджеру, он проверит оплату и свяжется с вами в ближайшее время.'
GENERAL = 'Здравствуйте! Спасибо за обращение. Мы передали обращение менеджеру, он свяжется с вами в ближайшее время.'

@pytest.mark.parametrize('body,expected', [
    ({'text':'Верните деньги','facts':'Оплата прошла 3 дня назад'}, PAYMENT),
    ({'text':'Верните деньги','facts':'Оплата прошла 3 дня назад...!'}, PAYMENT),
    ({'text':'Когда начнётся набор?'}, GENERAL),
    ({'text':'Возврат'}, 'Здравствуйте! Приносим извинения за неудобства. Мы передали обращение менеджеру, он проверит оплату и свяжется с вами в ближайшее время.'),
    ({'text':'Вопрос','facts':'Получена заявка.'}, 'Здравствуйте! Спасибо за обращение. По нашим данным: Получена заявка. Мы передали обращение менеджеру, он свяжется с вами в ближайшее время.'),
])
def test_answer_exact(context, body, expected):
    client, *_ = context
    response = client.post('/ai/answer/',json=body)
    assert response.status_code == 200
    assert response.json() == {'text_draft':expected,'review':True}

@pytest.mark.parametrize('text,priority,course', [
    ('Не могу зайти в личный кабинет, пишет неверный пароль',1,None),
    ('Списали деньги дважды',1,None),
    ('Когда начнётся набор на Python Data Science?',2,'Python Data Science'),
    ('Спасибо, всё хорошо',3,None),
    ('На сайте ошибка',1,None),
])
def test_analyze(context, text, priority, course):
    client, *_ = context
    response = client.post('/ai/analyze/',json={'text':text})
    assert response.status_code == 200
    result = response.json()
    assert result['priority'] == priority and result['course_name'] == course
    assert 'менеджер' in result['answer']
    assert not any(char.isascii() and char.isalpha() for char in result['answer'])
    if 'пароль' in text:
        assert result['answer'] == 'Здравствуйте! Сожалеем о проблеме со входом или паролем. Мы передали обращение менеджеру, он поможет разобраться и свяжется с вами.'

def test_search_screenshot(context):
    client, *_ = context
    response = client.post('/ai/search/',json={'question':'Python среднего уровня'})
    assert response.status_code == 200
    result = response.json()
    assert result['answer'] == 'Найдено курсов: 1'
    assert result['filters'] == dict(keyword='Python', category_id=None, level='intermediate', min_price=None, max_price=None, status=None)
    assert len(result['courses']) == 1
    course = result['courses'][0]
    assert course.pop('created_at') and course.pop('updated_at')
    assert course == dict(id=2,title='Python Data Science',category_id=2,description='Pandas, NumPy and machine learning basics',level='intermediate',price=7500.0,duration_weeks=16,is_active=True,status='free')

@pytest.mark.parametrize('question,field,value', [
    ('курсы до 5к сом','max_price',5000), ('не дороже 5 000 сом','max_price',5000),
    ('дешевле 5000','max_price',5000), ('от 5к','min_price',5000),
    ('дороже 7 500 сом','min_price',7500), ('с нуля','level','beginner'),
    ('продвинутый','level','advanced'), ('бесплатный','status','free'), ('премиум','status','plus'),
])
def test_filters(question, field, value):
    filters = extract_filters(question, [])
    assert filters[field] == value
    assert filters['keyword'] is None

def test_category_casefold_and_active(context):
    client, factory, _, _ = context
    assert client.post('/ai/search/',json={'question':'курсы data science'}).json()['filters']['category_id'] == 2
    with factory() as db:
        course = db.get(Course,1)
        course.title = 'ПИТОН'
        course.description = 'КИРИЛЛИЦА'
        db.get(Course,2).is_active = False
        db.commit()
    assert client.post('/ai/search/',json={'question':'питон кириллица'}).json()['courses'][0]['id'] == 1
    assert client.post('/ai/search/',json={'question':'Python среднего уровня'}).json()['answer'] == 'Курсы не найдены'

@pytest.mark.parametrize('path,field,limit', [('/ai/search/','question',500),('/ai/answer/','text',5000),('/ai/analyze/','text',5000)])
@pytest.mark.parametrize('kind', ['empty','whitespace','long'])
def test_ai_validation(context, path, field, limit, kind):
    client, *_ = context
    value = '' if kind == 'empty' else ('   ' if kind == 'whitespace' else 'a'*(limit+1))
    assert client.post(path,json={field:value}).status_code == 422

@pytest.mark.parametrize('mode', ['missing_key','error','timeout','unsafe','invalid_json','valid'])
def test_llm_fallback(monkeypatch, mode):
    import json
    import sys
    import types
    from pydantic import SecretStr
    monkeypatch.setattr(settings,'AI_MODE','llm')
    monkeypatch.setattr(settings,'LLM_API_KEY',None if mode == 'missing_key' else SecretStr('test-key'))
    baseline = {'text_draft': GENERAL, 'review':True}
    called = []
    class FakeModel:
        async def ainvoke(self, messages):
            called.append(True)
            if mode == 'error':
                raise RuntimeError('provider unavailable')
            if mode == 'timeout':
                raise asyncio.TimeoutError
            content = 'invalid' if mode == 'invalid_json' else json.dumps({'text_draft':'Invented fact','review':False} if mode == 'unsafe' else baseline)
            return types.SimpleNamespace(content=content)
    def init_model(*args, **kwargs):
        assert kwargs['timeout'] <= 20 and kwargs['max_retries'] == 0
        return FakeModel()
    package = types.ModuleType('langchain')
    module = types.ModuleType('langchain.chat_models')
    module.init_chat_model = init_model
    monkeypatch.setitem(sys.modules,'langchain',package)
    monkeypatch.setitem(sys.modules,'langchain.chat_models',module)
    assert llm.with_optional_llm('answer',{},baseline) == baseline
    assert bool(called) == (mode != 'missing_key')

def test_llm_deadline(monkeypatch):
    from pydantic import SecretStr
    monkeypatch.setattr(settings,'AI_MODE','llm')
    monkeypatch.setattr(settings,'LLM_API_KEY',SecretStr('test-key'))
    async def deadline(coroutine, timeout):
        coroutine.close()
        assert timeout == 20
        raise asyncio.TimeoutError
    monkeypatch.setattr(asyncio,'wait_for',deadline)
    assert llm.with_optional_llm('answer',{}, {'review':True}) == {'review':True}

def test_seed_idempotent(context):
    import seed
    from sqlalchemy import select, func
    from mysite.database.models import User, StudyGroup, Category
    _, factory, _, _ = context
    with factory() as db:
        counts = [db.scalar(select(func.count()).select_from(model)) for model in (User,Course,StudyGroup,Category)]
        seed.seed(db)
        assert counts == [db.scalar(select(func.count()).select_from(model)) for model in (User,Course,StudyGroup,Category)]
