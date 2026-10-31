from sqladmin import ModelView
from wtforms import PasswordField
from mysite.database.models import User, Category, Course, StudyGroup, Application, Enrollment
from mysite.api.security import hash_password

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.full_name, User.email, User.role, User.is_active]
    column_details_exclude_list = [User.password]
    column_export_exclude_list = [User.password]
    form_columns = [User.full_name, User.email, User.password, User.role, User.user_status, User.is_active]
    form_overrides = {'password': PasswordField}

    async def on_model_change(self, data, model, is_created, request):
        password = data.get('password')
        if password:
            if len(password) < 8 or len(password.encode('utf-8')) > 72:
                raise ValueError('Сырсөз 8 белгиден кем эмес жана 72 байттан ашпасын')
            data['password'] = hash_password(password)
        elif is_created:
            raise ValueError('Сырсөз керек')
        else:
            data.pop('password', None)

class CategoryAdmin(ModelView, model=Category):
    column_list = [Category.id, Category.category_name]

class CourseAdmin(ModelView, model=Course):
    column_list = [Course.id, Course.title, Course.level]

class StudyGroupAdmin(ModelView, model=StudyGroup):
    column_list = [StudyGroup.id, StudyGroup.name, StudyGroup.status, StudyGroup.capacity]

class ApplicationAdmin(ModelView, model=Application):
    column_list = [Application.id, Application.student_id, Application.status]

class EnrollmentAdmin(ModelView, model=Enrollment):
    column_list = [Enrollment.id, Enrollment.student_id, Enrollment.status]
