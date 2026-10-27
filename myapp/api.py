"""REST API (mounted at /api/). Every endpoint is scoped to request.user."""
from datetime import date

from rest_framework import generics, serializers as drf_serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from . import services
from .models import Goal, Meal, Workout
from .serializers import (
    GoalSerializer, MealSerializer, RegisterSerializer, WorkoutSerializer,
)


def _query_date(request, name):
    raw = request.query_params.get(name)
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise drf_serializers.ValidationError({name: 'Use YYYY-MM-DD.'})


class OwnedByUserMixin:
    """Restrict a viewset to the caller's rows and stamp new rows with the caller."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset().filter(user=self.request.user)
        exact, start, end = (_query_date(self.request, k) for k in ('date', 'from', 'to'))
        if exact:
            qs = qs.filter(date=exact)
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MealViewSet(OwnedByUserMixin, viewsets.ModelViewSet):
    queryset = Meal.objects.all()
    serializer_class = MealSerializer


class WorkoutViewSet(OwnedByUserMixin, viewsets.ModelViewSet):
    queryset = Workout.objects.all()
    serializer_class = WorkoutSerializer


class GoalView(generics.RetrieveUpdateAPIView):
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return Goal.for_user(self.request.user)


class SummaryView(APIView):
    """GET /api/summary/?date=YYYY-MM-DD — totals, goal progress and the 7-day series."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        s = services.dashboard_summary(request.user, _query_date(request, 'date'))
        return Response({
            'date': s['date'],
            'goal': GoalSerializer(s['goal']).data,
            'totals': s['totals'],
            'net_calories': s['net_calories'],
            'remaining_calories': s['remaining'],
            'over_goal': s['over'],
            'calorie_progress_pct': s['ring_pct'],
            'protein_progress_pct': s['protein_pct'],
            'sessions_this_week': s['sessions_this_week'],
            'week': [
                {'date': d['date'], 'eaten': d['eaten'], 'burned': d['burned']} for d in s['week']
            ],
        })


class AuthThrottle(AnonRateThrottle):
    rate = '20/min'


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — create an account and return its API token."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'username': user.username, 'token': token.key}, status=status.HTTP_201_CREATED)
