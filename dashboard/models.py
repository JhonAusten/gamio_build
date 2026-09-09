from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

GRADE_LEVELS = [
    ("Preschool", "Preschool"),
    ("Grade 1", "Grade 1"),
    ("Grade 2", "Grade 2"),
    ("Grade 3", "Grade 3"),
    ("Grade 4", "Grade 4"),
    ("Grade 5", "Grade 5"),
    ("Grade 6", "Grade 6"),
]
GRADE_LEVEL_VALUES = [g[0] for g in GRADE_LEVELS]

LEVEL_GROUPS = [
    ("Preschool", "Preschool"),
    ("Elementary", "Elementary"),
]

ELEMENTARY_GRADES = ["Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6"]


def grades_for_level_group(level_group):
    if level_group == "Preschool":
        return ["Preschool"]
    return ELEMENTARY_GRADES


# Colors the in-game color-detector recognizes. Each color can only belong to
# ONE active student at a time so the detector can tell students apart.
COLOR_PALETTE = [
    ("Red", "#E8493C"),
    ("Blue", "#3B7CB0"),
    ("Green", "#5DBB8E"),
    ("Yellow", "#F2C94C"),
    ("Purple", "#9B6FDE"),
    ("Orange", "#F2994A"),
    ("Teal", "#4DAEB0"),
    ("Pink", "#E8887A"),
    ("Brown", "#A97155"),
    ("Cyan", "#5BA9C4"),
    ("Lime", "#9ABF5C"),
    ("Magenta", "#C1558B"),
]

DEFAULT_QUESTIONS_FALLBACK = [
    {"text": "What is 1/2 + 1/4?", "options": ["3/4", "2/6", "1/6", "2/4"], "correct": 0},
    {"text": "Which fraction is the largest?", "options": ["1/8", "1/2", "1/4", "1/5"], "correct": 1},
    {"text": "True or False: 2/4 is the same as 1/2.", "options": ["True", "False", "Maybe", "Never"], "correct": 0},
    {
        "text": "If a pizza is cut into 8 equal slices and you eat 2, what fraction did you eat?",
        "options": ["2/6", "2/8", "8/2", "6/8"],
        "correct": 1,
    },
]

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    class_name = models.CharField(max_length=120, blank=True)

    def display_name(self):
        return self.user.get_full_name() or self.user.username

    def __str__(self):
        return self.display_name()

class SchoolClass(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="classes")
    grade = models.CharField(max_length=20, choices=GRADE_LEVELS)
    section = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["grade", "section"]
        unique_together = ("teacher", "grade", "section")

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return f"{self.grade} - {self.section}"

class Student(models.Model):
    GENDER_CHOICES = [("Male", "Male"), ("Female", "Female")]

    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="students")
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="students", null=True, blank=True)
    name = models.CharField(max_length=120)
    grade = models.CharField(max_length=20, choices=GRADE_LEVELS)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    color_name = models.CharField(max_length=20)
    color_hex = models.CharField(max_length=7)
    points = models.PositiveIntegerField(default=0)
    badges = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def latest_attempt(self):
        return self.attempts.order_by("-played_at").first()

    @property
    def average_score(self):
        agg = self.attempts.aggregate(models.Avg("score"))["score__avg"]
        return round(agg) if agg is not None else None


class Quiz(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField(max_length=150)
    subject = models.CharField(max_length=80, default="New")
    level_group = models.CharField(max_length=20, choices=LEVEL_GROUPS)
    source_filename = models.CharField(max_length=255, blank=True)
    source_file = models.FileField(upload_to="lesson_files/", blank=True, null=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def average_score(self):
        agg = self.attempts.aggregate(models.Avg("score"))["score__avg"]
        return round(agg) if agg is not None else None

    @property
    def wrong_count(self):
        """Students who scored below the 'mastered' threshold on this quiz."""
        return self.attempts.filter(score__lt=60).count()

    @property
    def total_attempts(self):
        return self.attempts.count()


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:50]


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attempts")
    score = models.PositiveIntegerField(help_text="Percentage score, 0-100")
    played_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-played_at"]

    @property
    def status(self):
        return "Great" if self.score >= 60 else "Needs Support"

    def __str__(self):
        return f"{self.student} \u00b7 {self.quiz} \u00b7 {self.score}%"

import random
import string


def generate_session_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class GameSession(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="game_sessions")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="game_sessions")
    students = models.ManyToManyField(Student, related_name="game_sessions")
    code = models.CharField(max_length=8, unique=True, default=generate_session_code)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} — {self.quiz.title}"