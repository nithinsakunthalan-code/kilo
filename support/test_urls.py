"""URLconf used only by tests: adds a view that crashes so the custom 500 page can be exercised."""
from django.urls import path

from myproject.urls import (  # noqa: F401
    handler400, handler403, handler404, handler500, urlpatterns as base_patterns,
)


def boom(request):
    raise RuntimeError('deliberate test failure')


urlpatterns = [path('boom/', boom)] + list(base_patterns)
