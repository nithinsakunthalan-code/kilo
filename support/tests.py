import json
from unittest import mock

import mongomock
import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from . import assistant, foods, mongo
from .models import FAQ, ErrorCode, Ticket

User = get_user_model()
PUBLIC_PAGES = ['faq', 'error_codes', 'support', 'health', 'login', 'signup']
PRIVATE_PAGES = ['dashboard', 'meals', 'workouts', 'goals']


def post_json(client, url, data):
    return client.post(url, json.dumps(data), content_type='application/json')


class FreshStateMixin:
    def setUp(self):
        cache.clear()
        mongo._down_until = 0.0
        self.mongo_db = mongomock.MongoClient()['test']
        patcher = mock.patch('support.mongo.get_db', return_value=self.mongo_db)
        patcher.start()
        self.addCleanup(patcher.stop)


class RequirementsTests(FreshStateMixin, TestCase):
    def test_ten_faqs_and_eight_error_codes_in_sql(self):
        self.assertGreaterEqual(FAQ.objects.count(), 10)
        codes = set(ErrorCode.objects.values_list('code', flat=True))
        self.assertGreaterEqual(len(codes), 8)
        self.assertTrue({'400', '401', '403', '404', '429', '500', '503'} <= codes)
        self.assertTrue(any(c.startswith('KILO-') for c in codes))

    def test_every_page_has_chat_widget_and_viewport(self):
        for name in PUBLIC_PAGES:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, 'id="chat"', msg_prefix=name)
            self.assertContains(response, 'name="viewport"', msg_prefix=name)
        self.client.force_login(User.objects.create_user('ana', password='pw-12345-xyz'))
        for name in PRIVATE_PAGES:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, 'id="chat"', msg_prefix=name)

    def test_faq_page_shows_database_faqs(self):
        response = self.client.get(reverse('faq'))
        for faq in FAQ.objects.all():
            self.assertContains(response, faq.question)

    def test_support_form_creates_ticket_linked_to_user(self):
        user = User.objects.create_user('ana', password='pw-12345-xyz')
        self.client.force_login(user)
        response = self.client.post(reverse('support'), {'email': 'a@b.co', 'message': 'My goal will not save'})
        self.assertContains(response, 'TKT-')
        ticket = Ticket.objects.get()
        self.assertEqual((ticket.source, ticket.email, ticket.user), ('form', 'a@b.co', user))

    def test_support_form_validation(self):
        response = self.client.post(reverse('support'), {'message': '', 'email': 'nope'})
        self.assertContains(response, 'Please write a message.')
        self.assertContains(response, 'valid email')
        self.assertEqual(Ticket.objects.count(), 0)


class ErrorPageTests(FreshStateMixin, TestCase):
    def test_custom_404_with_ask_assistant(self):
        response = self.client.get('/definitely/not/a/page/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'This page does not exist', status_code=404)
        self.assertContains(response, 'Ask the assistant', status_code=404)
        self.assertContains(response, 'data-ask=', status_code=404)
        self.assertContains(response, 'id="chat"', status_code=404)

    @override_settings(ROOT_URLCONF='support.test_urls')
    def test_custom_500_with_ask_assistant(self):
        client = Client(raise_request_exception=False)
        response = client.get('/boom/')
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, 'Something went wrong', status_code=500)
        self.assertContains(response, 'Ask the assistant', status_code=500)

    def test_real_401_and_429_codes_exist(self):
        self.assertEqual(APIClient().get('/api/meals/').status_code, 401)   # documented as error 401


class AssistantTests(FreshStateMixin, TestCase):
    def chat(self, message, session='s1'):
        return post_json(self.client, reverse('chat'), {'message': message, 'session_id': session})

    def test_answers_from_faq(self):
        data = self.chat('How do I log a meal?').json()
        self.assertEqual(data['source'], 'faq')
        self.assertIn('Meals page', data['reply'])
        self.assertEqual(Ticket.objects.count(), 0)

    def test_answers_several_app_questions(self):
        cases = {
            'how are my remaining calories calculated': 'Remaining = daily goal',
            'how can I change my protein goal': 'Goals page',
            'is there an api for developers': 'REST API',
            'can I use kilo on my phone': 'responsive',
        }
        for question, expected in cases.items():
            data = self.chat(question).json()
            self.assertEqual(data['source'], 'faq', question)
            self.assertIn(expected, data['reply'], question)

    def test_explains_every_error_code(self):
        for code in ('400', '401', '403', '404', '429', '500', '503', 'KILO-1001', 'KILO-2001'):
            data = self.chat(f'what does error {code} mean?').json()
            self.assertEqual(data['source'], 'error_code', code)
            self.assertIn(code, data['reply'])

    def test_unknown_question_creates_ticket(self):
        data = self.chat('What is the airspeed velocity of an unladen swallow?', 'sess-9').json()
        self.assertEqual(data['source'], 'ticket')
        ticket = Ticket.objects.get()
        self.assertEqual(data['ticket'], ticket.reference)
        self.assertEqual((ticket.session_id, ticket.source, ticket.user), ('sess-9', 'chat', None))

    def test_ticket_links_logged_in_user(self):
        user = User.objects.create_user('ana', password='pw-12345-xyz')
        self.client.force_login(user)
        self.chat('Completely unrelated gibberish zzz qqq')
        self.assertEqual(Ticket.objects.get().user, user)

    def test_smalltalk(self):
        self.assertEqual(self.chat('hi').json()['source'], 'smalltalk')
        self.assertEqual(Ticket.objects.count(), 0)

    def test_chat_logged_to_mongodb(self):
        data = self.chat('How do I log a workout?', 'sess-1').json()
        doc = self.mongo_db.chat_logs.find_one({'message_id': data['message_id']})
        self.assertEqual((doc['session_id'], doc['user_message']), ('sess-1', 'How do I log a workout?'))
        self.assertNotIn('127.0.0.1', json.dumps(doc, default=str))      # IP stored only as a hash

    def test_feedback_logged_to_mongodb(self):
        message_id = self.chat('How do I log a meal?').json()['message_id']
        response = post_json(self.client, reverse('chat-feedback'),
                             {'session_id': 's1', 'message_id': message_id, 'rating': 'down'})
        self.assertEqual(response.json(), {'ok': True, 'stored': True})
        self.assertEqual(self.mongo_db.feedback.find_one()['rating'], 'down')
        self.assertEqual(post_json(self.client, reverse('chat-feedback'), {'rating': 'meh'}).status_code, 400)

    def test_chat_survives_mongodb_outage(self):
        with mock.patch('support.mongo.get_db', return_value=None):
            self.assertEqual(self.chat('How do I log a meal?').status_code, 200)

    def test_validation_returns_kilo_code(self):
        for bad in ('', '   ', 'x' * 501):
            response = self.chat(bad)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['code'], 'KILO-1001')

    @override_settings(CHAT_RATE_LIMIT=3)
    def test_rate_limit_returns_429(self):
        statuses = [self.chat('hi').status_code for _ in range(5)]
        self.assertEqual(statuses, [200, 200, 200, 429, 429])

    def test_csrf_enforced_and_get_rejected(self):
        strict = Client(enforce_csrf_checks=True)
        response = strict.post(reverse('chat'), json.dumps({'message': 'hi'}), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get(reverse('chat')).status_code, 405)

    def test_ticket_email_only_for_same_session(self):
        self.chat('Completely unrelated gibberish zzz', 'mine')
        ref = Ticket.objects.get().reference
        url = reverse('chat-ticket-email')
        other = post_json(self.client, url, {'session_id': 'someone-else', 'reference': ref, 'email': 'x@y.co'})
        self.assertEqual(other.status_code, 404)
        mine = post_json(self.client, url, {'session_id': 'mine', 'reference': ref, 'email': 'x@y.co'})
        self.assertEqual(mine.status_code, 200)
        self.assertEqual(Ticket.objects.get().email, 'x@y.co')

    def test_retrieval_ranks_relevant_faq_first(self):
        ranked = assistant.rank_faqs('forgot my password', list(FAQ.objects.all()))
        self.assertIn('password', ranked[0][1].question.lower())


@override_settings(ANTHROPIC_API_KEY='test-key')
class LlmTests(FreshStateMixin, TestCase):
    def chat(self, message):
        return post_json(self.client, reverse('chat'), {'message': message, 'session_id': 's'}).json()

    def fake_llm(self, text):
        response = mock.Mock(status_code=200)
        response.json.return_value = {'content': [{'type': 'text', 'text': text}]}
        response.raise_for_status.return_value = None
        return response

    def test_llm_answer_used_when_available(self):
        with mock.patch('support.assistant.requests.post', return_value=self.fake_llm('Open Meals and press Add.')):
            data = self.chat('How do I log a meal?')
        self.assertEqual((data['source'], data['reply']), ('llm', 'Open Meals and press Add.'))

    def test_llm_timeout_falls_back_to_faq(self):
        with mock.patch('support.assistant.requests.post', side_effect=requests.Timeout):
            self.assertEqual(self.chat('How do I log a meal?')['source'], 'faq')

    def test_llm_no_answer_creates_ticket(self):
        with mock.patch('support.assistant.requests.post', return_value=self.fake_llm('NO_ANSWER')):
            self.assertEqual(self.chat('How do I log a meal?')['source'], 'ticket')


class FoodLookupTests(FreshStateMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user('ana', password='pw-12345-xyz')

    def off_response(self, products):
        ok = mock.Mock()
        ok.raise_for_status.return_value = None
        ok.json.return_value = {'hits': products}
        return ok

    def test_requires_login_401(self):
        response = self.client.get(reverse('food-lookup') + '?q=banana')
        self.assertEqual((response.status_code, response.json()['code']), (401, '401'))

    def test_short_query_400(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('food-lookup') + '?q=b').status_code, 400)

    def test_timeout_uses_fallback_with_time_limit(self):
        self.client.force_login(self.user)
        with mock.patch('support.foods.requests.get', side_effect=requests.Timeout) as get:
            data = self.client.get(reverse('food-lookup') + '?q=banana').json()
        self.assertEqual(data['source'], 'fallback')
        self.assertEqual(data['results'][0]['name'], 'Banana')
        self.assertEqual(get.call_args.kwargs['timeout'], 4.0)

    def test_success_parsed_and_cached(self):
        self.client.force_login(self.user)
        products = [
            {'product_name': 'Oat drink', 'brands': ['Acme', 'Other'],
             'nutriments': {'energy-kcal_100g': 46, 'proteins_100g': 1, 'carbohydrates_100g': 6.7, 'fat_100g': 1.5}},
            {'product_name': 'Soya drink', 'brands': 'Beta, Other',
             'nutriments': {'energy-kcal_100g': 39, 'proteins_100g': 3.3, 'carbohydrates_100g': 2.5, 'fat_100g': 1.8}},
            {'product_name': 'No energy value', 'brands': ['X'], 'nutriments': {}},
        ]
        with mock.patch('support.foods.requests.get', return_value=self.off_response(products)) as get:
            first = foods.search_foods('oat')
            second = foods.search_foods('OAT')
        self.assertEqual(first['source'], 'openfoodfacts')
        self.assertEqual(first['results'], [
            {'name': 'Oat drink (Acme)', 'calories': 46.0, 'protein': 1.0, 'carbs': 6.7, 'fat': 1.5},
            {'name': 'Soya drink (Beta)', 'calories': 39.0, 'protein': 3.3, 'carbs': 2.5, 'fat': 1.8},
        ])
        self.assertEqual(second, first)
        self.assertEqual(get.call_count, 1)

    def test_http_error_and_empty_results_use_fallback(self):
        bad = mock.Mock()
        bad.raise_for_status.side_effect = requests.HTTPError('503')
        with mock.patch('support.foods.requests.get', return_value=bad):
            self.assertEqual(foods.search_foods('rice')['source'], 'fallback')
        cache.clear()
        with mock.patch('support.foods.requests.get', return_value=self.off_response([])):
            self.assertEqual(foods.search_foods('paneer')['source'], 'fallback')


class HealthAndLoggingTests(FreshStateMixin, TestCase):
    @override_settings(MONGODB_URI='mongodb://test')
    def test_health_ok(self):
        response = self.client.get(reverse('health') + '?format=json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
        self.assertEqual(response.json()['checks'], {'database': 'ok', 'mongodb': 'ok'})

    @override_settings(MONGODB_URI='mongodb://test')
    def test_health_degraded_when_mongo_down(self):
        with mock.patch('support.mongo.get_db', return_value=None):
            response = self.client.get(reverse('health') + '?format=json')
        self.assertEqual((response.status_code, response.json()['status']), (200, 'degraded'))

    def test_health_503_when_database_down(self):
        with mock.patch('support.views._check_database', return_value='down'):
            response = self.client.get(reverse('health') + '?format=json')
        self.assertEqual(response.status_code, 503)

    def test_request_logging(self):
        with self.assertLogs('requests', level='INFO') as logs:
            response = self.client.get('/faq/')
            self.client.get('/nope/')
        self.assertIn('X-Request-ID', response)
        self.assertRegex(logs.output[0], r'method=GET path=/faq/ status=200 duration_ms=[\d.]+ user=-')
        self.assertIn('status=404', logs.output[1])
