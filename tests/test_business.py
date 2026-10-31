from types import SimpleNamespace
import pytest
from sqlalchemy import select
from mysite.api.application import can_student_apply
from mysite.database.models import Application, Course, Enrollment, StudyGroup, User
from mysite.api.security import verify_password

@pytest.mark.parametrize('active,status,expected', [(True,'free',True),(True,'plus',True),(False,'free',True),(False,'plus',False)])
def test_can_student_apply(active, status, expected):
    assert can_student_apply(SimpleNamespace(is_active=active), SimpleNamespace(status=status)) is expected

@pytest.mark.parametrize('role,ids', [('student',[1]), ('student_inactive',[2]), ('teacher',[1]), ('other_teacher',[2]), ('manager',[1,2]), ('admin',[1,2])])
def test_queryset(context, role, ids):
    client, _, headers, _ = context
    response = client.get('/enrollment/', headers=headers[role])
    assert [e['id'] for e in response.json()] == ids
    for pk in (1,2):
        assert client.get(f'/enrollment/{pk}/', headers=headers[role]).status_code == (200 if pk in ids else 404)

@pytest.mark.parametrize('method,payload', [('GET',None), ('PUT',{'status':'cancelled'}), ('DELETE',None)])
def test_foreign_enrollment_hidden(context, method, payload):
    client, _, headers, _ = context
    for role in ('student', 'teacher'):
        kwargs = {'json':payload} if payload else {}
        assert client.request(method, '/enrollment/2/', headers=headers[role], **kwargs).status_code == 404

@pytest.mark.parametrize('scenario,expected', [('success',201),('duplicate',400),('full',400),('completed',400),('missing',404)])
def test_admission(context, scenario, expected):
    client, factory, headers, users = context
    with factory() as db:
        if scenario != 'duplicate':
            db.delete(db.get(Enrollment,1))
        if scenario == 'full':
            db.get(StudyGroup,1).capacity = 1
            db.add(Enrollment(student_id=users['student_inactive'], group_id=1))
        db.commit()
    group_id = 2 if scenario == 'completed' else (999 if scenario == 'missing' else 1)
    assert client.post('/enrollment/', json={'group_id':group_id}, headers=headers['student']).status_code == expected

@pytest.mark.parametrize('course,expected', [(2,201),(3,403),(999,404)])
def test_inactive_application(context, course, expected):
    client, _, headers, users = context
    response = client.post('/application/', json={'course_id':course}, headers=headers['student_inactive'])
    assert response.status_code == expected
    if expected == 201:
        assert response.json()['student_id'] == users['student_inactive']

def test_application_validation(context):
    client, factory, headers, users = context
    assert client.post('/application/', json={'course_id':1}, headers=headers['student']).status_code == 400
    with factory() as db:
        db.get(Application,1).status = 'in_progress'
        db.get(Course,2).is_active = False
        db.commit()
    assert client.post('/application/', json={'course_id':1}, headers=headers['student']).status_code == 400
    assert client.post('/application/', json={'course_id':2}, headers=headers['student']).status_code == 400
    assert client.post('/application/', json={'course_id':2, 'student_id':1}, headers=headers['student']).status_code == 422
    response = client.put('/application/1/', json={'status':'accepted','comment':'ok'}, headers=headers['manager'])
    assert response.json()['manager_id'] == users['manager']
    assert client.put('/application/1/', json={'status':'new','student_id':1}, headers=headers['manager']).status_code == 422

def test_teacher_ownership(context):
    client, _, headers, users = context
    body = dict(name='Group', course_id=1, teacher_id=users['other_teacher'], starts_on='2027-01-01', ends_on='2027-02-01')
    response = client.post('/group/', json=body, headers=headers['teacher'])
    assert response.status_code == 201
    assert response.json()['teacher_id'] == users['teacher']
    assert client.put('/group/2/',json=body,headers=headers['teacher']).status_code == 403
    assert client.delete('/group/2/',headers=headers['teacher']).status_code == 403
    body['teacher_id'] = users['student']
    assert client.post('/group/',json=body,headers=headers['admin']).status_code == 400
    body['teacher_id'] = 999
    assert client.post('/group/',json=body,headers=headers['admin']).status_code == 404
    body['teacher_id'] = users['teacher']; body['course_id'] = 999
    assert client.post('/group/',json=body,headers=headers['teacher']).status_code == 404
    body['course_id'] = 1; body['capacity'] = 0
    assert client.post('/group/',json=body,headers=headers['teacher']).status_code == 422
    body['capacity'] = 2; body['ends_on'] = body['starts_on']
    assert client.post('/group/',json=body,headers=headers['teacher']).status_code == 422

def test_course_validation(context):
    client, _, headers, _ = context
    body = dict(title='Test',category_id=999,description='Test',level=['beginner'],price=0,duration_weeks=1)
    assert client.post('/course/',json=body,headers=headers['teacher']).status_code == 404
    body['category_id'] = 1; body['price'] = -1
    assert client.post('/course/',json=body,headers=headers['teacher']).status_code == 422
    body['price'] = 0; body['duration_weeks'] = 0
    assert client.post('/course/',json=body,headers=headers['teacher']).status_code == 422

def test_student_cancel_only_and_reactivation(context):
    client, factory, headers, _ = context
    assert client.put('/enrollment/1/',json={'status':'completed'},headers=headers['student']).status_code == 403
    assert client.put('/enrollment/1/',json={'status':'cancelled'},headers=headers['student']).status_code == 200
    with factory() as db:
        db.get(StudyGroup,1).status = 'completed'
        db.commit()
    assert client.put('/enrollment/1/',json={'status':'active'},headers=headers['manager']).status_code == 400

def test_auth_and_profile(context):
    client, factory, headers, users = context
    body = dict(full_name='New',email='new@test.kg',password='Test12345!')
    assert client.post('/auth/register/',json={**body,'role':'admin'}).status_code == 422
    response = client.post('/auth/register/',json=body)
    assert response.status_code == 201
    assert response.json()['role'] == 'student' and 'password' not in response.json()
    assert client.post('/auth/register/',json=body).status_code == 409
    assert client.post('/auth/login/',json={'email':'new@test.kg','password':'wrong'}).status_code == 401
    assert client.post('/auth/token/',data={'username':'new@test.kg','password':'wrong'}).status_code == 401
    assert client.post('/auth/login/',json={'email':'student_inactive@test.kg','password':'Test12345!'}).status_code == 200
    response = client.put('/users/me/',json={'password':'NewPass123!','full_name':'Updated'},headers=headers['student'])
    assert response.status_code == 200 and 'password' not in response.json()
    assert client.put('/users/me/',json={'role':'admin'},headers=headers['student']).status_code == 422
    assert client.post('/auth/login/',json={'email':'student@test.kg','password':'NewPass123!'}).status_code == 200
    with factory() as db:
        assert verify_password('NewPass123!', db.get(User, users['student']).password)
    assert client.post('/auth/register/',json={**body,'email':'long@test.kg','password':'я'*40}).status_code == 422

def test_docs_swagger_and_admin_auth(context):
    client, _, _, _ = context
    assert client.get('/docs').status_code == 200
    spec = client.get('/openapi.json').json()
    assert spec['components']['securitySchemes']['OAuth2PasswordBearer']['flows']['password']['tokenUrl'] == '/auth/token/'
    assert client.get('/admin').status_code == 200
    for role in ('student','teacher','manager'):
        response = client.post('/admin/login',data={'username':f'{role}@test.kg','password':'Test12345!'})
        assert 'Invalid credentials' in response.text
    response = client.post('/admin/login',data={'username':'admin@test.kg','password':'Test12345!'})
    assert response.status_code == 200 and '/admin/login' not in str(response.url)
    assert client.get('/admin/').status_code == 200


def test_admin_hash_hook(context):
    import asyncio
    from mysite.admin.views import UserAdmin
    from mysite.api.security import verify_password
    _, factory, _, _ = context
    with factory() as db:
        model = db.get(User,1)
        view = UserAdmin()
        data = {'password':'NewAdmin123!'}
        asyncio.run(view.on_model_change(data,model,True,None))
        assert verify_password('NewAdmin123!',data['password'])
        empty = {'password':''}
        asyncio.run(view.on_model_change(empty,model,False,None))
        assert 'password' not in empty
        for value in ('', 'short', 'я'*40):
            with pytest.raises(ValueError):
                asyncio.run(view.on_model_change({'password':value},model,True,None))

@pytest.mark.parametrize('kind', ['expired','missing_exp','unknown_user'])
def test_jwt_rejected(context, kind):
    from datetime import datetime, timedelta, timezone
    import jwt
    from mysite.config import settings
    client, *_ = context
    payload = {'sub':'99999' if kind == 'unknown_user' else '1'}
    if kind != 'missing_exp':
        payload['exp'] = datetime.now(timezone.utc) + timedelta(minutes=-1 if kind == 'expired' else 1)
    token = jwt.encode(payload,settings.SECRET_KEY.get_secret_value(),algorithm=settings.ALGORITHM)
    response = client.get('/users/me/',headers={'Authorization':f'Bearer {token}'})
    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'


def test_multipart_token(context):
    client, *_ = context
    response = client.post('/auth/token/',files={'username':(None,'student@test.kg'),'password':(None,'Test12345!')})
    assert response.status_code == 200
    assert response.json()['token_type'] == 'bearer'


def test_capacity_database_constraint(context):
    from sqlalchemy.exc import IntegrityError
    _, factory, _, _ = context
    with factory() as db:
        db.get(StudyGroup,1).capacity = 0
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
