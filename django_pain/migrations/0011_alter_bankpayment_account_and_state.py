# Generated by Django 2.0.7 on 2018-08-09 05:57

from django.db import migrations, models
import django.db.models.deletion
import django_pain.constants


class Migration(migrations.Migration):

    dependencies = [
        ('django_pain', '0010_verbose_names'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bankpayment',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='django_pain.BankAccount', verbose_name='Destination account'),
        ),
        migrations.AlterField(
            model_name='bankpayment',
            name='state',
            field=models.TextField(choices=[(django_pain.constants.PaymentState('imported'), 'imported'), (django_pain.constants.PaymentState('processed'), 'processed'), (django_pain.constants.PaymentState('deferred'), 'not identified'), (django_pain.constants.PaymentState('exported'), 'exported')], default=django_pain.constants.PaymentState('imported'), verbose_name='Payment state'),
        ),
    ]
