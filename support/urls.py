from django.urls import path

from . import views

urlpatterns = [
    path('faq/', views.faq, name='faq'),
    path('errors/', views.error_codes, name='error_codes'),
    path('support/', views.contact, name='support'),
    path('health/', views.health, name='health'),
    path('api/chat/', views.chat, name='chat'),
    path('api/chat/feedback/', views.chat_feedback, name='chat-feedback'),
    path('api/chat/ticket-email/', views.chat_ticket_email, name='chat-ticket-email'),
    path('api/foods/', views.food_lookup, name='food-lookup'),
]
