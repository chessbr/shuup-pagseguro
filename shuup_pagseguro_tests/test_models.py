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
from mock import patch
import pytest
import xmltodict

from shuup.core.models._orders import Order
from shuup.testing.factories import (
    get_default_product, get_default_shipping_method, get_default_shop, get_default_supplier,
    get_default_tax_class
)
from shuup.testing.soup_utils import extract_form_fields
from shuup_pagseguro.constants import (
    PagSeguroPaymentMethod, PagSeguroPaymentMethodCode, PagSeguroPaymentMethodIdentifier
)
from shuup_pagseguro.models import PagSeguroPayment
from shuup_pagseguro.pagseguro import PagSeguro
from shuup_pagseguro_tests.utils import get_payment_provider, initialize, patch_pagseguro
from shuup_tests.front.test_checkout_flow import fill_address_inputs
from shuup_tests.utils import SmartClient


def setup_module():
    patch_pagseguro()

def teardown_module():
    patch.stopall()


@pytest.mark.django_db
def test_payment_refresh():
    """ Testa pagamentos """

    initialize()
    c = SmartClient()
    default_product = get_default_product()
    basket_path = reverse("shuup:basket")
    c.post(basket_path, data={
        "command": "add",
        "product_id": default_product.pk,
        "quantity": 1,
        "supplier": get_default_supplier().pk
    })

    shipping_method = get_default_shipping_method()
    processor = get_payment_provider()
    payment_method = processor.create_service(
        PagSeguroPaymentMethod.ONLINE_DEBIT.value,
        identifier="pagseguro_debit",
        shop=get_default_shop(),
        name="debit",
        enabled=True,
        tax_class=get_default_tax_class()
    )

    service_choices = processor.get_service_choices()
    assert len(service_choices) == 2
    assert service_choices[0].identifier == PagSeguroPaymentMethod.BOLETO.value
    assert service_choices[1].identifier == PagSeguroPaymentMethod.ONLINE_DEBIT.value

    addresses_path = reverse("shuup:checkout", kwargs={"phase": "addresses"})
    methods_path = reverse("shuup:checkout", kwargs={"phase": "methods"})
    payment_path = reverse("shuup:checkout", kwargs={"phase": "payment"})
    confirm_path = reverse("shuup:checkout", kwargs={"phase": "confirm"})

    addresses_soup = c.soup(addresses_path)
    inputs = fill_address_inputs(addresses_soup, with_company=False)
    c.post(addresses_path, data=inputs)
    c.post(methods_path, data={
        "payment_method": payment_method.pk,
        "shipping_method": shipping_method.pk
    })
    c.get(confirm_path)
    c.soup(payment_path)
    c.post(payment_path, {
        "paymentMethod": PagSeguroPaymentMethodIdentifier.Debito,
        "bankOption": "{0}".format(PagSeguroPaymentMethodCode.DebitoOnlineBB.value),
        "senderHash": "J7E98Y37WEIRUHDIAI9U8RYE7UQE"
    })

    confirm_soup = c.soup(confirm_path)
    c.post(confirm_path, data=extract_form_fields(confirm_soup))
    order = Order.objects.filter(payment_method=payment_method).first()
    process_payment_path = reverse("shuup:order_process_payment", kwargs={"pk": order.pk, "key": order.key})
    process_payment_return_path = reverse("shuup:order_process_payment_return",kwargs={"pk": order.pk, "key": order.key})
    order_complete_path = reverse("shuup:order_complete",kwargs={"pk": order.pk, "key": order.key})

    c.get(process_payment_path)
    c.get(process_payment_return_path)
    c.get(order_complete_path)

    # testa o refresh do pagamento
    payment = PagSeguroPayment.objects.get(order=order)

    transaction_info = xmltodict.parse("""
        <?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>
        <transaction>
            <status>2</status>
        </transaction>
    """.strip())

    # altera o estado da transacao
    with patch.object(PagSeguro, 'get_transaction_info', return_value=transaction_info):
        assert payment.data['transaction']['status'] == "3"
        payment.refresh()
        assert payment.data['transaction']['status'] == "2"

    # format string
    "{0}".format(payment)
