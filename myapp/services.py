"""Business logic shared by the HTML views and the REST API.

Views and API endpoints stay thin: they authenticate, validate and render,
while every number shown to the user is computed here.
"""
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import Goal, Meal, Workout


def day_totals(user, day):
    """Calories/macros eaten and calories burned on one day."""
    eaten = Meal.objects.filter(user=user, date=day).aggregate(
        calories=Sum('calories'), protein=Sum('protein'),
        carbs=Sum('carbs'), fat=Sum('fat'),
    )
    burned = Workout.objects.filter(user=user, date=day).aggregate(
        burned=Sum('calories_burned'), minutes=Sum('duration_min'),
    )
    return {
        'calories': eaten['calories'] or 0,
        'protein': eaten['protein'] or 0,
        'carbs': eaten['carbs'] or 0,
        'fat': eaten['fat'] or 0,
        'burned': burned['burned'] or 0,
        'minutes': burned['minutes'] or 0,
    }


def week_series(user, end_day, goal, days=7):
    """Per-day eaten/burned for the `days` days ending at `end_day`, with bar heights (0-100)."""
    span = [end_day - timedelta(days=i) for i in range(days - 1, -1, -1)]
    eaten = {
        r['date']: r['t']
        for r in Meal.objects.filter(user=user, date__gte=span[0], date__lte=end_day)
        .values('date').annotate(t=Sum('calories'))
    }
    burned = {
        r['date']: r['t']
        for r in Workout.objects.filter(user=user, date__gte=span[0], date__lte=end_day)
        .values('date').annotate(t=Sum('calories_burned'))
    }
    peak = max([goal.daily_calories, *eaten.values(), *burned.values()]) or 1
    return [
        {
            'date': d,
            'label': d.strftime('%a'),
            'is_today': d == end_day,
            'eaten': eaten.get(d, 0),
            'burned': burned.get(d, 0),
            'eaten_h': round(eaten.get(d, 0) / peak * 100),
            'burned_h': round(burned.get(d, 0) / peak * 100),
        }
        for d in span
    ]


def sessions_this_week(user, day):
    """Distinct days with at least one workout since Monday of `day`'s week."""
    week_start = day - timedelta(days=day.weekday())
    return (
        Workout.objects.filter(user=user, date__gte=week_start, date__lte=day)
        .values('date').distinct().count()
    )


def _pct(value, target):
    return min(round(value / target * 100), 100) if target else 0


def dashboard_summary(user, day=None):
    """Everything the 'Today' screen and /api/summary/ need, in one dict."""
    day = day or timezone.localdate()
    goal = Goal.for_user(user)
    totals = day_totals(user, day)
    net = totals['calories'] - totals['burned']
    sessions = sessions_this_week(user, day)
    ring_pct = _pct(totals['calories'], goal.daily_calories)
    return {
        'date': day,
        'goal': goal,
        'totals': totals,
        'net_calories': net,
        'remaining': goal.daily_calories - net,
        'over': net > goal.daily_calories,
        'ring_pct': ring_pct,
        'protein_pct': _pct(totals['protein'], goal.daily_protein),
        'sessions_this_week': sessions,
        'workout_pct': _pct(sessions, goal.weekly_workouts),
        'week': week_series(user, day, goal),
    }
