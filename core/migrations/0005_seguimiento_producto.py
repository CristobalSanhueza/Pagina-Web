# Generated by Django 3.1.2 on 2023-06-21 22:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_remove_seguimiento_fecha_pago'),
    ]

    operations = [
        migrations.AddField(
            model_name='seguimiento',
            name='producto',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='core.producto'),
            preserve_default=False,
        ),
    ]