# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.

from mock import patch
import xmltodict

from shuup.core.defaults.order_statuses import create_default_order_statuses
from shuup.core.models._product_shops import ShopProduct
from shuup.testing.factories import _get_service_provider, get_default_product, get_default_shop
from shuup.testing.mock_population import populate_if_required
from shuup.xtheme._theme import set_current_theme
from shuup_pagseguro.models import PagSeguroConfig, PagSeguroPaymentProcessor
from shuup_pagseguro.pagseguro import PagSeguro, PagSeguroPaymentResult
from shuup_pagseguro_tests import PRODUCT_PRICE, SESSION_XML, TRANSACTION_XML

session_patcher = patch.object(PagSeguro, 'get_session_id', return_value=xmltodict.parse(SESSION_XML)['session']['id'])
notification_patcher = patch.object(PagSeguro, 'get_notification_info', return_value=xmltodict.parse(TRANSACTION_XML))
transaction_patcher = patch.object(PagSeguro, 'get_transaction_info', return_value=xmltodict.parse(TRANSACTION_XML))
pay_patcher = patch.object(PagSeguro, 'pay', return_value=PagSeguroPaymentResult(xmltodict.parse(TRANSACTION_XML)))


def get_payment_provider(**kwargs):
    return _get_service_provider(PagSeguroPaymentProcessor)

def get_pagseguro_config(**kwargs):
    return PagSeguroConfig.objects.get_or_create(shop=get_default_shop(), **kwargs)[0]

def initialize():
    get_default_shop()
    get_pagseguro_config()
    set_current_theme('shuup.themes.classic_gray')
    create_default_order_statuses()
    populate_if_required()

    default_product = get_default_product()
    sp = ShopProduct.objects.get(product=default_product, shop=get_default_shop())
    sp.default_price = get_default_shop().create_price(PRODUCT_PRICE)
    sp.save()

def patch_pagseguro():
    session_patcher.start()
    notification_patcher.start()
    transaction_patcher.start()
    pay_patcher.start()
