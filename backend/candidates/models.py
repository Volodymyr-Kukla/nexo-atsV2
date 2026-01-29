from core.models import TimeStampedModel
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Skill(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Candidate(TimeStampedModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50, blank=True, default="")

    city = models.CharField(max_length=120, blank=True, default="")
    experience_years = models.PositiveSmallIntegerField(default=0)

    about = models.TextField(blank=True, default="")

    rating = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )

    is_archived = models.BooleanField(default=False)

    skills = models.ManyToManyField(
        Skill, through="CandidateSkill", related_name="candidates", blank=True
    )

    class Meta:
        ordering = ["-created_at"]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})"


class CandidateSkill(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["candidate", "skill"], name="uniq_candidate_skill"),
        ]

    def __str__(self) -> str:
        return f"{self.candidate_id}:{self.skill_id}"


class CandidateExperience(TimeStampedModel):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="experiences")

    title = models.CharField(max_length=150)
    company = models.CharField(max_length=150, blank=True, default="")

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    description = models.TextField(blank=True, default="")

    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self) -> str:
        return f"{self.candidate_id}:{self.title}"


# Create your models here.
