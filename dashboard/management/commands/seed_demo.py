import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from dashboard.models import COLOR_PALETTE, Option, Question, Quiz, QuizAttempt, Student, TeacherProfile

DEMO_STUDENTS = [
    ("Mariane Vertudes", "Grade 1", "Female"),
    ("John Cabornay", "Grade 1", "Male"),
    ("Jade Felicidario", "Preschool", "Female"),
    ("Rose Rama", "Preschool", "Female"),
    ("Miguel Santos", "Grade 2", "Male"),
    ("Ella Cruz", "Grade 2", "Female"),
]

DEMO_QUIZZES = [
    ("Fractions Fun", "Math", "Elementary", "fractions-fun.pdf"),
    ("Shapes & Colors", "Math", "Preschool", "shapes-and-colors.pptx"),
    ("Reading: Short Vowels", "English", "Elementary", "short-vowels.docx"),
]

QUESTIONS = [
    {"text": "What is 1/2 + 1/4?", "options": ["3/4", "2/6", "1/6", "2/4"], "correct": 0},
    {"text": "Which fraction is the largest?", "options": ["1/8", "1/2", "1/4", "1/5"], "correct": 1},
    {"text": "True or False: 2/4 is the same as 1/2.", "options": ["True", "False"], "correct": 0},
]


class Command(BaseCommand):
    help = "Seed a demo teacher account (demo / demo1234) with sample students, quizzes, and scores."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username="demo", defaults={"first_name": "Demo", "last_name": "Teacher"})
        if created:
            user.set_password("demo1234")
            user.save()
            TeacherProfile.objects.create(user=user, class_name="Grade 1 - Hope")
            self.stdout.write(self.style.SUCCESS("Created user 'demo' / password 'demo1234'"))
        else:
            self.stdout.write("User 'demo' already exists — reusing it.")

        students = []
        for i, (name, grade, gender) in enumerate(DEMO_STUDENTS):
            color_name, color_hex = COLOR_PALETTE[i % len(COLOR_PALETTE)]
            student, _ = Student.objects.get_or_create(
                teacher=user, name=name,
                defaults={"grade": grade, "gender": gender, "color_name": color_name,
                          "color_hex": color_hex, "points": random.randint(10, 32), "badges": random.randint(0, 5)},
            )
            students.append(student)

        for title, subject, level_group, filename in DEMO_QUIZZES:
            quiz, created = Quiz.objects.get_or_create(
                teacher=user, title=title,
                defaults={"subject": subject, "level_group": level_group,
                          "source_filename": filename, "is_published": True},
            )
            if created:
                for i, q in enumerate(QUESTIONS):
                    question = Question.objects.create(quiz=quiz, text=q["text"], order=i)
                    for j, opt_text in enumerate(q["options"]):
                        Option.objects.create(question=question, text=opt_text, is_correct=(j == q["correct"]), order=j)
                for student in students:
                    if student.grade == "Preschool" and level_group != "Preschool":
                        continue
                    if student.grade != "Preschool" and level_group == "Preschool":
                        continue
                    QuizAttempt.objects.create(quiz=quiz, student=student, score=random.randint(40, 100))

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
