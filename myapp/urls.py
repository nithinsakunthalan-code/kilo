from django.contrib.auth import views as auth_views
from django.urls import include, path
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.routers import DefaultRouter

from . import api, views


class ThrottledObtainAuthToken(ObtainAuthToken):
    throttle_classes = [api.AuthThrottle]


router = DefaultRouter()
router.register('meals', api.MealViewSet, basename='api-meal')
router.register('workouts', api.WorkoutViewSet, basename='api-workout')

api_urls = [
    path('auth/register/', api.RegisterView.as_view(), name='api-register'),
    path('auth/token/', ThrottledObtainAuthToken.as_view(), name='api-token'),
    path('goal/', api.GoalView.as_view(), name='api-goal'),
    path('summary/', api.SummaryView.as_view(), name='api-summary'),
    path('', include(router.urls)),
]

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('meals/', views.meals, name='meals'),
    path('meals/<int:pk>/delete/', views.delete_meal, name='delete_meal'),
    path('workouts/', views.workouts, name='workouts'),
    path('workouts/<int:pk>/delete/', views.delete_workout, name='delete_workout'),
    path('goals/', views.goals, name='goals'),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/signup/', views.signup, name='signup'),
    path('api/', include(api_urls)),
]
