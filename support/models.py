from django.conf import settings
from django.db import models


class FAQ(models.Model):
    """Frequently asked question. Shown on /faq/ and used by the assistant as its knowledge base."""

    question = models.CharField(max_length=200)
    answer = models.TextField()
    keywords = models.CharField(
        max_length=200, blank=True, help_text='Comma-separated extra words that should match this FAQ.')
    category = models.CharField(max_length=40, default='General')
    position = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'position', 'id']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question


class ErrorCode(models.Model):
    """Explanation of an HTTP status or a KILO-specific error code."""

    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=80)
    meaning = models.TextField()
    how_to_fix = models.TextField()
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['position', 'code']

    def __str__(self):
        return f'{self.code} {self.title}'


class Ticket(models.Model):
    """Support ticket. Created by the assistant when it cannot answer, or by the support form."""

    CHAT, FORM = 'chat', 'form'
    SOURCES = [(CHAT, 'Chat assistant'), (FORM, 'Support form')]
    OPEN, CLOSED = 'open', 'closed'
    STATUSES = [(OPEN, 'Open'), (CLOSED, 'Closed')]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='tickets')
    question = models.TextField()
    email = models.EmailField(blank=True)
    source = models.CharField(max_length=10, choices=SOURCES, default=CHAT)
    session_id = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(max_length=10, choices=STATUSES, default=OPEN)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    @property
    def reference(self):
        return f'TKT-{self.pk:05d}' if self.pk else ''

    def __str__(self):
        return f'{self.reference} ({self.get_status_display()})'
