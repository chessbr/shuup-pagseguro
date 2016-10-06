# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.

from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt

from shuup_pagseguro.views import PagSeguroNotificationView, PagSeguroPaymentReturnView

urlpatterns = patterns(
    '',
    url(r'^checkout/pagseguro/return/$',
        csrf_exempt(PagSeguroPaymentReturnView.as_view()),
        name='pagseguro_payment_return'),

    url(r'^pagseguro/notify/$',
        csrf_exempt(PagSeguroNotificationView.as_view()),
        name='pagseguro_notification'),
)
