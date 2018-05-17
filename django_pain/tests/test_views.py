from django.test import TestCase, override_settings
from django.urls import reverse

from django_pain.models import BankAccount
from django_pain.tests.utils import get_payment


@override_settings(ROOT_URLCONF='django_pain.urls')
class TestPaymentListView(TestCase):

    def test_empty(self):
        result = self.client.get(reverse('payments-list'))
        self.assertQuerysetEqual(result.context['payments'], [])

    def test_not_empty(self):
        account = BankAccount(account_number='123456789/0123', currency='CZK')
        account.save()
        payment1 = get_payment(identifier='PAYMENT_1', account=account)
        payment1.save()
        payment2 = get_payment(identifier='PAYMENT_2', account=account)
        payment2.save()

        result = self.client.get(reverse('payments-list'))
        self.assertQuerysetEqual(result.context['payments'].values_list(
            'identifier', 'account', 'counter_account_number', 'transaction_date'
        ), [
            (payment1.identifier, payment1.account.pk, payment1.counter_account_number, payment1.transaction_date),
            (payment2.identifier, payment2.account.pk, payment2.counter_account_number, payment2.transaction_date),
        ], transform=tuple, ordered=False)
