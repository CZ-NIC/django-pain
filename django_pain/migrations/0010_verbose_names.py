# Generated by Django 2.0.7 on 2018-08-07 04:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('django_pain', '0009_bankpayment_add_processor_and_objective'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bankaccount',
            options={'verbose_name': 'Bank account', 'verbose_name_plural': 'Bank accounts'},
        ),
        migrations.AlterModelOptions(
            name='bankpayment',
            options={'verbose_name': 'Bank payment', 'verbose_name_plural': 'Bank payments'},
        ),
    ]
