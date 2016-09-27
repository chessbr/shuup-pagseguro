# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.

import logging

from django.core.urlresolvers import reverse
from django.http.response import HttpResponse
from django.shortcuts import redirect
from django.views.generic.base import View

from shuup_pagseguro.constants import PagSeguroTransactionStatus
from shuup_pagseguro.models import PagSeguroPayment
from shuup_pagseguro.notify_events import PagSeguroPaymentStatusChanged
from shuup_pagseguro.pagseguro import PagSeguro

logger = logging.getLogger(__name__)


class PagSeguroPaymentReturnView(View):
    def get(self, request, *args, **kwargs):
        return redirect(reverse("shuup:checkout", kwargs={"phase": "payment"}))


class PagSeguroNotificationView(View):

    def post(self, request):
        notification_code = request.POST.get('notificationCode')
        # notification_type = request.POST.get('notificationType')

        pagseguro = PagSeguro.create_from_config(request.shop.pagseguro_config)

        try:
            transaction_info = pagseguro.get_notification_info(notification_code)
            payment = PagSeguroPayment.objects.get(code=transaction_info['transaction']['code'])

            old_status = int(payment.data['transaction']['status'])
            new_status = int(transaction_info['transaction']['status'])

            payment.data.update(transaction_info)
            payment.save()

            # Alteração de estado!
            if new_status != old_status:

                # cancela o pedido se assim for necessário
                if new_status == PagSeguroTransactionStatus.Canceled.value and payment.order.can_set_canceled():
                    payment.order.set_canceled()

                # faz o pagamento do pedido
                elif new_status == PagSeguroTransactionStatus.Paid.value and payment.order.can_create_payment():
                    payment.order.create_payment(payment.order.get_total_unpaid_amount(), payment.code)

                # dispara evento para uso no Shuup Notify
                PagSeguroPaymentStatusChanged(
                    order=payment.order,
                    customer_email=payment.order.email,
                    customer_phone=payment.order.phone,
                    language=payment.order.language,
                    new_status=PagSeguroTransactionStatus(new_status),
                    old_status=PagSeguroTransactionStatus(old_status)
                ).run()

        except:
            logger.exception("PagSeguro notification exception")

        response = HttpResponse()
        response['Access-Control-Allow-Origin'] = 'https://sandbox.pagseguro.uol.com.br'
        return response
