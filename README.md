# Gamio — Django Edition

A Django rebuild of the Gamio teacher dashboard prototype: turn lesson files into
quizzes, manage a student roster with in-game characters, and track scores,
leaderboards, and performance — all server-rendered with Django templates.

## What's included

- **Accounts** — sign up, sign in, sign out, and a simulated 3-step "forgot
  password" flow (no real email is sent; the reset code is shown on-screen
  since there's no email backend configured).
- **Dashboard** — class stats, a lesson-file upload modal that generates a
  starter quiz, and a leaderboard/performance summary.
- **Manage Students** — add a student (name, grade, player type) and Gamio
  auto-assigns one of 12 detector colors and renders an SVG game character.
- **Quizzes** — published quizzes grouped into Preschool / Elementary
  accordions, each showing average score and how many students need review.
- **Edit Questions** — edit a generated quiz's questions/options, add or
  delete questions, save a draft, or publish it to the game.
- **Leader Board / Students Scores / Performance Tracker** — grade-filterable
  views built from real `Student`, `Quiz`, and `QuizAttempt` data.

The "AI quiz generation" from an uploaded file is stubbed out: uploading any
file seeds a starter question set you can edit before publishing. Wire in a
real generator (e.g. an LLM call) inside `dashboard/views.py::upload_quiz`
when you're ready.

## Project layout

```
gamio/            Django project settings & root URLs
dashboard/        The app: models, views, forms, templates, static CSS
  models.py        Student, Quiz, Question, Option, QuizAttempt, TeacherProfile
  views.py         All page views
  forms.py         SignUpForm, StudentForm, QuizUploadForm
  urls.py          App routes
  templates/dashboard/   All page templates (extend base.html)
  static/dashboard/css/style.css   Shared design system, ported from the prototype
  management/commands/seed_demo.py   Optional demo-data seeder
```

## Setup

```bash
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/

# optional: seed a demo teacher (user: demo / password: demo1234)
# with sample students, quizzes, and scores
python manage.py seed_demo

python manage.py runserver
```

Visit `http://127.0.0.1:8000/`. Sign up for a new teacher account, or sign in
with the seeded `demo` / `demo1234` account.

The Django admin at `/admin/` is fully wired up for `Quiz`, `Question`,
`Student`, and `QuizAttempt` if you want to poke at the data directly.

## Notes on decisions made while porting

- The original was a single-file client-side mock-up with hardcoded demo
  data and in-memory state. This port replaces that with real models, a
  proper `User`-based auth system, and Django's session framework for the
  bits of transient UI state (which accordion is open, which quiz is
  mid-draft, the forgot-password step).
- Each teacher only sees their own students and quizzes (`teacher` foreign
  key + `request.user` filtering throughout).
- Toasts use Django's `messages` framework and auto-dismiss client-side.
- File uploads are stored under `media/lesson_files/` in development
  (`MEDIA_ROOT`); configure real storage (e.g. S3) for production.
