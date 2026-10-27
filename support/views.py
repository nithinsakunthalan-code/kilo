import hashlib
import json
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import assistant, foods, mongo
from .middleware import client_ip
from .models import FAQ, ErrorCode, Ticket

logger = logging.getLogger('support')
STARTED = time.time()


# ------------------------------------------------------------------ pages
def faq(request):
    items = FAQ.objects.filter(is_published=True)
    categories = {}
    for item in items:
        categories.setdefault(item.category, []).append(item)
    return render(request, 'support/faq.html', {'categories': categories, 'count': items.count()})


def error_codes(request):
    return render(request, 'support/errors.html', {'codes': ErrorCode.objects.all()})


@require_http_methods(['GET', 'POST'])
def contact(request):
    errors, sent, values = {}, None, {'email': '', 'message': ''}
    if request.method == 'POST':
        values = {k: request.POST.get(k, '').strip() for k in values}
        if not values['message']:
            errors['message'] = 'Please write a message.'
        elif len(values['message']) > 2000:
            errors['message'] = 'Please keep it under 2000 characters.'
        if values['email'] and ('@' not in values['email'] or len(values['email']) > 254):
            errors['email'] = 'Enter a valid email address.'
        if not errors:
            ticket = Ticket.objects.create(
                question=values['message'], email=values['email'], source=Ticket.FORM,
                user=request.user if request.user.is_authenticated else None)
            sent = ticket.reference
            values = {'email': '', 'message': ''}
    return render(request, 'support/contact.html', {'errors': errors, 'sent': sent, 'values': values})


# ------------------------------------------------------------------ health check
def _check_database():
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return 'ok'
    except Exception as exc:  # noqa: BLE001
        logger.error('Health check: database down: %s', exc)
        return 'down'


@require_GET
def health(request):
    """Health page. HTML for browsers, JSON with ?format=json. 503 if the SQL database is down;
    MongoDB being down only degrades the app (chat still works, it just isn't logged)."""
    checks = {'database': _check_database(), 'mongodb': mongo.ping()}
    if checks['database'] != 'ok':
        overall, status = 'down', 503
    elif checks['mongodb'] == 'ok':
        overall, status = 'ok', 200
    else:
        overall, status = 'degraded', 200
    payload = {'status': overall, 'checks': checks, 'uptime_seconds': int(time.time() - STARTED),
               'assistant_llm': 'enabled' if settings.ANTHROPIC_API_KEY else 'faq_only'}
    if request.GET.get('format') == 'json':
        return JsonResponse(payload, status=status)
    return render(request, 'support/health.html', payload, status=status)


# ------------------------------------------------------------------ chat API
def _json_error(message, code, status, **extra):
    return JsonResponse({'error': message, 'code': code, **extra}, status=status)


def _rate_limited(ip):
    key = f'chat-rate:{ip}'
    window = settings.CHAT_RATE_WINDOW_SECONDS
    cache.add(key, 0, window)
    try:
        return cache.incr(key) > settings.CHAT_RATE_LIMIT
    except ValueError:                     # key expired between add and incr
        cache.set(key, 1, window)
        return False


def _body(request):
    try:
        data = json.loads(request.body or '{}')
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _hash_ip(ip):
    return hashlib.sha256(f'{settings.SECRET_KEY}:{ip}'.encode()).hexdigest()[:16]


@require_POST
def chat(request):
    ip = client_ip(request)
    if _rate_limited(ip):
        return _json_error('Too many messages. Please wait a minute and try again.', '429', 429,
                           retry_after=settings.CHAT_RATE_WINDOW_SECONDS)
    data = _body(request)
    message = str(data.get('message', '')).strip()
    session_id = str(data.get('session_id', ''))[:64]
    if not message or len(message) > settings.CHAT_MAX_MESSAGE_LENGTH:
        return _json_error(
            f'Message must be 1-{settings.CHAT_MAX_MESSAGE_LENGTH} characters.', 'KILO-1001', 400)

    started = time.perf_counter()
    result = assistant.reply_to(message, session_id, request.user)
    latency = round((time.perf_counter() - started) * 1000)
    username = request.user.get_username() if request.user.is_authenticated else None
    message_id = mongo.log_chat(
        session_id, message, result['reply'], result['source'], latency, _hash_ip(ip),
        username=username, ticket=result['ticket'], faq_id=result['faq_id'])
    return JsonResponse({
        'message_id': message_id, 'reply': result['reply'], 'source': result['source'],
        'ticket': result['ticket'], 'suggestions': result['suggestions'],
    })


@require_POST
def chat_feedback(request):
    data = _body(request)
    rating = data.get('rating')
    if rating not in ('up', 'down'):
        return _json_error('rating must be "up" or "down".', '400', 400)
    stored = mongo.log_feedback(
        str(data.get('session_id', ''))[:64], str(data.get('message_id', ''))[:64], rating,
        str(data.get('comment', ''))[:300])
    return JsonResponse({'ok': True, 'stored': stored})


@require_POST
def chat_ticket_email(request):
    """Attach an email to a ticket the same browser session created."""
    data = _body(request)
    email = str(data.get('email', '')).strip()
    session_id = str(data.get('session_id', ''))[:64]
    reference = str(data.get('reference', ''))
    if '@' not in email or len(email) > 254:
        return _json_error('Enter a valid email address.', '400', 400)
    try:
        pk = int(reference.removeprefix('TKT-'))
    except ValueError:
        return _json_error('Unknown ticket.', '404', 404)
    updated = Ticket.objects.filter(pk=pk, session_id=session_id, status=Ticket.OPEN).exclude(
        session_id='').update(email=email)
    if not updated:
        return _json_error('Unknown ticket.', '404', 404)
    return JsonResponse({'ok': True})


# ------------------------------------------------------------------ food lookup (third-party API)
@require_GET
def food_lookup(request):
    """GET /api/foods/?q=banana — per-100 g nutrition from Open Food Facts, or the built-in fallback."""
    if not request.user.is_authenticated:
        return _json_error('Sign in to look up foods.', '401', 401)
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return _json_error('Type at least 2 characters.', '400', 400)
    return JsonResponse(foods.search_foods(query))


# ------------------------------------------------------------------ error pages
def _error(request, status, template):
    try:
        return render(request, template, {'path': request.path}, status=status)
    except Exception:  # noqa: BLE001 - the error page itself must never fail
        return JsonResponse({'error': f'HTTP {status}'}, status=status)


def bad_request(request, exception=None):
    return _error(request, 400, '400.html')


def forbidden(request, exception=None):
    return _error(request, 403, '403.html')


def not_found(request, exception=None):
    return _error(request, 404, '404.html')


def server_error(request):
    return _error(request, 500, '500.html')
