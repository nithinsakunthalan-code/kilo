from django.contrib import admin

from .models import FAQ, ErrorCode, Ticket


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'position', 'is_published')
    list_filter = ('category', 'is_published')
    search_fields = ('question', 'answer', 'keywords')


@admin.register(ErrorCode)
class ErrorCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'http_status')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('reference', 'status', 'source', 'user', 'email', 'created')
    list_filter = ('status', 'source')
    search_fields = ('question', 'email', 'session_id', 'user__username')
