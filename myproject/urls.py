from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('support.urls')),
    path('', include('myapp.urls')),
]

handler400 = 'support.views.bad_request'
handler403 = 'support.views.forbidden'
handler404 = 'support.views.not_found'
handler500 = 'support.views.server_error'
