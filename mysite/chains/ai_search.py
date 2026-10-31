import re
from sqlalchemy import select
from mysite.base_knowledge import LEVEL_WORDS, STATUS_WORDS, STOP_WORDS
from mysite.database.models import Category, Course
from mysite.database.schema import CourseOutSchema

NUMBER = r'(\d+(?:[ \u00a0]\d{3})*(?:[.,]\d+)?\s*[кk]?)'
PRICE = re.compile(r'(?<!\w)(не\s+дороже|дешевле|до|дороже|от)\s*' + NUMBER + r'\s*(?:сом(?:ов)?|руб(?:лей)?)?', re.I)

def extract_filters(question, categories):
    remaining = question
    filters = dict(keyword=None, category_id=None, level=None, min_price=None, max_price=None, status=None)
    for field, choices in [('level', LEVEL_WORDS), ('status', STATUS_WORDS)]:
        for value, words in choices.items():
            pattern = r'(?<!\w)(?:' + '|'.join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r')(?!\w)'
            if re.search(pattern, remaining, re.I):
                if filters[field] is None:
                    filters[field] = value
                remaining = re.sub(pattern, ' ', remaining, flags=re.I)
    def price(match):
        amount = match[2].casefold().replace(' ', '').replace('\u00a0', '').replace(',', '.')
        multiplier = 1000 if amount.endswith(('к', 'k')) else 1
        value = float(amount.rstrip('кk')) * multiplier
        operator = ' '.join(match[1].casefold().split())
        filters['max_price' if operator in ('до', 'дешевле', 'не дороже') else 'min_price'] = value
        return ' '
    remaining = PRICE.sub(price, remaining)
    for category in sorted(categories, key=lambda c: len(c.category_name), reverse=True):
        pattern = r'(?<!\w)' + re.escape(category.category_name) + r'(?!\w)'
        if re.search(pattern, remaining, re.I):
            filters['category_id'] = category.id
            remaining = re.sub(pattern, ' ', remaining, flags=re.I)
            break
    words = re.findall(r'[\w#+]+', remaining, re.UNICODE)
    filters['keyword'] = ' '.join(word for word in words if word.casefold() not in STOP_WORDS) or None
    return filters

def search(db, question):
    filters = extract_filters(question, db.scalars(select(Category)).all())
    query = select(Course).where(Course.is_active.is_(True)).order_by(Course.id)
    for name in ('category_id', 'status'):
        if filters[name] is not None:
            query = query.where(getattr(Course, name) == filters[name])
    if filters['min_price'] is not None:
        query = query.where(Course.price >= filters['min_price'])
    if filters['max_price'] is not None:
        query = query.where(Course.price <= filters['max_price'])
    courses = []
    for course in db.scalars(query):
        if filters['level'] and filters['level'] not in course.level:
            continue
        haystack = f'{course.title} {course.description}'.casefold()
        if filters['keyword'] and not all(word.casefold() in haystack for word in filters['keyword'].split()):
            continue
        data = CourseOutSchema.model_validate(course).model_dump(mode='json')
        data['level'] = filters['level'] or (course.level[0] if course.level else '')
        courses.append(data)
    return {'answer': f'Найдено курсов: {len(courses)}' if courses else 'Курсы не найдены', 'filters': filters, 'courses': courses}
