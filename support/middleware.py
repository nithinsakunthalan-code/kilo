import logging
import time
import uuid

logger = logging.getLogger('requests')

SKIP_PREFIXES = ('/static/',)


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '-')


class RequestLoggingMiddleware:
    """Logs one line per request: id, method, path, status, duration, user, client ip and user agent."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = uuid.uuid4().hex[:12]
        request.request_id = request_id
        start = time.perf_counter()
        status = 500
        try:
            response = self.get_response(request)
            status = response.status_code
            response['X-Request-ID'] = request_id
            return response
        finally:
            if not request.path.startswith(SKIP_PREFIXES):
                duration_ms = round((time.perf_counter() - start) * 1000, 1)
                user = getattr(request, 'user', None)
                username = user.get_username() if user is not None and user.is_authenticated else '-'
                level = logging.ERROR if status >= 500 else logging.WARNING if status >= 400 else logging.INFO
                logger.log(
                    level, 'id=%s method=%s path=%s status=%s duration_ms=%s user=%s ip=%s ua="%s"',
                    request_id, request.method, request.get_full_path(), status, duration_ms, username,
                    client_ip(request), request.META.get('HTTP_USER_AGENT', '-')[:120])
