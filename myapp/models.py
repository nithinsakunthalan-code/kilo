from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Goal(models.Model):
    """Per-user daily/weekly targets (one row per user)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goal')
    daily_calories = models.PositiveIntegerField(
        default=2200, validators=[MinValueValidator(800), MaxValueValidator(10000)])
    daily_protein = models.PositiveIntegerField(
        default=150, validators=[MaxValueValidator(500)], help_text='grams')
    weekly_workouts = models.PositiveSmallIntegerField(
        default=4, validators=[MaxValueValidator(14)])

    @classmethod
    def for_user(cls, user):
        goal, _ = cls.objects.get_or_create(user=user)
        return goal

    def __str__(self):
        return f'{self.user}: {self.daily_calories} kcal / {self.daily_protein} g protein'


class Meal(models.Model):
    BREAKFAST, LUNCH, DINNER, SNACK = 'breakfast', 'lunch', 'dinner', 'snack'
    MEAL_TYPES = [
        (BREAKFAST, 'Breakfast'),
        (LUNCH, 'Lunch'),
        (DINNER, 'Dinner'),
        (SNACK, 'Snack'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meals')
    date = models.DateField(default=timezone.localdate)
    meal_type = models.CharField(max_length=10, choices=MEAL_TYPES, default=BREAKFAST)
    name = models.CharField(max_length=120)
    calories = models.PositiveIntegerField(validators=[MaxValueValidator(10000)])
    protein = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(1000)], help_text='grams')
    carbs = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(1000)], help_text='grams')
    fat = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(1000)], help_text='grams')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created']
        indexes = [models.Index(fields=['user', 'date'])]

    def __str__(self):
        return f'{self.name} ({self.calories} kcal)'


class Workout(models.Model):
    STRENGTH, CARDIO, MOBILITY, OTHER = 'strength', 'cardio', 'mobility', 'other'
    CATEGORIES = [
        (STRENGTH, 'Strength'),
        (CARDIO, 'Cardio'),
        (MOBILITY, 'Mobility'),
        (OTHER, 'Other'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workouts')
    date = models.DateField(default=timezone.localdate)
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=10, choices=CATEGORIES, default=STRENGTH)
    duration_min = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(1440)], help_text='minutes')
    calories_burned = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(10000)])
    sets = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(100)])
    reps = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(1000)])
    weight_kg = models.DecimalField(
        max_digits=6, decimal_places=1, null=True, blank=True, validators=[MinValueValidator(0)])
    notes = models.CharField(max_length=200, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created']
        indexes = [models.Index(fields=['user', 'date'])]

    @property
    def volume(self):
        """Total kg lifted (sets x reps x weight), or None if not a lifting entry."""
        if self.sets and self.reps and self.weight_kg:
            return int(self.sets * self.reps * self.weight_kg)
        return None

    def __str__(self):
        return f'{self.name} ({self.duration_min} min)'
