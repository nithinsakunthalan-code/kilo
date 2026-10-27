from django.db import migrations


def update(apps, schema_editor):
    ErrorCode = apps.get_model('support', 'ErrorCode')
    for row in ErrorCode.objects.filter(code='KILO-2001', meaning__contains='within 3 seconds'):
        row.meaning = row.meaning.replace('within 3 seconds', 'within 4 seconds')
        row.save(update_fields=['meaning'])


class Migration(migrations.Migration):
    dependencies = [('support', '0002_seed_content')]
    operations = [migrations.RunPython(update, migrations.RunPython.noop)]
