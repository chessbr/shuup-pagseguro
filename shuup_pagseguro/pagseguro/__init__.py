# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
from decimal import Decimal
import re

from django.template.loader import get_template
import requests
import xmltodict

from shuup_pagseguro.constants import PagSeguroPaymentMethod

phone_matcher = re.compile("\(?(\d{2})\)?\D*(\d+)\D*(\d*)")

PAGSEGURO_WS_CHECKOUT_URL = "https://ws.pagseguro.uol.com.br/v2/transactions"
PAGSEGURO_WS_CHECKOUT_URL_SANDBOX = "https://ws.sandbox.pagseguro.uol.com.br/v2/transactions"

PAGSEGURO_WS_SESSION_URL = "https://ws.pagseguro.uol.com.br/v2/sessions"
PAGSEGURO_WS_SESSION_URL_SANDBOX = "https://ws.sandbox.pagseguro.uol.com.br/v2/sessions"

PAGSEGURO_WS_TRANSACTION_URL = "https://ws.pagseguro.uol.com.br/v3/transactions/{0}"
PAGSEGURO_WS_TRANSACTION_URL_SANDBOX = "https://ws.sandbox.pagseguro.uol.com.br/v3/transactions/{0}"

PAGSEGURO_WS_NOTIFICATION_URL = "https://ws.pagseguro.uol.com.br/v3/transactions/notifications/{0}"
PAGSEGURO_WS_NOTIFICATION_URL_SANDBOX = "https://ws.sandbox.pagseguro.uol.com.br/v3/transactions/notifications/{0}"


class PagSeguroPaymentResult(object):
    _data = None
    error = False
    errors = []
    code = None
    payment_link = None

    def __init__(self, data):
        self._data = data

        if data.get("errors"):
            self.error = True
            self.errors = data["errors"]
        else:
            self.code = data["transaction"]["code"]
            self.payment_link = data["transaction"].get("paymentLink")


class PagSeguroException(Exception):
    def __init__(self, status_code, error):
        self.status_code = status_code
        self.error = error


class PagSeguro(object):
    email = None
    token = None
    sandbox = False
    notification_url = None

    def __init__(self, email, token, sandbox=False):
        self.email = email
        self.token = token
        self.sandbox = sandbox

    def _create_params(self):
        return {
            'email': self.email,
            'token': self.token
        }

    @classmethod
    def create_from_config(cls, pagseguro_config):
        return cls(pagseguro_config.email,
                   pagseguro_config.token,
                   pagseguro_config.sandbox)

    def get_session_id(self):
        """
        Obtém um ID de sessão
        :rtype: str
        :return: ID de uma nova sessão
        """
        url = PAGSEGURO_WS_SESSION_URL_SANDBOX if self.sandbox else PAGSEGURO_WS_SESSION_URL
        response = requests.post(url, params=self._create_params())

        # Tudo limpo
        if response.status_code == 200:
            result = xmltodict.parse(response.content)
            return result["session"]["id"]
        else:
            raise PagSeguroException(response.status_code, response.content)

    def get_notification_info(self, notification_code):
        """
        Obtém as informações de uma transação
        :rtype: dict
        :return: dicionário contento informações de uma transação
        """
        url = PAGSEGURO_WS_NOTIFICATION_URL_SANDBOX if self.sandbox else PAGSEGURO_WS_NOTIFICATION_URL
        url = url.format(notification_code)
        response = requests.get(url, params=self._create_params())

        # Tudo limpo
        if response.status_code == 200:
            return xmltodict.parse(response.content)
        else:
            raise PagSeguroException(response.status_code, response.content)

    def get_transaction_info(self, transaction_code):
        """
        Obtém as informações de uma transação
        :rtype: dict
        :return: dicionário contento informações de uma transação
        """
        url = PAGSEGURO_WS_TRANSACTION_URL_SANDBOX if self.sandbox else PAGSEGURO_WS_TRANSACTION_URL
        url = url.format(transaction_code)
        response = requests.get(url, params=self._create_params())

        # Tudo limpo
        if response.status_code == 200:
            return xmltodict.parse(response.content)
        else:
            raise PagSeguroException(response.status_code, response.content)

    def pay(self, service, order):
        """
        Faz a transação do pagamento
        :type service: shuup.core.models.PaymentMethod
        :type order: shuup.core.models.Order
        :rtype: PagSeguroPaymentResult
        :return: sucesso ou erro
        """
        payment_xml = self._get_payment_xml(service, order)

        url = PAGSEGURO_WS_CHECKOUT_URL_SANDBOX if self.sandbox else PAGSEGURO_WS_CHECKOUT_URL
        headers = {'Content-Type': 'application/xml'}
        response = requests.post(url, params=self._create_params(), data=payment_xml, headers=headers)

        # Erro!!
        if response.status_code == 500:
            raise PagSeguroException(response.status_code, response.content)
        else:
            result = xmltodict.parse(response.content)
            return PagSeguroPaymentResult(result)

    def _get_payment_xml(self, service, order):
        """
        Gera o XML para pagamento do PagSeguro
        :type service: shuup.core.models.PaymentMethod
        :type order: shuup.core.models.Order
        """
        template = get_template("pagseguro/xml/payment.jinja")

        phone_area_code = ""
        phone_number = ""
        cpf = ""
        cnpj = ""

        lines = []
        total_lines = Decimal()

        for line in order.lines.all():
            if line.taxful_price.value > 0:
                lines.append(line)
                total_lines = total_lines + line.taxful_price.value

        extra_amount = (order.taxful_total_price.value - total_lines)
        postal_code = "".join([d for d in order.shipping_address.postal_code if d.isdigit()])

        phone_result = phone_matcher.search(order.phone)
        if phone_result:
            phone_groups = phone_result.groups()
            phone_area_code = phone_groups[0]
            phone_number = "".join(phone_groups[1:])

        if hasattr(order.creator, 'pf_person') and order.creator.pf_person.cpf:
            cpf = "".join([d for d in order.creator.pf_person.cpf if d.isdigit()])

        if hasattr(order.creator, 'pj_person') and order.creator.pj_person.cnpj:
            cnpj = "".join([d for d in order.creator.pj_person.cnpj if d.isdigit()])

        return template.render({
            "order": order,
            "service": service,
            "lines": lines,
            "extra_amount": extra_amount,
            "postal_code": postal_code,
            "phone_area_code": phone_area_code,
            "phone_number": phone_number,
            "customer_cpf": cpf,
            "customer_cnpj": cnpj,
            "PagSeguroPaymentMethod": PagSeguroPaymentMethod
        })
