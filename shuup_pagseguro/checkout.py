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

from django.http.response import HttpResponse, HttpResponseBadRequest
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import TemplateView

from shuup.front.checkout import BasicServiceCheckoutPhaseProvider, CheckoutPhaseViewMixin
from shuup_pagseguro.constants import (
    PagSeguroBank, PagSeguroDebitBankMap, PagSeguroPaymentMethodIdentifier
)
from shuup_pagseguro.models import PagSeguroPaymentProcessor
from shuup_pagseguro.pagseguro import PagSeguro

logger = logging.getLogger(__name__)


class PagSeguroCheckoutPhase(CheckoutPhaseViewMixin, TemplateView):
    template_name = 'pagseguro/checkout.jinja'
    identifier = 'pagseguro'
    title = _('Payment information')

    def get_context_data(self, **kwargs):
        context = super(PagSeguroCheckoutPhase, self).get_context_data(**kwargs)
        context['ps_session_id'] = PagSeguro.create_from_config(self.request.shop.pagseguro_config).get_session_id()
        context['next_phase'] = self.next_phase
        context['payment_method'] = self.request.basket.payment_method
        context['current_bank_option'] = self.storage.get("bank_option")
        return context

    def post(self, request, *args, **kwargs):
        self.storage.reset()
        payment_method = request.POST.get('paymentMethod')

        # check for payment method
        if payment_method not in (PagSeguroPaymentMethodIdentifier.Boleto,
                                  PagSeguroPaymentMethodIdentifier.Debito):

            return HttpResponseBadRequest(_("Invalid payment method"))
        else:
            self.storage.set("payment_method", payment_method)

        # check for payment method
        if payment_method == PagSeguroPaymentMethodIdentifier.Debito:
            bank_name = PagSeguroDebitBankMap.get(request.POST.get('bankOption'))

            if bank_name not in PagSeguroBank.get_options():
                return HttpResponseBadRequest(_("Invalid bank option"))
            else:
                self.storage.set("bank_name", bank_name)
                self.storage.set("bank_option", request.POST['bankOption'])

        # check for sender hash
        sender_hash = request.POST.get('senderHash')
        if sender_hash:
            self.storage.set("sender_hash", sender_hash)
        else:
            return HttpResponseBadRequest(_("Invalid sender hash"))

        return HttpResponse()

    def is_valid(self):
        return self.storage.has_all(["payment_method", "sender_hash"])

    def process(self):
        self.request.basket.payment_data["pagseguro"] = {
            "payment_method": self.storage.get("payment_method"),
            "bank_name": self.storage.get("bank_name"),
            "sender_hash": self.storage.get("sender_hash"),
        }
        self.request.basket.save()


class PagSeguroCheckoutPhaseProvider(BasicServiceCheckoutPhaseProvider):
    '''
    Atribui a fase PagSeguroCheckoutPhase à forma de pagamento PagSeguroPaymentProcessor
    '''
    phase_class = PagSeguroCheckoutPhase
    service_provider_class = PagSeguroPaymentProcessor
