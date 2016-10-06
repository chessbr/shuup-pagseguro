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

from django.db import models
from django.shortcuts import redirect
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from jsonfield.fields import JSONField

from shuup.core.models._orders import Order
from shuup.core.models._service_base import ServiceChoice
from shuup.core.models._service_payment import PaymentProcessor
from shuup.core.models._shops import Shop
from shuup_pagseguro.constants import PagSeguroPaymentMethod
from shuup_pagseguro.pagseguro import PagSeguro
from six.moves import urllib

logger = logging.getLogger(__name__)


class PagSeguroPaymentProcessor(PaymentProcessor):

    class Meta:
        verbose_name = _('PagSeguro')
        verbose_name_plural = _('PagSeguro')

    def get_service_choices(self):
        return [
            ServiceChoice(PagSeguroPaymentMethod.BOLETO.value, PagSeguroPaymentMethod.BOLETO),
            ServiceChoice(PagSeguroPaymentMethod.ONLINE_DEBIT.value, PagSeguroPaymentMethod.ONLINE_DEBIT),
        ]

    def get_payment_process_response(self, service, order, urls):
        """
        Get payment process response for given order.

        :type service: shuup.core.models.PaymentMethod
        :type order: shuup.core.models.Order
        :type urls: PaymentUrls
        :rtype: django.http.HttpResponse|None
        """

        pagseguro = PagSeguro.create_from_config(order.shop.pagseguro_config)

        try:
            result = pagseguro.pay(service, order)

            if result.error:
                logger.error("PagSeguro Payment Request Errors: {0}", result.errors)
                order.add_log_entry("PagSeguro Error: {0}".format(result.errors))
                return redirect(urls.cancel_url)

            else:
                payment, __ = PagSeguroPayment.objects.get_or_create(order=order, code=result.code)
                payment.data = result._data
                payment.save()

                # salva os dados adicionais da transação do pagseguro
                order.payment_data["pagseguro"].update({
                    "payment_link": result.payment_link,
                    "code": result.code,
                    "_data": result._data,
                })
                order.save()
                return redirect(urls.return_url)

        except:
            logger.exception("PagSeguro Payment Request Exception")
            params = ("?" + urllib.parse.urlencode({"problem": _("Internal error")}))
            return redirect(urls.cancel_url + params)

    def process_payment_return_request(self, service, order, request):
        pass


@python_2_unicode_compatible
class PagSeguroPayment(models.Model):
    order = models.ForeignKey(Order, verbose_name=_("order"))
    code = models.CharField(verbose_name=_("code"), max_length=32)
    last_update = models.DateTimeField(verbose_name=_("last update"), auto_now=True)
    data = JSONField(blank=True, null=True, verbose_name=_('pagseguro data'))

    class Meta:
        verbose_name = _('PagSeguro payments')
        verbose_name_plural = _('PagSeguro payments')

    def __str__(self):
        return "PagSeguroPayment {0} for Order {1}".format(self.code, self.order)

    def refresh(self):
        pagseguro = PagSeguro.create_from_config(self.order.shop.pagseguro_config)
        self.data = pagseguro.get_transaction_info(self.code)
        self.save()


class PagSeguroConfig(models.Model):
    shop = models.OneToOneField(Shop, verbose_name=_("Shop"), related_name="pagseguro_config")

    email = models.EmailField(verbose_name=_("account email"))
    token = models.CharField(verbose_name=_("account token"), max_length=32)

    sandbox = models.BooleanField(_('Sandbox mode'),
                                  default=False,
                                  help_text=_('Enable this to activate Developer mode (testing).'))

    class Meta:
        verbose_name = _('PagSeguro configuration')
        verbose_name_plural = _('PagSeguro configurations')

    def __str__(self):  # pragma: no cover
        return _('PagSeguro Configuration for {0}').format(self.shop)
