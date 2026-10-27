from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from . import services
from .models import Goal, Meal, Workout

User = get_user_model()


class ServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ana', password='pw-12345-xyz')
        self.today = timezone.localdate()

    def test_day_totals_and_summary(self):
        Meal.objects.create(user=self.user, name='Oats', calories=400, protein=20, carbs=60, fat=8)
        Meal.objects.create(user=self.user, name='Rice', calories=600, protein=30, carbs=90, fat=5)
        Workout.objects.create(user=self.user, name='Run', category='cardio', duration_min=30, calories_burned=300)
        s = services.dashboard_summary(self.user)
        self.assertEqual(s['totals']['calories'], 1000)
        self.assertEqual(s['totals']['protein'], 50)
        self.assertEqual(s['net_calories'], 700)
        self.assertEqual(s['remaining'], 2200 - 700)
        self.assertFalse(s['over'])
        self.assertEqual(s['sessions_this_week'], 1)
        self.assertEqual(len(s['week']), 7)
        self.assertEqual(s['week'][-1]['eaten'], 1000)

    def test_over_goal_and_progress_cap(self):
        Meal.objects.create(user=self.user, name='Feast', calories=3000)
        s = services.dashboard_summary(self.user)
        self.assertTrue(s['over'])
        self.assertEqual(s['ring_pct'], 100)

    def test_other_users_and_old_days_excluded(self):
        other = User.objects.create_user('bo', password='pw-12345-xyz')
        Meal.objects.create(user=other, name='Not mine', calories=999)
        Meal.objects.create(user=self.user, name='Yesterday', calories=500, date=self.today - timedelta(days=1))
        s = services.dashboard_summary(self.user)
        self.assertEqual(s['totals']['calories'], 0)
        self.assertEqual(s['week'][-2]['eaten'], 500)

    def test_volume(self):
        w = Workout(sets=5, reps=5, weight_kg=100, duration_min=40)
        self.assertEqual(w.volume, 2500)
        self.assertIsNone(Workout(duration_min=20).volume)


class WebTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ana', password='pw-12345-xyz')

    def test_pages_require_login(self):
        for name in ('dashboard', 'meals', 'workouts', 'goals'):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302)
            self.assertIn(reverse('login'), r['Location'])

    def test_signup_logs_in_and_creates_goal_lazily(self):
        r = self.client.post(reverse('signup'), {
            'username': 'newbie', 'password1': 'Str0ng-pass-99', 'password2': 'Str0ng-pass-99'})
        self.assertRedirects(r, reverse('dashboard'))
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
        self.assertTrue(Goal.objects.filter(user__username='newbie').exists())

    def test_log_and_delete_meal(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse('meals'), {
            'date': timezone.localdate().isoformat(), 'meal_type': 'lunch',
            'name': 'Bowl', 'calories': 650, 'protein': 40, 'carbs': 70, 'fat': 15})
        self.assertEqual(r.status_code, 302)
        meal = Meal.objects.get()
        self.assertEqual(meal.user, self.user)
        self.client.post(reverse('delete_meal', args=[meal.pk]))
        self.assertEqual(Meal.objects.count(), 0)

    def test_cannot_delete_another_users_meal(self):
        other = User.objects.create_user('bo', password='pw-12345-xyz')
        meal = Meal.objects.create(user=other, name='Theirs', calories=100)
        self.client.force_login(self.user)
        r = self.client.post(reverse('delete_meal', args=[meal.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Meal.objects.filter(pk=meal.pk).exists())


class ApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ana', password='pw-12345-xyz')
        self.other = User.objects.create_user('bo', password='pw-12345-xyz')
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=self.user).key}')

    def test_requires_authentication(self):
        r = APIClient().get('/api/meals/')
        self.assertEqual(r.status_code, 401)

    def test_register_then_token_login(self):
        r = APIClient().post('/api/auth/register/', {'username': 'cy', 'password': 'Str0ng-pass-99'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertIn('token', r.json())
        r = APIClient().post('/api/auth/token/', {'username': 'cy', 'password': 'Str0ng-pass-99'}, format='json')
        self.assertEqual(r.status_code, 200)
        weak = APIClient().post('/api/auth/register/', {'username': 'dee', 'password': '123'}, format='json')
        self.assertEqual(weak.status_code, 400)

    def test_meal_crud_is_scoped_to_owner(self):
        r = self.api.post('/api/meals/', {'name': 'Eggs', 'calories': 300, 'protein': 20}, format='json')
        self.assertEqual(r.status_code, 201)
        mine = r.json()['id']
        theirs = Meal.objects.create(user=self.other, name='Secret', calories=1).pk

        listing = self.api.get('/api/meals/').json()
        self.assertEqual([m['id'] for m in listing['results']], [mine])
        self.assertEqual(self.api.get(f'/api/meals/{theirs}/').status_code, 404)
        self.assertEqual(self.api.delete(f'/api/meals/{theirs}/').status_code, 404)
        self.assertEqual(self.api.patch(f'/api/meals/{mine}/', {'calories': 350}, format='json').status_code, 200)
        self.assertEqual(self.api.delete(f'/api/meals/{mine}/').status_code, 204)

    def test_cannot_assign_meal_to_another_user(self):
        r = self.api.post('/api/meals/', {'name': 'X', 'calories': 5, 'user': self.other.pk}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Meal.objects.get(pk=r.json()['id']).user, self.user)

    def test_validation(self):
        bad = self.api.post('/api/meals/', {'name': 'X', 'calories': -5}, format='json')
        self.assertEqual(bad.status_code, 400)
        huge = self.api.post('/api/meals/', {'name': 'X', 'calories': 999999}, format='json')
        self.assertEqual(huge.status_code, 400)
        bad_date = self.api.get('/api/meals/?date=not-a-date')
        self.assertEqual(bad_date.status_code, 400)

    def test_date_filter(self):
        today = timezone.localdate()
        Meal.objects.create(user=self.user, name='Old', calories=1, date=today - timedelta(days=3))
        Meal.objects.create(user=self.user, name='New', calories=1, date=today)
        r = self.api.get(f'/api/meals/?date={today.isoformat()}').json()
        self.assertEqual([m['name'] for m in r['results']], ['New'])
        r = self.api.get(f'/api/meals/?from={(today - timedelta(days=5)).isoformat()}').json()
        self.assertEqual(r['count'], 2)

    def test_workout_volume_and_goal_and_summary(self):
        r = self.api.post('/api/workouts/', {
            'name': 'Squat', 'category': 'strength', 'duration_min': 45,
            'calories_burned': 300, 'sets': 5, 'reps': 5, 'weight_kg': '100.0'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['volume'], 2500)

        self.assertEqual(self.api.patch('/api/goal/', {'daily_calories': 2500}, format='json').status_code, 200)
        self.assertEqual(self.api.patch('/api/goal/', {'daily_calories': 5}, format='json').status_code, 400)

        Meal.objects.create(user=self.user, name='Lunch', calories=1000)
        s = self.api.get('/api/summary/').json()
        self.assertEqual(s['totals']['calories'], 1000)
        self.assertEqual(s['totals']['burned'], 300)
        self.assertEqual(s['remaining_calories'], 2500 - 700)
        self.assertEqual(len(s['week']), 7)
