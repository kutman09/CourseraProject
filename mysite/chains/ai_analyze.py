from sqlalchemy import select
from mysite.database.models import Course
from mysite.base_knowledge import PAYMENT_WORDS, LOGIN_WORDS, ERROR_WORDS, MEDIUM_WORDS

def analyze(db, text):
    folded = text.casefold()
    payment = any(word in folded for word in PAYMENT_WORDS)
    login = any(word in folded for word in LOGIN_WORDS)
    error = any(word in folded for word in ERROR_WORDS)
    priority = 1 if payment or login or error else (2 if any(word in folded for word in MEDIUM_WORDS) else 3)
    courses = db.scalars(select(Course).order_by(Course.id)).all()
    course_name = next((c.title for c in sorted(courses, key=lambda c: len(c.title), reverse=True) if c.title.casefold() in folded), None)
    if login:
        response = 'Здравствуйте! Сожалеем о проблеме со входом или паролем. Мы передали обращение менеджеру, он поможет разобраться и свяжется с вами.'
    elif payment:
        response = 'Здравствуйте! Сожалеем о проблеме с оплатой. Мы передали обращение менеджеру, он проверит информацию и свяжется с вами.'
    elif error:
        response = 'Здравствуйте! Сожалеем о проблеме с работой сайта. Мы передали обращение менеджеру, он поможет разобраться и свяжется с вами.'
    else:
        response = 'Здравствуйте! Спасибо за обращение. Мы передали обращение менеджеру, он свяжется с вами в ближайшее время.'
    return {'priority': priority, 'course_name': course_name, 'answer': response}
