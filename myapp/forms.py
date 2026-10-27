from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Goal, Meal, Workout


class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = ('username',)


class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ['date', 'meal_type', 'name', 'calories', 'protein', 'carbs', 'fat']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Chicken rice bowl'}),
        }


class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = [
            'date', 'name', 'category', 'duration_min', 'calories_burned',
            'sets', 'reps', 'weight_kg', 'notes',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Back squat'}),
            'notes': forms.TextInput(attrs={'placeholder': 'optional'}),
        }


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['daily_calories', 'daily_protein', 'weekly_workouts']
