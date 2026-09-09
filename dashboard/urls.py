from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/upload/", views.upload_quiz, name="upload_quiz"),

    path("classes/", views.classes_view, name="classes"),
    path("classes/<int:pk>/", views.class_detail, name="class_detail"),
    path("classes/<int:pk>/remove/", views.remove_class, name="remove_class"),
    path("classes/<int:class_id>/students/<int:pk>/remove/", views.remove_student_from_class, name="remove_student_from_class"),
    path("classes/<int:class_id>/start-session/", views.start_class_session, name="start_class_session"),

    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("quizzes/", views.scoreboard, name="scoreboard"),
    path("quizzes/<int:pk>/edit/", views.edit_questions, name="edit_questions"),
        path("dashboard/quizzes/<int:pk>/discard/", views.discard_quiz, name="discard_quiz"),
    path("quizzes/<int:pk>/publish/", views.publish_quiz, name="publish_quiz"),
    path("quizzes/<int:pk>/questions/add/", views.add_question, name="add_question"),
    path("quizzes/<int:pk>/questions/<int:question_id>/delete/", views.delete_question, name="delete_question"),

    path("student-scores/", views.student_scores, name="student_scores"),
    path("performance/", views.performance, name="performance"),

    path("api/session/<str:code>/questions/", views.api_session_questions, name="api_session_questions"),
    path("api/session/<str:code>/roster/", views.api_session_roster, name="api_session_roster"),
    path("api/session/<str:code>/answer/", views.api_submit_answer, name="api_submit_answer"),
    path("api/session/<str:code>/finish/", views.api_submit_finish, name="api_submit_finish"),

    path("session/start/", views.start_session, name="start_session"),
]
