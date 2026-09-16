import json
import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives, send_mail
from django.db import IntegrityError
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .ai_quiz import generate_questions_with_ai
from .forms import ClassForm, QuizUploadForm, SignUpForm, StudentForm
from .models import (
    COLOR_PALETTE,
    GRADE_LEVELS,
    LEVEL_GROUPS,
    GameSession,
    Option,
    Question,
    Quiz,
    QuizAttempt,
    SchoolClass,
    Student,
    TeacherProfile,
)

# Sample data shown on the logged-out marketing homepage only.
HOME_WEEKLY_LEADERS = [
    {"name": "John Cabornay", "pts": 30, "init": "JC", "color": "#E8493C"},
    {"name": "Jade Felicidario", "pts": 29, "init": "JF", "color": "#4DAEB0"},
    {"name": "Rose Rama", "pts": 28, "init": "RR", "color": "#E8887A"},
]

def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard:dashboard")
    return render(request, "dashboard/home.html", {"weekly_leaders": HOME_WEEKLY_LEADERS})


def send_otp_email(recipient_email, code):
    spaced_code = " ".join(str(code).strip())
    subject = "Welcome to Gamio! 🎓"

    message = (
        f"Welcome to Gamio!\n\n"
        f"Your verification code is:\n\n"
        f"{spaced_code}\n\n"
        f"If you did not request this verification code, please ignore this email."
    )

    html_message = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:28px 18px;background-color:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#111827;">
  <div style="max-width:540px;margin:0 auto;">
    <h1 style="font-size:24px;font-weight:700;color:#111827;margin:0 0 18px 0;letter-spacing:-0.4px;">Welcome to Gamio! &#127891;</h1>
    <p style="font-size:15px;color:#4B5563;margin:0 0 24px 0;line-height:1.5;">Your verification code is:</p>
    <div style="font-size:42px;font-weight:800;color:#2563EB;letter-spacing:12px;margin:0 0 32px 0;font-family:'Nunito Sans',-apple-system,BlinkMacSystemFont,sans-serif;">
      {spaced_code}
    </div>
    <div style="font-size:12.5px;color:#9CA3AF;margin-top:40px;border-top:1px solid #E5E7EB;padding-top:16px;">
      Gamio Learning Platform &bull; If you did not request this verification code, you can safely ignore this email.
    </div>
  </div>
</body>
</html>"""

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Gamio <gamio.cecsystem@gmail.com>")
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[recipient_email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
        return True, None
    except UnicodeEncodeError:
        try:
            msg = EmailMultiAlternatives(
                subject="Welcome to Gamio!",
                body=message,
                from_email=from_email,
                to=[recipient_email]
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send(fail_silently=False)
            return True, None
        except Exception as exc:
            return False, str(exc)
    except Exception as exc:
        return False, str(exc)


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:dashboard")

    step = request.session.get("signup_step", 1)
    signup_data = request.session.get("signup_data", {})

    if request.method == "POST":
        action = request.POST.get("action")

        # --- STEP 2 ACTIONS ---
        if step == 2 and action == "verify_code":
            entered = "".join(request.POST.get(f"d{i}", "") for i in range(6)).strip()
            expected = str(request.session.get("signup_code", "")).strip()

            if entered and entered == expected:
                data = request.session.get("signup_data", {})
                username = data.get("username", "").strip()
                try:
                    user = User.objects.filter(username__iexact=username).first()
                    if not user:
                        user = User.objects.create_user(
                            username=username,
                            email=data.get("email", ""),
                            password=data.get("password", "")
                        )
                    else:
                        user.email = data.get("email", "")
                        user.set_password(data.get("password", ""))
                        user.save()
                except IntegrityError:
                    user = User.objects.filter(username__iexact=username).first()
                    if user:
                        user.email = data.get("email", "")
                        user.set_password(data.get("password", ""))
                        user.save()
                    else:
                        messages.error(request, "This username is already taken. Please choose another.")
                        request.session["signup_step"] = 1
                        return render(request, "dashboard/signup.html", {"form": SignUpForm(data), "step": 1})

                name_parts = data.get("full_name", "").strip().split(" ", 1)
                user.first_name = name_parts[0]
                user.last_name = name_parts[1] if len(name_parts) > 1 else ""
                user.save()

                profile, _ = TeacherProfile.objects.get_or_create(user=user)
                profile.class_name = data.get("class_name", "").strip()
                profile.save()

                # Clean up session
                for k in ("signup_step", "signup_code", "signup_data"):
                    request.session.pop(k, None)

                messages.success(request, f"Account created successfully for {user.first_name or user.username}! You can now sign in.")
                return redirect("dashboard:home")
            else:
                messages.error(request, "That 6-digit code doesn't match. Please try again.")
                return render(request, "dashboard/signup.html", {"step": 2, "email": signup_data.get("email")})

        elif step == 2 and action == "resend_code":
            code = f"{random.randint(0, 999999):06d}"
            request.session["signup_code"] = code
            email = signup_data.get("email")
            sent, err = send_otp_email(email, code)
            if sent:
                messages.success(request, f"New verification code sent to {email}!")
            else:
                messages.info(request, f"New verification code sent to {email}. (Dev note: code is {code})")
            return render(request, "dashboard/signup.html", {"step": 2, "email": email})

        elif step == 2 and action == "edit_info":
            request.session["signup_step"] = 1
            form = SignUpForm(initial=signup_data)
            return render(request, "dashboard/signup.html", {"form": form, "step": 1})

        # --- STEP 1 FORM SUBMIT ---
        else:
            form = SignUpForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                code = f"{random.randint(0, 999999):06d}"
                request.session["signup_data"] = {
                    "full_name": data["full_name"],
                    "class_name": data["class_name"],
                    "username": data["username"],
                    "email": data["email"],
                    "password": data["password"],
                }
                request.session["signup_code"] = code
                request.session["signup_step"] = 2

                sent, err = send_otp_email(data["email"], code)
                if sent:
                    messages.success(request, f"We sent a 6-digit code to {data['email']}. Please check your inbox!")
                else:
                    messages.info(request, f"We sent a 6-digit code to {data['email']}. (Dev note: code is {code})")

                return render(request, "dashboard/signup.html", {"step": 2, "email": data["email"]})
            else:
                return render(request, "dashboard/signup.html", {"form": form, "step": 1})

    # GET request
    if step == 2 and signup_data.get("email"):
        return render(request, "dashboard/signup.html", {"step": 2, "email": signup_data.get("email")})

    form = SignUpForm(initial=signup_data if signup_data else None)
    return render(request, "dashboard/signup.html", {"form": form, "step": 1})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:dashboard")

    error_message = None
    email_val = ""

    if request.method == "POST":
        ident = request.POST.get("email", "").strip() or request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        email_val = ident

        from django.contrib.auth import authenticate
        user = authenticate(request, username=ident, password=password)
        if user is not None:
            login(request, user, backend='dashboard.backends.CaseInsensitiveModelBackend')
            return redirect("dashboard:dashboard")
        else:
            error_message = "Invalid email or password. Please try again."

    return render(request, "dashboard/login.html", {
        "email_val": email_val,
        "error_message": error_message,
    })


def logout_view(request):
    logout(request)
    return redirect("dashboard:home")


def forgot_password(request):
    """A simplified 3-step reset flow, mirroring the original mock-up. Since
    this demo has no email backend wired up, step 2's code is shown on-screen
    via a message instead of actually being emailed."""
    step = request.session.get("forgot_step", 1)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "send_code" and step == 1:
            ident = request.POST.get("email", "").strip()
            if not ident:
                messages.error(request, "Enter your username or email.")
            else:
                user = (
                    User.objects.filter(email__iexact=ident).first()
                    or User.objects.filter(username__iexact=ident).first()
                )
                if not user:
                    for u in User.objects.all():
                        full = f"{u.first_name} {u.last_name}".strip()
                        if full.lower() == ident.lower():
                            user = u
                            break
                code = f"{random.randint(0, 999999):06d}"
                request.session["forgot_ident"] = ident
                if user:
                    request.session["forgot_user_id"] = user.id
                request.session["forgot_code"] = code
                request.session["forgot_step"] = 2
                messages.info(request, f"Demo mode: your reset code is {code} (normally emailed to you).")
                step = 2
        elif action == "verify_code" and step == 2:
            entered = "".join(request.POST.get(f"d{i}", "") for i in range(6))
            if entered == request.session.get("forgot_code"):
                request.session["forgot_step"] = 3
                step = 3
            else:
                messages.error(request, "That code doesn't match. Try again.")
        elif action == "resend_code" and step == 2:
            code = f"{random.randint(0, 999999):06d}"
            request.session["forgot_code"] = code
            messages.info(request, f"Demo mode: your new reset code is {code}.")
        elif action == "change_password" and step == 3:
            pw1 = request.POST.get("password1", "")
            pw2 = request.POST.get("password2", "")
            user_id = request.session.get("forgot_user_id")
            user = User.objects.filter(id=user_id).first() if user_id else None
            if not user:
                ident = request.session.get("forgot_ident", "")
                user = (
                    User.objects.filter(email__iexact=ident).first()
                    or User.objects.filter(username__iexact=ident).first()
                )
            if len(pw1) < 8:
                messages.error(request, "Password must be at least 8 characters.")
            elif pw1 != pw2:
                messages.error(request, "Passwords don't match.")
            else:
                if user:
                    user.set_password(pw1)
                    user.save()
                    messages.success(request, "Password reset successfully! Please sign in.")
                request.session["forgot_step"] = 4
                step = 4
        elif action == "restart":
            for key in ("forgot_step", "forgot_email", "forgot_ident", "forgot_user_id", "forgot_code"):
                request.session.pop(key, None)
            return redirect("dashboard:login")

    return render(request, "dashboard/forgot_password.html", {"step": step})


@login_required
def dashboard(request):
    students = Student.objects.filter(teacher=request.user)
    quiz_ids = Quiz.objects.filter(teacher=request.user).values_list("id", flat=True)
    avg_score = QuizAttempt.objects.filter(quiz_id__in=quiz_ids).aggregate(Avg("score"))["score__avg"]

    needs_attention = sum(1 for s in students if (s.average_score or 100) < 60)

    ready_quiz = None
    ready_quiz_id = request.session.get("ready_quiz_id")
    if ready_quiz_id:
        ready_quiz = Quiz.objects.filter(id=ready_quiz_id, teacher=request.user, is_published=False).first()
        if not ready_quiz:
            request.session.pop("ready_quiz_id", None)

    top_students = students.order_by("-points")[:5]
    great = [s for s in students if s.average_score is not None and s.average_score >= 60][:3]
    support = [s for s in students if s.average_score is not None and s.average_score < 60][:3]

    context = {
        "stat_total_students": students.count(),
        "stat_avg_score": round(avg_score) if avg_score is not None else "—",
        "stat_badges": sum(s.badges for s in students),
        "stat_needs_attention": needs_attention,
        "ready_quiz": ready_quiz,
        "upload_form": QuizUploadForm(),
        "top_students": top_students,
        "great_students": great,
        "support_students": support,
    }
    return render(request, "dashboard/dashboard.html", context)

@login_required
@require_POST
def upload_quiz(request):
    form = QuizUploadForm(request.POST, request.FILES)
    if form.is_valid():
        uploaded = form.cleaned_data["source_file"]
        level_group = form.cleaned_data["level_group"]
        title = uploaded.name.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").strip() or "New Quiz"

        quiz = Quiz.objects.create(
            teacher=request.user,
            title=title,
            subject="New",
            level_group=level_group,
            source_filename=uploaded.name,
            source_file=uploaded,
        )

        from .ai_quiz import extract_text_from_file
        lesson_text = extract_text_from_file(uploaded)
        generated_questions = generate_questions_with_ai(lesson_text, level_group)

        for i, q in enumerate(generated_questions):
            question = Question.objects.create(quiz=quiz, text=q["text"], order=i)
            for j, opt_text in enumerate(q["options"]):
                Option.objects.create(question=question, text=opt_text, is_correct=(j == q["correct"]), order=j)

        request.session["ready_quiz_id"] = quiz.id
        messages.success(request, "Quiz generated from your file!")
    else:
        messages.error(request, "Please choose a file to upload.")
    return redirect("dashboard:dashboard")

def _save_question_edits(request, quiz):
    for question in quiz.questions.all():
        text = request.POST.get(f"q_text_{question.id}")
        if text is not None:
            question.text = text
            question.save(update_fields=["text"])
        correct_id = request.POST.get(f"q_correct_{question.id}")
        for option in question.options.all():
            opt_text = request.POST.get(f"opt_text_{option.id}")
            if opt_text is not None:
                option.text = opt_text
            option.is_correct = str(option.id) == correct_id
            option.save()


def _publish(request, quiz):
    quiz.is_published = True
    quiz.save(update_fields=["is_published"])
    if request.session.get("ready_quiz_id") == quiz.id:
        request.session.pop("ready_quiz_id", None)
    accordion = request.session.get("quiz_accordion", {})
    accordion[quiz.level_group] = True
    request.session["quiz_accordion"] = accordion
    messages.success(request, f"Quiz added to {quiz.level_group} quizzes \U0001F3AE")


@login_required
def edit_questions(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, teacher=request.user)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save":
            _save_question_edits(request, quiz)
            messages.success(request, "Draft saved")
            return redirect("dashboard:edit_questions", pk=quiz.pk)
        elif action == "publish":
            _save_question_edits(request, quiz)
            _publish(request, quiz)
            return redirect("dashboard:scoreboard")

    return render(request, "dashboard/edit_questions.html", {"quiz": quiz})


@login_required
@require_POST
def add_question(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, teacher=request.user)
    order = quiz.questions.count()
    question = Question.objects.create(quiz=quiz, text="New question — type here", order=order)
    for j, label in enumerate(["Option A", "Option B", "Option C", "Option D"]):
        Option.objects.create(question=question, text=label, is_correct=(j == 0), order=j)
    return redirect("dashboard:edit_questions", pk=quiz.pk)


@login_required
@require_POST
def delete_question(request, pk, question_id):
    quiz = get_object_or_404(Quiz, pk=pk, teacher=request.user)
    get_object_or_404(Question, pk=question_id, quiz=quiz).delete()
    return redirect("dashboard:edit_questions", pk=quiz.pk)

@login_required
@require_POST
def discard_quiz(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, teacher=request.user, is_published=False)
    quiz.delete()  # cascades and deletes its Questions/Options too
    if request.session.get("ready_quiz_id") == quiz.id:
        request.session.pop("ready_quiz_id", None)
    messages.info(request, "Quiz discarded — upload a new file to try again.")
    return redirect("dashboard:dashboard")

@login_required
@require_POST
def publish_quiz(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk, teacher=request.user)
    _publish(request, quiz)
    return redirect("dashboard:scoreboard")

@login_required
def classes_view(request):
    classes = SchoolClass.objects.filter(teacher=request.user).annotate(student_count=Count("students"))

    if request.method == "POST":
        form = ClassForm(request.POST)
        if form.is_valid():
            school_class = form.save(commit=False)
            school_class.teacher = request.user
            try:
                school_class.save()
                messages.success(request, f"{school_class.display_name} created.")
                return redirect("dashboard:classes")
            except IntegrityError:
                messages.error(request, "You already have a class with that grade and section.")
        else:
            messages.error(request, "Please choose a grade and enter a section name.")
    else:
        form = ClassForm()

    return render(request, "dashboard/classes.html", {"classes": classes, "form": form})


@login_required
@require_POST
def remove_class(request, pk):
    school_class = get_object_or_404(SchoolClass, pk=pk, teacher=request.user)
    name = school_class.display_name
    school_class.delete()
    messages.success(request, f"{name} removed")
    return redirect("dashboard:classes")


@login_required
def class_detail(request, pk):
    school_class = get_object_or_404(SchoolClass, pk=pk, teacher=request.user)
    roster = school_class.students.all()
    used_colors = set(roster.values_list("color_name", flat=True))
    available_colors = [c for c in COLOR_PALETTE if c[0] not in used_colors]

    if request.method == "POST":
        form = StudentForm(request.POST)
        if not available_colors:
            messages.error(request, "All detector color slots for this class are full. Remove a student to add another.")
        elif form.is_valid():
            color_name, color_hex = available_colors[0]
            student = form.save(commit=False)
            student.teacher = request.user
            student.school_class = school_class
            student.grade = school_class.grade
            student.color_name = color_name
            student.color_hex = color_hex
            student.save()
            messages.success(request, f"{student.name}'s character is ready!")
            return redirect("dashboard:class_detail", pk=school_class.pk)
        else:
            messages.error(request, "Please fill in name and player type.")
    else:
        form = StudentForm()

    quizzes = Quiz.objects.filter(teacher=request.user, is_published=True)
    active_sessions = GameSession.objects.filter(
        teacher=request.user, is_active=True, students__school_class=school_class
    ).distinct().order_by("-created_at")

    return render(request, "dashboard/class_detail.html", {
        "school_class": school_class,
        "roster": roster,
        "form": form,
        "available_colors": available_colors,
        "color_palette": COLOR_PALETTE,
        "quizzes": quizzes,
        "active_sessions": active_sessions,
    })


@login_required
@require_POST
def remove_student_from_class(request, class_id, pk):
    school_class = get_object_or_404(SchoolClass, pk=class_id, teacher=request.user)
    student = get_object_or_404(Student, pk=pk, teacher=request.user, school_class=school_class)
    name = student.name
    student.delete()
    messages.success(request, f"{name} removed")
    return redirect("dashboard:class_detail", pk=school_class.pk)


@login_required
@require_POST
def start_class_session(request, class_id):
    school_class = get_object_or_404(SchoolClass, pk=class_id, teacher=request.user)
    quiz = get_object_or_404(Quiz, pk=request.POST.get("quiz"), teacher=request.user)

    students = school_class.students.all()
    if not students.exists():
        messages.error(request, "Add students to this class before starting a session.")
        return redirect("dashboard:class_detail", pk=school_class.pk)

    session = GameSession.objects.create(teacher=request.user, quiz=quiz)
    session.students.set(students)
    messages.success(request, f"Session started for {school_class.display_name} — code: {session.code}")
    return redirect("dashboard:class_detail", pk=school_class.pk)

class _Row:
    def __init__(self, d):
        self.__dict__.update(d)

def _class_filtered_page(request, session_key, items, class_attr, template, extra_context=None):
    classes = SchoolClass.objects.filter(teacher=request.user)
    classes_present = [c for c in classes if any(getattr(i, class_attr) == c for i in items)]
    default_class = classes_present[0] if classes_present else classes.first()

    current_id = request.GET.get("class") or request.session.get(session_key)
    current_class = classes.filter(pk=current_id).first() if current_id else None
    if not current_class:
        current_class = default_class

    request.session[session_key] = current_class.pk if current_class else None
    rows = [i for i in items if current_class and getattr(i, class_attr) == current_class]

    context = {"classes": classes, "current_class": current_class, "rows": rows}
    if extra_context:
        context.update(extra_context)
    return render(request, template, context)

@login_required
def leaderboard(request):
    students = list(Student.objects.filter(teacher=request.user).order_by("-points"))
    return _class_filtered_page(request, "leaderboard_class", students, "school_class", "dashboard/leaderboard.html")


@login_required
def student_scores(request):
    students = Student.objects.filter(teacher=request.user)
    rows = []
    for s in students:
        latest = s.latest_attempt
        rows.append(_Row({
            "name": s.name,
            "school_class": s.school_class,
            "quiz": latest.quiz.title if latest else "—",
            "score": latest.score if latest else None,
            "status": latest.status if latest else None,
        }))
    return _class_filtered_page(request, "studentscores_class", rows, "school_class", "dashboard/student_scores.html")


@login_required
def performance(request):
    students = Student.objects.filter(teacher=request.user)
    rows = []
    for s in students:
        pct = s.average_score
        if pct is None:
            continue
        rows.append(_Row({"name": s.name, "school_class": s.school_class, "pct": pct}))
    return _class_filtered_page(request, "performance_class", rows, "school_class", "dashboard/performance.html")

@login_required
def scoreboard(request):
    quizzes = Quiz.objects.filter(teacher=request.user, is_published=True)
    accordion = request.session.get("quiz_accordion", {"Preschool": True, "Elementary": False})

    if request.method == "POST" and request.POST.get("action") == "toggle":
        level = request.POST.get("level")
        accordion[level] = not accordion.get(level, False)
        request.session["quiz_accordion"] = accordion
        return redirect("dashboard:scoreboard")

    sections = []
    for level_group, _ in LEVEL_GROUPS:
        rows = quizzes.filter(level_group=level_group)
        sections.append({
            "level": level_group,
            "rows": rows,
            "is_open": accordion.get(level_group, False),
            "count": rows.count(),
        })

    return render(request, "dashboard/scoreboard.html", {"sections": sections})

def _get_active_session(code):
    return GameSession.objects.filter(code=code, is_active=True).select_related("quiz").first()


@require_GET
def api_session_questions(request, code):
    session = _get_active_session(code)
    if not session:
        return JsonResponse({"error": "Session not found or inactive"}, status=404)

    questions = []
    for q in session.quiz.questions.all():
        options = list(q.options.all())
        correct_index = next((i for i, o in enumerate(options) if o.is_correct), 0)
        questions.append({
            "text": q.text,
            "options": [o.text for o in options],
            "correct": correct_index,
        })

    return JsonResponse({
        "theme": session.quiz.title,
        "questions": questions,
    })


@require_GET
def api_session_roster(request, code):
    session = _get_active_session(code)
    if not session:
        return JsonResponse({"error": "Session not found or inactive"}, status=404)

    roster = [
        {
            "id": s.id,
            "name": s.name,
            "color_hex": s.color_hex,
            "gender": s.gender,
        }
        for s in session.students.all()
    ]
    return JsonResponse({"students": roster})


@csrf_exempt
def api_submit_answer(request, code):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    session = _get_active_session(code)
    if not session:
        return JsonResponse({"error": "Session not found or inactive"}, status=404)

    try:
        data = json.loads(request.body)
        student_id = data["student_id"]
        was_correct = bool(data["was_correct"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid payload"}, status=400)

    student = session.students.filter(id=student_id).first()
    if not student:
        return JsonResponse({"error": "Student not in this session"}, status=404)

    if was_correct:
        student.points += 1
        student.save(update_fields=["points"])

    return JsonResponse({"ok": True, "points": student.points})


@csrf_exempt
def api_submit_finish(request, code):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    session = _get_active_session(code)
    if not session:
        return JsonResponse({"error": "Session not found or inactive"}, status=404)

    try:
        data = json.loads(request.body)
        student_id = data["student_id"]
        score = int(data.get("score", 100))
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid payload"}, status=400)

    student = session.students.filter(id=student_id).first()
    if not student:
        return JsonResponse({"error": "Student not in this session"}, status=404)

    student.badges += 1
    student.save(update_fields=["badges"])

    QuizAttempt.objects.create(quiz=session.quiz, student=student, score=score)

    return JsonResponse({"ok": True, "badges": student.badges})

@login_required
def start_session(request):
    quizzes = Quiz.objects.filter(teacher=request.user, is_published=True)
    students = Student.objects.filter(teacher=request.user)

    if request.method == "POST":
        quiz_id = request.POST.get("quiz")
        student_ids = request.POST.getlist("students")
        quiz = get_object_or_404(Quiz, pk=quiz_id, teacher=request.user)

        session = GameSession.objects.create(teacher=request.user, quiz=quiz)
        session.students.set(student_ids)

        messages.success(request, f"Session started — code: {session.code}")
        return redirect("dashboard:start_session")

    active_sessions = GameSession.objects.filter(teacher=request.user, is_active=True).order_by("-created_at")

    return render(request, "dashboard/start_session.html", {
        "quizzes": quizzes,
        "students": students,
        "active_sessions": active_sessions,
    })