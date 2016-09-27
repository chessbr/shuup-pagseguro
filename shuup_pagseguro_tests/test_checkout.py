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
from shuup_pagseguro.models import PagSeguroPaymentProcessor
from shuup_pagseguro.pagseguro import PagSeguro, PagSeguroException, PagSeguroPaymentResult
from shuup_pagseguro_tests import ERROR_XML
from shuup_pagseguro_tests.utils import get_payment_provider, initialize, patch_pagseguro
from shuup_tests.front.test_checkout_flow import fill_address_inputs
from shuup_tests.utils import SmartClient


def setup_module():
    patch_pagseguro()

def teardown_module():
    patch.stopall()


@pytest.mark.django_db
def test_checkout_boleto_success():
    """ Transação com Boleto com sucesso """
    initialize()

    c = SmartClient()
    default_product = get_default_product()

    basket_path = reverse("shuup:basket")
    add_to_basket_resp = c.post(basket_path, data={
        "command": "add",
        "product_id": default_product.pk,
        "quantity": 1,
        "supplier": get_default_supplier().pk
    })
    assert add_to_basket_resp.status_code < 400

    # Create methods
    shipping_method = get_default_shipping_method()
    processor = get_payment_provider()
    assert isinstance(processor, PagSeguroPaymentProcessor)

    payment_method = processor.create_service(
        PagSeguroPaymentMethod.BOLETO.value,
        identifier="pagseguro_boleto",
        shop=get_default_shop(),
        name="boleto",
        enabled=True,
        tax_class=get_default_tax_class())

    # Resolve paths
    addresses_path = reverse("shuup:checkout", kwargs={"phase": "addresses"})
    methods_path = reverse("shuup:checkout", kwargs={"phase": "methods"})
    payment_path = reverse("shuup:checkout", kwargs={"phase": "payment"})
    confirm_path = reverse("shuup:checkout", kwargs={"phase": "confirm"})


    # Phase: Addresses
    addresses_soup = c.soup(addresses_path)
    inputs = fill_address_inputs(addresses_soup, with_company=False)
    response = c.post(addresses_path, data=inputs)
    assert response.status_code == 302, "Address phase should redirect forth"
    assert response.url.endswith(methods_path)

    # Phase: Methods
    assert Order.objects.filter(payment_method=payment_method).count() == 0
    response = c.post(
        methods_path,
        data={
            "payment_method": payment_method.pk,
            "shipping_method": shipping_method.pk
        }
    )

    assert response.status_code == 302, "Methods phase should redirect forth"
    assert response.url.endswith(confirm_path)
    response = c.get(confirm_path)
    assert response.status_code == 302, "Confirm should first redirect forth"
    assert response.url.endswith(payment_path)

    # Phase: Payment
    response = c.soup(payment_path)
    response = c.post(payment_path, {
        "paymentMethod": PagSeguroPaymentMethodIdentifier.Boleto,
        "senderHash": "J7E98Y37WEIRUHDIAI9U8RYE7UQE"
    })
    assert response.status_code == 200

    confirm_soup = c.soup(confirm_path)
    response = c.post(confirm_path, data=extract_form_fields(confirm_soup))
    assert response.status_code == 302, "Confirm should redirect forth"
    assert Order.objects.count() == 1

    order = Order.objects.filter(payment_method=payment_method).first()
    process_payment_path = reverse("shuup:order_process_payment", kwargs={"pk": order.pk, "key": order.key})
    process_payment_return_path = reverse("shuup:order_process_payment_return",kwargs={"pk": order.pk, "key": order.key})
    order_complete_path = reverse("shuup:order_complete",kwargs={"pk": order.pk, "key": order.key})

    # Visit payment page
    response = c.get(process_payment_path)
    assert response.status_code == 302, "Payment page should redirect forth"
    assert response.url.endswith(process_payment_return_path)

    # Check payment return
    response = c.get(process_payment_return_path)
    assert response.status_code == 302, "Payment return should redirect forth"
    assert response.url.endswith(order_complete_path)

    response = c.get(order_complete_path)
    assert response.status_code == 200


@pytest.mark.django_db
def test_checkout_boleto_errors():
    """ Transação com Boleto com erros """
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

    # Create methods
    shipping_method = get_default_shipping_method()
    processor = get_payment_provider()

    payment_method = processor.create_service(
        PagSeguroPaymentMethod.BOLETO.value,
        identifier="pagseguro_boleto",
        shop=get_default_shop(),
        name="boleto",
        enabled=True,
        tax_class=get_default_tax_class())

    # Resolve paths
    addresses_path = reverse("shuup:checkout", kwargs={"phase": "addresses"})
    methods_path = reverse("shuup:checkout", kwargs={"phase": "methods"})
    payment_path = reverse("shuup:checkout", kwargs={"phase": "payment"})
    confirm_path = reverse("shuup:checkout", kwargs={"phase": "confirm"})

    # Phase: Addresses
    addresses_soup = c.soup(addresses_path)
    inputs = fill_address_inputs(addresses_soup, with_company=False)
    c.post(addresses_path, data=inputs)

    # Phase: Methods
    c.post(
        methods_path,
        data={
            "payment_method": payment_method.pk,
            "shipping_method": shipping_method.pk
        }
    )
    c.get(confirm_path)

    # Phase: Payment
    # Erro1 - faltando paymentMethod
    response = c.post(payment_path, {})
    assert response.status_code == 400
    assert "Invalid payment method" in response.content.decode("utf-8")

    # Erro2 - faltando senderHash
    response = c.post(payment_path, {
        "paymentMethod": PagSeguroPaymentMethodIdentifier.Boleto,
    })
    assert response.status_code == 400
    assert "Invalid sender hash" in response.content.decode("utf-8")

    response = c.post(payment_path, {
        "paymentMethod": PagSeguroPaymentMethodIdentifier.Boleto,
        "senderHash": "J7E98Y37WEIRUHDIAI9U8RYE7UQE"
    })
    assert response.status_code == 200

    confirm_soup = c.soup(confirm_path)
    response = c.post(confirm_path, data=extract_form_fields(confirm_soup))
    assert response.status_code == 302
    assert Order.objects.count() == 1

    order = Order.objects.filter(payment_method=payment_method).first()
    process_payment_path = reverse("shuup:order_process_payment", kwargs={"pk": order.pk, "key": order.key})
    process_payment_return_path = reverse("shuup:order_process_payment_return",kwargs={"pk": order.pk, "key": order.key})
    order_complete_path = reverse("shuup:order_complete", kwargs={"pk": order.pk, "key": order.key})
    order_canceled_path = reverse("shuup:order_payment_canceled", kwargs={"pk": order.pk, "key": order.key})

    # Pay - Error from PagSeguro
    with patch.object(PagSeguro, 'pay', return_value=PagSeguroPaymentResult(xmltodict.parse(ERROR_XML))):
        response = c.get(process_payment_path)
        assert response.status_code == 302
        assert order_canceled_path in response.url

    # Pay - Exception! from PagSeguro
    with patch.object(PagSeguro, 'pay') as mock:
        mock.side_effect = PagSeguroException(500, "my_custom_error")
        response = c.get(process_payment_path)
        assert response.status_code == 302
        assert order_canceled_path in response.url

    # Pay again - Success
    response = c.get(process_payment_path)
    assert response.status_code == 302
    assert response.url.endswith(process_payment_return_path)

    # Check payment return
    response = c.get(process_payment_return_path)
    assert response.status_code == 302
    assert response.url.endswith(order_complete_path)

    response = c.get(order_complete_path)
    assert response.status_code == 200



@pytest.mark.django_db
def test_checkout_debit_success():
    """ Transação com Debito Online com sucesso """
    initialize()

    c = SmartClient()
    default_product = get_default_product()

    basket_path = reverse("shuup:basket")
    add_to_basket_resp = c.post(basket_path, data={
        "command": "add",
        "product_id": default_product.pk,
        "quantity": 1,
        "supplier": get_default_supplier().pk
    })
    assert add_to_basket_resp.status_code < 400

    # Create methods
    shipping_method = get_default_shipping_method()
    processor = get_payment_provider()
    assert isinstance(processor, PagSeguroPaymentProcessor)

    payment_method = processor.create_service(
        PagSeguroPaymentMethod.ONLINE_DEBIT.value,
        identifier="pagseguro_debit",
        shop=get_default_shop(),
        name="debit",
        enabled=True,
        tax_class=get_default_tax_class())

    # Resolve paths
    addresses_path = reverse("shuup:checkout", kwargs={"phase": "addresses"})
    methods_path = reverse("shuup:checkout", kwargs={"phase": "methods"})
    payment_path = reverse("shuup:checkout", kwargs={"phase": "payment"})
    confirm_path = reverse("shuup:checkout", kwargs={"phase": "confirm"})


    # Phase: Addresses
    addresses_soup = c.soup(addresses_path)
    inputs = fill_address_inputs(addresses_soup, with_company=False)
    response = c.post(addresses_path, data=inputs)
    assert response.status_code == 302, "Address phase should redirect forth"
    assert response.url.endswith(methods_path)

    # Phase: Methods
    assert Order.objects.filter(payment_method=payment_method).count() == 0
    response = c.post(
        methods_path,
        data={
            "payment_method": payment_method.pk,
            "shipping_method": shipping_method.pk
        }
    )

    assert response.status_code == 302, "Methods phase should redirect forth"
    assert response.url.endswith(confirm_path)
    response = c.get(confirm_path)
    assert response.status_code == 302, "Confirm should first redirect forth"
    assert response.url.endswith(payment_path)

    # Phase: Payment
    response = c.soup(payment_path)
    response = c.post(payment_path, {
        "paymentMethod": PagSeguroPaymentMethodIdentifier.Debito,
        "bankOption": "{0}".format(PagSeguroPaymentMethodCode.DebitoOnlineBB.value),
        "senderHash": "J7E98Y37WEIRUHDIAI9U8RYE7UQE"
    })

    assert response.status_code == 200

    confirm_soup = c.soup(confirm_path)
    response = c.post(confirm_path, data=extract_form_fields(confirm_soup))
    assert response.status_code == 302, "Confirm should redirect forth"
    assert Order.objects.count() == 1

    order = Order.objects.filter(payment_method=payment_method).first()
    process_payment_path = reverse("shuup:order_process_payment", kwargs={"pk": order.pk, "key": order.key})
    process_payment_return_path = reverse("shuup:order_process_payment_return",kwargs={"pk": order.pk, "key": order.key})
    order_complete_path = reverse("shuup:order_complete",kwargs={"pk": order.pk, "key": order.key})

    # Visit payment page
    response = c.get(process_payment_path)
    assert response.status_code == 302, "Payment page should redirect forth"
    assert response.url.endswith(process_payment_return_path)

    # Check payment return
    response = c.get(process_payment_return_path)
    assert response.status_code == 302, "Payment return should redirect forth"
    assert response.url.endswith(order_complete_path)

    response = c.get(order_complete_path)
    assert response.status_code == 200


@pytest.mark.django_db
def test_checkout_debit_errors():
    """ Transação com Debito Online com erros """
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

    # Create methods
    shipping_method = get_default_shipping_method()
    processor = get_payment_provider()

    payment_method = processor.create_service(
        PagSeguroPaymentMethod.ONLINE_DEBIT.value,
        identifier="pagseguro_debit",
        shop=get_default_shop(),
        name="debit",
        enabled=True,
        tax_class=get_default_tax_class())

    # Resolve paths
    addresses_path = reverse("shuup:checkout", kwargs={"phase": "addresses"})
    methods_path = reverse("shuup:checkout", kwargs={"phase": "methods"})
    payment_path = reverse("shuup:checkout", kwargs={"phase": "payment"})
    confirm_path = reverse("shuup:checkout", kwargs={"phase": "confirm"})


    # Phase: Addresses
    addresses_soup = c.soup(addresses_path)
    inputs = fill_address_inputs(addresses_soup, with_company=False)
    c.post(addresses_path, data=inputs)

    # Phase: Methods
    c.post(
        methods_path,
        data={
            "payment_method": payment_method.pk,
            "shipping_method": shipping_method.pk
        }
    )

    c.get(confirm_path)

    # Erro1 - faltando paymentMethod
    response = c.post(payment_path, {})
    assert response.status_code == 400
    assert "Invalid payment method" in response.content.decode("utf-8")

    # Erro2 - faltando bankOption
    response = c.post(payment_path, {
        "paymentMethod": PagSeguroPaymentMethodIdentifier.Debito,
    })
    assert response.status_code == 400
    assert "Invalid bank option" in response.content.decode("utf-8")

    # Erro3 - faltando senderHash
    response = c.post(payment_path, {
        "paymentMethod": PagSeguroPaymentMethodIdentifier.Debito,
        "bankOption": "{0}".format(PagSeguroPaymentMethodCode.DebitoOnlineBB.value),
    })
    assert response.status_code == 400
    assert "Invalid sender hash" in response.content.decode("utf-8")

    response = c.post(payment_path, {
        "paymentMethod": PagSeguroPaymentMethodIdentifier.Debito,
        "bankOption": "{0}".format(PagSeguroPaymentMethodCode.DebitoOnlineBB.value),
        "senderHash": "J7E98Y37WEIRUHDIAI9U8RYE7UQE"
    })

    confirm_soup = c.soup(confirm_path)
    response = c.post(confirm_path, data=extract_form_fields(confirm_soup))
    assert response.status_code == 302, "Confirm should redirect forth"
    assert Order.objects.count() == 1

    order = Order.objects.filter(payment_method=payment_method).first()
    process_payment_path = reverse("shuup:order_process_payment", kwargs={"pk": order.pk, "key": order.key})
    process_payment_return_path = reverse("shuup:order_process_payment_return",kwargs={"pk": order.pk, "key": order.key})
    order_complete_path = reverse("shuup:order_complete",kwargs={"pk": order.pk, "key": order.key})

    # Visit payment page
    response = c.get(process_payment_path)
    assert response.status_code == 302, "Payment page should redirect forth"
    assert response.url.endswith(process_payment_return_path)

    # Check payment return
    response = c.get(process_payment_return_path)
    assert response.status_code == 302, "Payment return should redirect forth"
    assert response.url.endswith(order_complete_path)

    response = c.get(order_complete_path)
    assert response.status_code == 200
