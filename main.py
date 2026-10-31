from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from mysite.database.db import Base, engine
from mysite.api.auth import auth_router
from mysite.api.user import user_router
from mysite.api.category import category_router
from mysite.api.course import course_router
from mysite.api.stady_group import group_router
from mysite.api.application import application_router
from mysite.api.enrollment import enrollment_router
from mysite.api.ai import ai_router
from mysite.admin.setup import setup_admin
import uvicorn

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield

app = FastAPI(title='Course Project', lifespan=lifespan)

@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(status_code=422, content={'detail': 'Маалымат туура эмес', 'fields': [list(error['loc']) for error in exc.errors()]})

for router in (auth_router, user_router, category_router, course_router, group_router, application_router, enrollment_router, ai_router):
    app.include_router(router)
admin = setup_admin(app)

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8001)
