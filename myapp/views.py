from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import services
from .forms import GoalForm, MealForm, SignUpForm, WorkoutForm
from .models import Goal, Meal, Workout


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return timezone.localdate()


def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('dashboard')
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def dashboard(request):
    summary = services.dashboard_summary(request.user)
    day = summary['date']
    totals = summary['totals']
    goal = summary['goal']
    context = {
        'today': day,
        'goal': goal,
        'calories': totals['calories'],
        'burned': totals['burned'],
        'protein': totals['protein'],
        'carbs': totals['carbs'],
        'fat': totals['fat'],
        'remaining': summary['remaining'],
        'over': summary['over'],
        'ring_pct': summary['ring_pct'],
        'ring_deg': summary['ring_pct'] * 3.6,
        'protein_pct': summary['protein_pct'],
        'workouts_this_week': summary['sessions_this_week'],
        'workout_pct': summary['workout_pct'],
        'week': summary['week'],
        'todays_meals': Meal.objects.filter(user=request.user, date=day),
        'todays_workouts': Workout.objects.filter(user=request.user, date=day),
    }
    return render(request, 'myapp/dashboard.html', context)


@login_required
def meals(request):
    day = _parse_date(request.GET.get('date'))
    if request.method == 'POST':
        form = MealForm(request.POST)
        if form.is_valid():
            meal = form.save(commit=False)
            meal.user = request.user
            meal.save()
            messages.success(request, f'Logged {meal.name}.')
            return redirect(f"{request.path}?date={meal.date.isoformat()}")
    else:
        form = MealForm(initial={'date': day})

    day_meals = Meal.objects.filter(user=request.user, date=day)
    context = {
        'form': form,
        'day': day,
        'prev_day': day - timedelta(days=1),
        'next_day': day + timedelta(days=1),
        'is_today': day == timezone.localdate(),
        'meals': day_meals,
        'totals': day_meals.aggregate(
            calories=Sum('calories'), protein=Sum('protein'),
            carbs=Sum('carbs'), fat=Sum('fat')),
        'goal': Goal.for_user(request.user),
    }
    return render(request, 'myapp/meals.html', context)


@login_required
def workouts(request):
    if request.method == 'POST':
        form = WorkoutForm(request.POST)
        if form.is_valid():
            workout = form.save(commit=False)
            workout.user = request.user
            workout.save()
            messages.success(request, f'Logged {workout.name}.')
            return redirect('workouts')
    else:
        form = WorkoutForm()

    recent = Workout.objects.filter(
        user=request.user, date__gte=timezone.localdate() - timedelta(days=30))
    stats = recent.aggregate(minutes=Sum('duration_min'), burned=Sum('calories_burned'))
    context = {
        'form': form,
        'workouts': recent,
        'sessions': recent.values('date').distinct().count(),
        'minutes': stats['minutes'] or 0,
        'burned': stats['burned'] or 0,
    }
    return render(request, 'myapp/workouts.html', context)


@login_required
def goals(request):
    goal = Goal.for_user(request.user)
    if request.method == 'POST':
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Goals updated.')
            return redirect('dashboard')
    else:
        form = GoalForm(instance=goal)
    return render(request, 'myapp/goals.html', {'form': form})


@login_required
@require_POST
def delete_meal(request, pk):
    meal = get_object_or_404(Meal, pk=pk, user=request.user)
    day = meal.date.isoformat()
    meal.delete()
    return redirect(f"/meals/?date={day}")


@login_required
@require_POST
def delete_workout(request, pk):
    get_object_or_404(Workout, pk=pk, user=request.user).delete()
    return redirect('workouts')
