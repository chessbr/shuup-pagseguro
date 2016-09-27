# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
from django.core.urlresolvers import reverse
from mock import patch
import pytest
import xmltodict

from shuup.core.models._orders import Order, OrderStatusRole, PaymentStatus
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
def test_views(rf):
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

    transaction_code = "38490248UEHBU90-2342-324502221-442"

    confirm_soup = c.soup(confirm_path)
    c.post(confirm_path, data=extract_form_fields(confirm_soup))
    order = Order.objects.filter(payment_method=payment_method).first()
    payment = PagSeguroPayment.objects.create(order=order, code=transaction_code, data={
        "transaction": {
            "status": "1"
        }
    })
    payment.save()
    order.payment_data['pagseguro']['code'] = payment.code
    order.save()


    # Verifica: pagseguro_payment_return
    response = c.get(reverse("shuup:pagseguro_payment_return"))
    assert response.status_code == 302
    assert reverse("shuup:checkout", kwargs={"phase": "payment"}) in response.url


    notify_path = reverse("shuup:pagseguro_notification")

    # Erro: notificationCode nao informado
    response = c.post(notify_path)
    assert response.status_code == 200
    assert len(response.content.decode("utf-8")) == 0
    assert response["Access-Control-Allow-Origin"] == 'https://sandbox.pagseguro.uol.com.br'


    # Sucesso 1
    transaction_info = xmltodict.parse("""
        <?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>
        <transaction>
            <status>2</status>
            <code>{0}</code>
        </transaction>
    """.format(transaction_code).strip())

    # altera retorno do get_notification_info
    with patch.object(PagSeguro, 'get_notification_info', return_value=transaction_info):
        response = c.post(notify_path, {"notificationCode": "it-does-not-mattter"})
        assert response.status_code == 200
        assert response["Access-Control-Allow-Origin"] == 'https://sandbox.pagseguro.uol.com.br'

        payment.refresh_from_db()
        order.refresh_from_db()
        assert payment.data['transaction']['status'] == "2"
        assert payment.data['transaction']['code'] == transaction_code
        assert order.payment_status == PaymentStatus.NOT_PAID


    # Sucesso 2 - PAGO, emite notificacao e bota o pedido como pago
    transaction_info = xmltodict.parse("""
        <?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>
        <transaction>
            <status>3</status>
            <code>{0}</code>
        </transaction>
    """.format(transaction_code).strip())
    with patch.object(PagSeguro, 'get_notification_info', return_value=transaction_info):
        response = c.post(notify_path, {"notificationCode": "it-does-not-mattter"})
        assert response.status_code == 200

        payment.refresh_from_db()
        order.refresh_from_db()

        assert payment.data['transaction']['status'] == "3"
        assert order.payment_status == PaymentStatus.FULLY_PAID


    # volta o pedido ao estado de não pago
    order.payment_status = PaymentStatus.NOT_PAID
    order.save()

    # Sucesso 3 - CANCELADO, emite notificacao e bota o pedido como cancelado
    transaction_info = xmltodict.parse("""
        <?xml version="1.0" encoding="ISO-8859-1" standalone="yes"?>
        <transaction>
            <status>7</status>
            <code>{0}</code>
        </transaction>
    """.format(transaction_code).strip())
    with patch.object(PagSeguro, 'get_notification_info', return_value=transaction_info):
        response = c.post(notify_path, {"notificationCode": "it-does-not-mattter"})
        assert response.status_code == 200

        payment.refresh_from_db()
        order.refresh_from_db()

        assert payment.data['transaction']['status'] == "7"
        assert order.status.role == OrderStatusRole.CANCELED
