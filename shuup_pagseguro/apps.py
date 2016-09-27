# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.


from shuup.apps import AppConfig


class ShuupPagSeguroAppConfig(AppConfig):
    name = "shuup_pagseguro"
    verbose_name = "Shuup PagSeguro"
    provides = {
        "service_provider_admin_form": [
            "shuup_pagseguro.admin.forms:PagSeguroPaymentProcessorForm"
        ],
        "front_urls_pre": [
            "shuup_pagseguro.urls:urlpatterns"
        ],
        "admin_order_section": [
             "shuup_pagseguro.admin.order_section:PagSeguroOrderSection"
        ],
        "admin_module": [
            "shuup_pagseguro.admin:PagSeguroModule",
            "shuup_pagseguro.admin:PagSeguroConfigModule"
        ],
        "front_service_checkout_phase_provider": [
            "shuup_pagseguro.checkout:PagSeguroCheckoutPhaseProvider"
        ],
        "xtheme_plugin": [
            "shuup_pagseguro.plugins:PagSeguroPaymentPlugin"
        ],
        "notify_event": [
            "shuup_pagseguro.notify_events:PagSeguroPaymentStatusChanged",
        ]
    }
