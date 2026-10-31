"""Execute real curl requests against python main.py. Never write JWTs to logs."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8001'
CURL = shutil.which('curl.exe') or shutil.which('curl')
records = []
sys.stdout.reconfigure(encoding='utf-8')

def request(method, path, body=None, token=None, form=False, expected=200, label=None):
    command = [CURL, '--silent', '--show-error', '--max-time', '25', '-X', method, BASE+path, '-w', '\n%{http_code}']
    if token:
        command += ['-H', f'Authorization: Bearer {token}']
    data = None
    if body is not None:
        if form:
            from urllib.parse import urlencode
            data = urlencode(body).encode('utf-8')
            content_type = 'application/x-www-form-urlencoded'
        else:
            data = json.dumps(body,ensure_ascii=False).encode('utf-8')
            content_type = 'application/json'
        command += ['-H', 'Content-Type: '+content_type, '--data-binary', '@-']
    result = subprocess.run(command, input=data, capture_output=True, check=True)
    content, status = result.stdout.decode('utf-8').rsplit('\n',1)
    status = int(status)
    try:
        output = json.loads(content)
    except ValueError:
        output = {'html':True}
    sanitized = {**output, 'access_token':'<hidden>'} if isinstance(output,dict) and 'access_token' in output else output
    records.append({'request':label or f'{method} {path}', 'status':status, 'response':sanitized})
    assert status == expected, (path,status,sanitized)
    return output

email = f'live_{uuid4().hex[:10]}@test.kg'
registered = request('POST','/auth/register/',dict(full_name='Live verification',email=email,password='Test12345!'),expected=201)
student = request('POST','/auth/login/',dict(email=email,password='Test12345!'))['access_token']
manager = request('POST','/auth/login/',dict(email='manager@test.kg',password='Test12345!'))['access_token']
request('GET','/users/me/',token=student)
application = request('POST','/application/',dict(course_id=2,comment='Живая проверка'),token=student,expected=201)
request('PUT',f"/application/{application['id']}/",dict(status='accepted',comment='Кабыл алынды'),token=manager)
enrollment = request('POST','/enrollment/',dict(group_id=1),token=student,expected=201)
request('GET',f"/enrollment/{enrollment['id']}/",token=student)
request('GET','/application/',token=student,expected=403)
request('GET','/users/me/',expected=401)
search = request('POST','/ai/search/',{'question':'Python среднего уровня'})
assert search['answer'] == 'Найдено курсов: 1' and search['courses'][0]['id'] == 2
payment = request('POST','/ai/answer/',{'text':'Верните деньги','facts':'Оплата прошла 3 дня назад'})
assert payment == {'text_draft':'Здравствуйте! Приносим извинения за неудобства. По нашим данным: Оплата прошла 3 дня назад. Мы передали обращение менеджеру, он проверит оплату и свяжется с вами в ближайшее время.','review':True}
general = request('POST','/ai/answer/',{'text':'Когда начнётся набор?'})
assert general == {'text_draft':'Здравствуйте! Спасибо за обращение. Мы передали обращение менеджеру, он свяжется с вами в ближайшее время.','review':True}
request('POST','/ai/analyze/',{'text':'Не могу зайти в личный кабинет, пишет неверный пароль'})
request('GET','/docs')
request('POST','/auth/token/',dict(username='student@test.kg',password='Test12345!'),form=True)
with httpx.Client(base_url=BASE,follow_redirects=True) as client:
    response = client.get('/admin')
    assert response.status_code == 200 and '/admin/login' in str(response.url)
    records.append({'request':'GET /admin (redirects followed)','status':response.status_code,'final_url':str(response.url)})
    response = client.post('/admin/login',data={'username':'student@test.kg','password':'Test12345!'})
    assert 'Invalid credentials' in response.text
    records.append({'request':'Admin login as student','rejected':True})
    response = client.post('/admin/login',data={'username':'admin@test.kg','password':'Test12345!'})
    assert response.status_code == 200 and '/admin/login' not in str(response.url)
    records.append({'request':'Admin login as admin','status':response.status_code,'final_url':str(response.url)})
    response = client.get('/admin/user/list')
    assert response.status_code == 200 and '$2b$' not in response.text
    records.append({'request':'GET /admin/user/list','status':response.status_code,'password_hashes_visible':False})
# Free the test seat for repeatable verification without modifying real users.
request('DELETE',f"/enrollment/{enrollment['id']}/",token=student)
(ROOT/'verification'/'live_responses.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(records,ensure_ascii=False,indent=2))
