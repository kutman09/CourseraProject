import pytest

ROLES = ('anonymous', 'student', 'teacher', 'manager', 'admin')
COURSE = dict(title='New course', category_id=1, description='test', level=['beginner'], price=0, duration_weeks=4)
GROUP = dict(name='New group', course_id=1, teacher_id=2, starts_on='2027-01-01', ends_on='2027-02-01', capacity=2)
CASES = []
for resource, payload, allowed in [('category', {'category_name': 'New'}, {'admin'}),
                                   ('course', COURSE, {'teacher', 'admin'}),
                                   ('group', GROUP, {'teacher', 'admin'})]:
    for suffix in ('', '1/'):
        CASES.append(('GET', f'/{resource}/{suffix}', None, set(ROLES), 200))
    CASES.extend([('POST', f'/{resource}/', payload, allowed, 201),
                  ('PUT', f'/{resource}/1/', payload, allowed, 200),
                  ('DELETE', f'/{resource}/1/', None, allowed, 200)])
CASES += [
    ('POST', '/application/', {'course_id': 2}, {'student', 'admin'}, 201),
    ('GET', '/application/', None, {'manager', 'admin'}, 200),
    ('GET', '/application/1/', None, {'manager', 'admin'}, 200),
    ('PUT', '/application/1/', {'status': 'in_progress', 'comment': 'ok'}, {'manager', 'admin'}, 200),
    ('DELETE', '/application/1/', None, {'manager', 'admin'}, 200),
    ('POST', '/enrollment/', {'group_id': 1}, {'student', 'admin'}, 201),
    ('GET', '/enrollment/', None, set(ROLES) - {'anonymous'}, 200),
    ('GET', '/enrollment/1/', None, set(ROLES) - {'anonymous'}, 200),
    ('PUT', '/enrollment/1/', {'status': 'cancelled'}, set(ROLES) - {'anonymous'}, 200),
    ('DELETE', '/enrollment/1/', None, set(ROLES) - {'anonymous'}, 200),
    ('GET', '/users/me/', None, set(ROLES) - {'anonymous'}, 200),
    ('PUT', '/users/me/', {'full_name': 'Changed'}, set(ROLES) - {'anonymous'}, 200),
    ('GET', '/users/', None, {'admin'}, 200),
    ('GET', '/users/1/', None, {'admin'}, 200),
    ('PUT', '/users/4/', {'is_active': False}, {'admin'}, 200),
    ('POST', '/ai/search/', {'question': 'Python среднего уровня'}, set(ROLES), 200),
    ('POST', '/ai/answer/', {'text': 'Спасибо'}, set(ROLES), 200),
    ('POST', '/ai/analyze/', {'text': 'Спасибо'}, set(ROLES), 200),
    ('POST', '/auth/register/', {'full_name': 'New', 'email': 'new@test.kg', 'password': 'Test12345!'}, set(ROLES), 201),
    ('POST', '/auth/login/', {'email': 'student@test.kg', 'password': 'Test12345!'}, set(ROLES), 200),
    ('POST', '/auth/token/', {'username': 'student@test.kg', 'password': 'Test12345!'}, set(ROLES), 200),
]

@pytest.mark.parametrize('role', ROLES)
@pytest.mark.parametrize('method,path,payload,allowed,success', CASES, ids=[f'{m} {p}' for m,p,*_ in CASES])
def test_role_matrix(context, role, method, path, payload, allowed, success):
    client, factory, headers, users = context
    if path == '/enrollment/' and method == 'POST':
        from mysite.database.models import Enrollment
        with factory() as db:
            db.delete(db.get(Enrollment, 1))
            db.commit()
    expected = success if role in allowed else (401 if role == 'anonymous' else 403)
    kwargs = {'data' if path == '/auth/token/' else 'json': payload} if payload is not None else {}
    response = client.request(method, path, headers=headers[role], **kwargs)
    assert response.status_code == expected, response.text

@pytest.mark.parametrize('path,method,payload', [('/category/999/', 'GET', None), ('/course/999/', 'PUT', COURSE),
    ('/group/999/', 'DELETE', None), ('/application/999/', 'GET', None), ('/enrollment/999/', 'GET', None), ('/users/999/', 'GET', None)])
def test_missing(context, path, method, payload):
    client, _, headers, _ = context
    response = client.request(method, path, headers=headers['admin'], **({'json': payload} if payload else {}))
    assert response.status_code == 404

@pytest.mark.parametrize('token', ['garbage', '', 'eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIn0.'])
def test_bad_token(context, token):
    client, *_ = context
    assert client.get('/users/me/', headers={'Authorization': f'Bearer {token}'}).status_code == 401
