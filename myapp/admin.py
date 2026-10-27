from django.contrib import admin

from .models import Goal, Meal, Workout


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'daily_calories', 'daily_protein', 'weekly_workouts')


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'date', 'meal_type', 'calories')
    list_filter = ('meal_type', 'date')
    search_fields = ('name', 'user__username')


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'date', 'category', 'duration_min', 'calories_burned')
    list_filter = ('category', 'date')
    search_fields = ('name', 'user__username')
