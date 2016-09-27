# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.http.response import HttpResponse, HttpResponseBadRequest
from django.views.generic.base import TemplateView, View

import shuup_pagseguro
from shuup_pagseguro.models import PagSeguroPayment

TRANSACTION_DETAIL_TEMPLAE = 'pagseguro/admin/payment_detail.jinja'


class DashboardView(TemplateView):
    template_name = "pagseguro/admin/dashboard.jinja"
    title = "PagSeguro"

    def get_context_data(self, **kwargs):
        context_data = super(DashboardView, self).get_context_data(**kwargs)
        context_data.update({
            'VERSION': shuup_pagseguro.__version__,
            'payment_return_url': self.request.build_absolute_uri(reverse("shuup:pagseguro_payment_return")),
            'notification_url': self.request.build_absolute_uri(reverse("shuup:pagseguro_notification"))
        })
        return context_data


class PaymentRefreshView(View):
    ''' Atualiza as informações de um pagamento do PagSeguro '''

    def post(self, request, *args, **kwargs):
        try:
            payment = PagSeguroPayment.objects.get(pk=request.POST.get("pk"))
            payment.refresh()
            return HttpResponse()

        except Exception as exc:
            return HttpResponseBadRequest("{0}".format(exc))
