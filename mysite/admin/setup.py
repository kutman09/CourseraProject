from fastapi import FastAPI
from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select
from mysite.config import settings
from mysite.database.db import engine, SessionLocal
from mysite.database.models import User
from mysite.api.security import verify_password
from .views import UserAdmin, CategoryAdmin, CourseAdmin, StudyGroupAdmin, ApplicationAdmin, EnrollmentAdmin

def admin_login(email, password):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email.casefold()))
        return user.id if user and user.role == 'admin' and verify_password(password, user.password) else None

def is_admin(user_id):
    if not isinstance(user_id, int):
        return False
    with SessionLocal() as db:
        user = db.get(User, user_id)
        return bool(user and user.role == 'admin')

class AdminAuthentication(AuthenticationBackend):
    async def login(self, request):
        form = await request.form()
        user_id = await run_in_threadpool(admin_login, str(form.get('username', '')), str(form.get('password', '')))
        if user_id is None:
            return False
        request.session.clear()
        request.session['admin_id'] = user_id
        return True

    async def logout(self, request):
        request.session.clear()
        return True

    async def authenticate(self, request):
        return await run_in_threadpool(is_admin, request.session.get('admin_id'))

def setup_admin(store_app: FastAPI):
    admin = Admin(store_app, engine, authentication_backend=AdminAuthentication(secret_key=settings.SECRET_KEY.get_secret_value()))
    for view in (UserAdmin, CategoryAdmin, CourseAdmin, StudyGroupAdmin, ApplicationAdmin, EnrollmentAdmin):
        admin.add_view(view)
    return admin
