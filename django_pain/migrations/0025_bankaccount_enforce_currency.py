# Generated by Django 2.2.20 on 2021-11-25 11:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_pain', '0024_empty_counteraccount'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankaccount',
            name='enforce_currency',
            field=models.BooleanField(default=True, verbose_name='Enforce currency check'),
        ),
    ]
