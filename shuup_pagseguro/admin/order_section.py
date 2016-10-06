# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.

import iso8601

from shuup.admin.base import Section
from shuup_pagseguro.constants import PagSeguroPaymentMethodCode, PagSeguroTransactionStatus
from shuup_pagseguro.models import PagSeguroPayment, PagSeguroPaymentProcessor


class PagSeguroOrderSection(Section):
    identifier = 'pagseguro'
    name = 'PagSeguro'
    icon = 'fa-dollar'
    template = 'pagseguro/admin/order_section.jinja'
    extra_js = 'pagseguro/admin/order_section_extra_js.jinja'
    order = 10

    @staticmethod
    def visible_for_object(order):
        return isinstance(order.payment_method.payment_processor, PagSeguroPaymentProcessor)

    @staticmethod
    def get_context_data(order):
        return {
            'order': order,
            'payments': PagSeguroPayment.objects.filter(order=order).order_by('id'),

            # utils
            'PagSeguroTransactionStatus': PagSeguroTransactionStatus,
            'PagSeguroPaymentMethodCode': PagSeguroPaymentMethodCode,
            'iso8601': iso8601
        }
