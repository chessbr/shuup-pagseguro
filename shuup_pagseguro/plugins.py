# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import unicode_literals

import logging

from django.core.urlresolvers import resolve, Resolver404
from django.utils.translation import ugettext_lazy as _

from shuup.core.models import Order
from shuup.xtheme.plugins._base import TemplatedPlugin
from shuup_pagseguro.constants import (
    PagSeguroPaymentMethod, PagSeguroPaymentMethodCode, PagSeguroTransactionCustomerStatus
)
from shuup_pagseguro.models import PagSeguroPayment

logger = logging.getLogger(__name__)


class PagSeguroPaymentPlugin(TemplatedPlugin):
    """
    Plugin para exibir informações do pagamento e botão para pagar
    """
    identifier = "shuup_pagseguro.pay_order"
    name = _("PagSeguro: informações e botão para efetuar o pagamento")
    template_name = "pagseguro/plugins/payment.jinja"

    def is_context_valid(self, context):
        context_data = super(PagSeguroPaymentPlugin, self).get_context_data(context)
        request = context_data["request"]

        try:
            resolved = resolve(request.path)
            return resolved.view_name in ('shuup:order_complete', 'shuup:show-order')
        except Resolver404:
            return False

    def get_context_data(self, context):
        context_data = super(PagSeguroPaymentPlugin, self).get_context_data(context)
        request = context_data["request"]
        resolved = resolve(request.path)

        if resolved.view_name == 'shuup:order_complete':
            order = Order.objects.get(pk=resolved.kwargs.get('pk'),
                                      key=resolved.kwargs.get('key'))

        # resolved.view_name == 'shuup:show-order':
        else:
            order = Order.objects.get(pk=resolved.kwargs.get('pk'))

        context_data.update({
            "PagSeguroTransactionCustomerStatus": PagSeguroTransactionCustomerStatus,
            "PagSeguroPaymentMethodCode": PagSeguroPaymentMethodCode,
            "order": order,
            "is_boleto": (order.payment_method.choice_identifier == PagSeguroPaymentMethod.BOLETO.value)
        })

        try:
            context_data["payment"] = PagSeguroPayment.objects.get(code=order.payment_data["pagseguro"]["code"])
        except:
            logger.exception("PagSeguro plugin exception")

        return context_data
