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

"""Serializers for REST API."""
from enum import Enum, unique

from rest_framework import serializers

from django_pain.card_payment_handlers import CartItem
from django_pain.constants import PaymentState
from django_pain.models import BankPayment
from django_pain.settings import get_card_payment_handler_instance


@unique
class ExternalPaymentState(str, Enum):
    """Card Payment state used by REST API."""

    INITIALIZED = 'initialized'
    PAID = 'paid'
    CANCELED = 'canceled'


CARD_PAYMENT_STATE_MAPPING = {
    PaymentState.INITIALIZED: ExternalPaymentState.INITIALIZED,
    PaymentState.READY_TO_PROCESS: ExternalPaymentState.PAID,
    PaymentState.PROCESSED: ExternalPaymentState.PAID,
    PaymentState.DEFERRED: ExternalPaymentState.PAID,
    PaymentState.EXPORTED: ExternalPaymentState.PAID,
    PaymentState.CANCELED: ExternalPaymentState.CANCELED,
}


class BankPaymentSerializer(serializers.ModelSerializer):
    """Serializer for BankPayment."""

    return_url = serializers.URLField(write_only=True)
    return_method = serializers.ChoiceField(choices=('GET', 'POST'), write_only=True)
    cart = serializers.JSONField(write_only=True, required=True)
    language = serializers.CharField(write_only=True)
    identifier = serializers.CharField(read_only=True)
    state = serializers.SerializerMethodField(read_only=True)
    gateway_redirect_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = BankPayment
        fields = ['uuid', 'identifier', 'amount', 'variable_symbol', 'processor', 'card_handler',
                  'return_url', 'return_method', 'cart', 'language',
                  'gateway_redirect_url', 'state']

    def __init__(self, *args, **kwargs):
        self.gateway_redirect_url = None
        super().__init__(*args, **kwargs)

    def get_state(self, obj):
        """Get simple state for REST API from BankPayment state attribute."""
        return CARD_PAYMENT_STATE_MAPPING[obj.state]

    def get_gateway_redirect_url(self, obj):
        """Get redriect URL of the payment gateway."""
        return self.gateway_redirect_url

    def validate_cart(self, value):
        """Validate cart is properly set."""
        if not (1 <= len(value) <= 2):
            raise serializers.ValidationError('`cart` must have one or two item(s)!')
        cart_items = []
        for item in value:
            if len(item['name']) > 20:
                raise serializers.ValidationError('`cartitem/name` must not exceede 20 characters!')
            cart_item = CartItem(**item)
            cart_items.append(cart_item)
        return cart_items

    def validate(self, data):
        """Overall checks thoughout the fields."""
        cart_total_amount = sum((item.amount * item.quantity for item in data['cart']))
        if cart_total_amount != data['amount']:
            raise serializers.ValidationError('Sum of `cart` items amounts must be equal to payments `amount`')
        return data

    def create(self, validated_data):
        """Create the payment using initialization of its CardHandler."""
        card_handler = get_card_payment_handler_instance(validated_data.pop('card_handler'))
        payment, self.gateway_redirect_url = card_handler.init_payment(**validated_data)
        return payment
