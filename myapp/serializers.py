from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Goal, Meal, Workout


class MealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meal
        fields = ['id', 'date', 'meal_type', 'name', 'calories', 'protein', 'carbs', 'fat', 'created']
        read_only_fields = ['id', 'created']


class WorkoutSerializer(serializers.ModelSerializer):
    volume = serializers.IntegerField(read_only=True)

    class Meta:
        model = Workout
        fields = [
            'id', 'date', 'name', 'category', 'duration_min', 'calories_burned',
            'sets', 'reps', 'weight_kg', 'volume', 'notes', 'created',
        ]
        read_only_fields = ['id', 'volume', 'created']


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ['daily_calories', 'daily_protein', 'weekly_workouts']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = get_user_model()
        fields = ['username', 'password']

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)
