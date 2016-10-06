# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import unicode_literals

from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from mock import patch
import pytest
import requests
import xmltodict

from shuup.core.models._addresses import MutableAddress
from shuup.core.models._orders import Order
from shuup.testing.factories import (
    get_default_product, get_default_shipping_method, get_default_shop, get_default_supplier,
    get_default_tax_class
)
from shuup.testing.soup_utils import extract_form_fields
from shuup_pagseguro.constants import (
    PagSeguroPaymentMethod, PagSeguroPaymentMethodCode, PagSeguroPaymentMethodIdentifier
)
from shuup_pagseguro.pagseguro import PagSeguro, PagSeguroException, PagSeguroPaymentResult
from shuup_pagseguro_tests import ERROR_XML, TRANSACTION_XML
from shuup_pagseguro_tests.utils import (
    get_pagseguro_config, get_payment_provider, initialize, patch_pagseguro
)
from shuup_tests.front.test_checkout_flow import fill_address_inputs
from shuup_tests.utils import SmartClient


class PFPerson(object):
    cpf = "012.345.678-90"
class PJPerson(object):
    cnpj = "80.033.176/0001-89"


def setup_module():
    patch_pagseguro()

def teardown_module():
    patch.stopall()


@pytest.mark.django_db
def test_pagseguro():
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

    addr = MutableAddress.from_data(dict(
        name=u"Dog Hello",
        suffix=", Esq.",
        postal_code="89999-999",
        street="Woof Ave.",
        city="Dog Fort",
        country="GB",
        phone="47 98821-2231",
    ))
    patch("shuup.testing.factories.get_address", new_callable=lambda:addr)

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
    USER_MODEL = get_user_model()

    order.phone = "47 98821-2231"
    order.creator = get_user_model().objects.create_user(**{
        USER_MODEL.USERNAME_FIELD: "admin@admin.com",
        "password": "123"
    })
    order.save()

    pagseguro = PagSeguro.create_from_config(get_pagseguro_config())

    # unpatch methods
    patch.stopall()

    # Test: get_session_id - SUCCESS
    session_xml_fake = """<session><id>WOEIFJE9IUREI29RU8</id></session>"""
    response = Mock()
    response.status_code = 200
    response.content = session_xml_fake
    with patch.object(requests, 'post', return_value=response):
        session_id = xmltodict.parse(session_xml_fake)['session']['id']
        assert pagseguro.get_session_id() == session_id

    # Test: get_session_id - EXCEPTION
    response = Mock()
    response.status_code = 500
    response.content = ERROR_XML
    with patch.object(requests, 'post', return_value=response):
        with pytest.raises(PagSeguroException) as exc:
            pagseguro.get_session_id()
        assert exc.value.status_code == 500
        assert exc.value.error == ERROR_XML


    # Test: get_notification_info - SUCCESS
    transaction_xml_fake = """<transaction><date>WOEIFJE9IUREI29RU8</date></transaction>"""
    response = Mock()
    response.status_code = 200
    response.content = transaction_xml_fake
    with patch.object(requests, 'get', return_value=response):
        assert pagseguro.get_notification_info("XXXX") == xmltodict.parse(transaction_xml_fake)

    # Test: get_notification_info - EXCEPTION
    response = Mock()
    response.status_code = 500
    response.content = ERROR_XML
    with patch.object(requests, 'get', return_value=response):
        with pytest.raises(PagSeguroException) as exc:
            pagseguro.get_notification_info("ZZZZ")
        assert exc.value.status_code == 500
        assert exc.value.error == ERROR_XML



    # Test: get_transaction_info - SUCCESS
    transaction_xml_fake = """<transaction><date>WOEIFJE9IUREI29RU8</date></transaction>"""
    response = Mock()
    response.status_code = 200
    response.content = transaction_xml_fake
    with patch.object(requests, 'get', return_value=response):
        assert pagseguro.get_transaction_info("XXXX") == xmltodict.parse(transaction_xml_fake)

    # Test: get_transaction_info - EXCEPTION
    response = Mock()
    response.status_code = 500
    response.content = ERROR_XML
    with patch.object(requests, 'get', return_value=response):
        with pytest.raises(PagSeguroException) as exc:
            pagseguro.get_transaction_info("ZZZZ")
        assert exc.value.status_code == 500
        assert exc.value.error == ERROR_XML



    # Test: pay - SUCCESS
    response = Mock()
    response.status_code = 200
    response.content = TRANSACTION_XML
    with patch.object(requests, 'post', return_value=response):
        parsed_xml = xmltodict.parse(TRANSACTION_XML)
        result = pagseguro.pay(payment_method, order)
        assert isinstance(result, PagSeguroPaymentResult)
        assert result.error is False
        assert result._data == parsed_xml
        assert result.code == parsed_xml['transaction']['code']
        assert result.payment_link == parsed_xml['transaction']['paymentLink']

    # Test: pay - ERROR
    response = Mock()
    response.status_code = 400
    response.content = ERROR_XML
    with patch.object(requests, 'post', return_value=response):
        parsed_xml = xmltodict.parse(ERROR_XML)
        result = pagseguro.pay(payment_method, order)
        assert isinstance(result, PagSeguroPaymentResult)
        assert result.error is True
        assert result._data == parsed_xml
        assert result.errors == parsed_xml['errors']

    # Test: pay - EXCEPTION
    response = Mock()
    response.status_code = 500
    response.content = "A BIG MISTAKE"
    with patch.object(requests, 'post', return_value=response):
        with pytest.raises(PagSeguroException) as exc:
            pagseguro.pay(payment_method, order)
        assert exc.value.status_code == 500
        assert exc.value.error == "A BIG MISTAKE"

    def get_only_nums(value):
        return "".join([c for c in value if c.isdigit()])


    # Test: _get_payment_xml with CPF
    order.creator.pf_person = PFPerson()
    payment_xml = xmltodict.parse(pagseguro._get_payment_xml(payment_method, order))

    assert payment_xml['payment']['currency'] == 'BRL'
    assert payment_xml['payment']['method'] == PagSeguroPaymentMethodIdentifier.Debito
    assert payment_xml['payment']['sender']['documents']['document']['type'] == 'CPF'
    assert payment_xml['payment']['sender']['documents']['document']['value'] == get_only_nums(PFPerson().cpf)

    # Test: _get_payment_xml with CNPJ
    delattr(order.creator, 'pf_person')
    order.creator.pj_person = PJPerson()
    payment_xml = xmltodict.parse(pagseguro._get_payment_xml(payment_method, order))
    assert payment_xml['payment']['sender']['documents']['document']['type'] == 'CNPJ'
    assert payment_xml['payment']['sender']['documents']['document']['value'] == get_only_nums(PJPerson().cnpj)

    assert payment_xml['payment']['sender']['phone']['areaCode'] == "47"
    assert payment_xml['payment']['sender']['phone']['number'] == "988212231"
