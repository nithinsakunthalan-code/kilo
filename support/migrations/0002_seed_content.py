from django.db import migrations

from support.seed_data import ERROR_CODES, FAQS


def load(apps, schema_editor):
    FAQ = apps.get_model('support', 'FAQ')
    ErrorCode = apps.get_model('support', 'ErrorCode')
    for position, (category, question, answer, keywords) in enumerate(FAQS, start=1):
        FAQ.objects.get_or_create(
            question=question,
            defaults={'category': category, 'answer': answer, 'keywords': keywords, 'position': position})
    for code, status, title, meaning, fix, position in ERROR_CODES:
        ErrorCode.objects.get_or_create(
            code=code,
            defaults={'http_status': status, 'title': title, 'meaning': meaning,
                      'how_to_fix': fix, 'position': position})


def unload(apps, schema_editor):
    apps.get_model('support', 'FAQ').objects.filter(question__in=[f[1] for f in FAQS]).delete()
    apps.get_model('support', 'ErrorCode').objects.filter(code__in=[e[0] for e in ERROR_CODES]).delete()


class Migration(migrations.Migration):
    dependencies = [('support', '0001_initial')]
    operations = [migrations.RunPython(load, unload)]
