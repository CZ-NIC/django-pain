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

"""REST API module."""
import logging
from copy import deepcopy

from rest_framework import mixins, routers, status, viewsets
from rest_framework.response import Response

from django_pain.card_payment_handlers import PaymentHandlerConnectionError
from django_pain.constants import PaymentState, PaymentType
from django_pain.models import BankPayment
from django_pain.serializers import BankPaymentSerializer
from django_pain.settings import get_card_payment_handler_instance, get_processor_instance

LOGGER = logging.getLogger(__name__)


class BankPaymentViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """BankPayment API for create and retrieve."""

    queryset = BankPayment.objects.filter(payment_type=PaymentType.CARD_PAYMENT).select_for_update()
    serializer_class = BankPaymentSerializer
    lookup_field = 'uuid'

    def _process_payment(self, payment):
        processor = get_processor_instance(payment.processor)
        LOGGER.info('Processing card payment with processor %s.', processor)
        result = list(processor.process_payments([deepcopy(payment)]))[0]
        if result.result:
            payment.state = PaymentState.PROCESSED
        else:
            LOGGER.info('Saving payment %s as DEFERRED with error %s.', payment.uuid, result.error)
            payment.state = PaymentState.DEFERRED
        payment.processing_error = result.error
        payment.save()

    def retrieve(self, request, *args, **kwargs):
        """Update payment state and return update payment."""
        payment = self.get_object()
        old_payment_state = payment.state

        card_payment_handler = get_card_payment_handler_instance(payment.card_handler)
        try:
            card_payment_handler.update_payments_state(payment)
        except PaymentHandlerConnectionError:
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if old_payment_state == PaymentState.INITIALIZED and payment.state == PaymentState.READY_TO_PROCESS:
            self._process_payment(payment)

        serializer = BankPaymentSerializer(payment)
        return Response(serializer.data)


ROUTER = routers.DefaultRouter()
ROUTER.register(r'bankpayment', BankPaymentViewSet)
