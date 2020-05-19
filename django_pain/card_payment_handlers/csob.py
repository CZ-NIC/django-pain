#
# Copyright (C) 2020  CZ.NIC, z. s. p. o.
#
# This file is part of FRED.
#
# FRED is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# FRED is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with FRED.  If not, see <https://www.gnu.org/licenses/>.

"""Card handler for CSOB Gateway."""
from typing import Dict, List, Tuple

from django.utils import timezone
from djmoney.money import Money
from pycsob import conf as CSOB
from pycsob.client import CsobClient
from pycsob.utils import CsobVerifyError

from django_pain.card_payment_handlers.common import AbstractCardPaymentHandler, CartItem
from django_pain.constants import PaymentState, PaymentType
from django_pain.models import BankAccount, BankPayment
from django_pain.settings import SETTINGS


class CsobGateError(CsobVerifyError):
    """CSOB payment gate exception."""


CSOB_GATEWAY_TO_PAYMENT_STATE_MAPPING = {
    CSOB.PAYMENT_STATUS_INIT: PaymentState.INITIALIZED,
    CSOB.PAYMENT_STATUS_PROCESS: PaymentState.INITIALIZED,
    CSOB.PAYMENT_STATUS_CANCELLED: PaymentState.CANCELED,
    CSOB.PAYMENT_STATUS_CONFIRMED: PaymentState.READY_TO_PROCESS,
    CSOB.PAYMENT_STATUS_REVERSED: PaymentState.CANCELED,
    CSOB.PAYMENT_STATUS_REJECTED: PaymentState.CANCELED,
    CSOB.PAYMENT_STATUS_WAITING: PaymentState.READY_TO_PROCESS,
    CSOB.PAYMENT_STATUS_RECOGNIZED: PaymentState.READY_TO_PROCESS,
    CSOB.PAYMENT_STATUS_RETURN_WAITING: PaymentState.CANCELED,
    CSOB.PAYMENT_STATUS_RETURNED: PaymentState.CANCELED,
}


class CSOBCardPaymentHandler(AbstractCardPaymentHandler):
    """CSOB Gateway card payment processor."""

    def __init__(self, name):
        super().__init__(name)
        self._client = None

    @property
    def client(self):
        """Get CSOB Gateway Client."""
        if self._client is None:
            self._client = CsobClient(
                SETTINGS.csob_card_merchant_id,
                SETTINGS.csob_card_api_url,
                SETTINGS.csob_card_merchant_private_key,
                SETTINGS.csob_card_api_public_key
            )
        return self._client

    def init_payment(self, amount: Money, variable_symbol: str, processor: str, return_url: str,
                     return_method: str, cart: List[CartItem], language: str) -> Tuple[BankPayment, str]:
        """Initialize card payment on the CSOB gateway, see parent class for detailed description."""
        dict_cart = []  # type: List[Dict]
        for item in cart:
            dict_item = item._asdict()
            # CSOB Gateway works with multiples of 100 of basic currency:
            dict_item['amount'] = int(dict_item['amount'] * 100)
            dict_cart.append(dict_item)

        # Init payment on CSOB Gateway
        response = self.client.payment_init(
            variable_symbol, int(amount * 100), return_url, description='Dummy value',
            cart=dict_cart, return_method=return_method, language=language,
            # logo_version=PAYMENTS_SETTINGS.PAYMENTS_CSOB_LOGO_VERSION,
            # color_scheme_version=PAYMENTS_SETTINGS.PAYMENTS_CSOB_COLOR_SCHEME_VERSION, merchant_data=merchant_data
        )
        data = self.client.gateway_return(response.json())
        if data['resultCode'] != CSOB.RETURN_CODE_OK:
            raise CsobGateError('init resultCode != OK', data)
        if data['paymentStatus'] != CSOB.PAYMENT_STATUS_INIT:
            raise CsobGateError('paymentStatus != PAYMENT_STATUS_INIT', data)

        redirect_url = self.client.get_payment_process_url(data['payId'])

        account = BankAccount.objects.get(account_name=SETTINGS.csob_card_account_name)
        payment = BankPayment.objects.create(
            identifier=data['payId'],
            payment_type=PaymentType.CARD_PAYMENT,
            account=account,
            transaction_date=timezone.now(),
            amount=amount,
            description=cart[0].name,
            state=PaymentState.INITIALIZED,
            card_payment_state=CSOB.PAYMENT_STATUSES[data['paymentStatus']],
            variable_symbol=variable_symbol,
            processor=processor,
            card_handler=self.name
        )
        return payment, redirect_url

    def update_payments_state(self, payment: BankPayment) -> None:
        """Update status of the payment form CSOB Gateway and if newly paid, process the payment."""
        gateway_result = self.client.payment_status(payment.identifier).payload
        payment.card_payment_state = CSOB.PAYMENT_STATUSES[gateway_result['paymentStatus']]
        payment.state = CSOB_GATEWAY_TO_PAYMENT_STATE_MAPPING[gateway_result['paymentStatus']]
        payment.save()
