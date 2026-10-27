from django.db import migrations

from support.seed_data import FAQS

NEW_QUESTION = 'Can the assistant make me a diet plan?'
CAPABILITIES_QUESTION = 'What can the KILO assistant do?'


def add(apps, schema_editor):
    FAQ = apps.get_model('support', 'FAQ')
    for position, (category, question, answer, keywords) in enumerate(FAQS, start=1):
        if question == NEW_QUESTION:
            FAQ.objects.get_or_create(
                question=question,
                defaults={'category': category, 'answer': answer, 'keywords': keywords, 'position': position})
        elif question == CAPABILITIES_QUESTION:       # refresh the wording now that the coach exists
            FAQ.objects.filter(question=question).update(answer=answer)


class Migration(migrations.Migration):
    dependencies = [('support', '0003_update_food_timeout_text')]
    operations = [migrations.RunPython(add, migrations.RunPython.noop)]
