from django.contrib import admin

from .models import Option, Question, Quiz, QuizAttempt, Student, TeacherProfile


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "teacher", "level_group", "subject", "is_published", "created_at")
    list_filter = ("level_group", "is_published")
    search_fields = ("title", "subject")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "quiz", "order")
    inlines = [OptionInline]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("name", "teacher", "grade", "gender", "color_name", "points", "badges")
    list_filter = ("grade", "gender")
    search_fields = ("name",)


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("student", "quiz", "score", "played_at")
    list_filter = ("quiz",)


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "class_name")
