# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class PagSeguroTransactionStatus(Enum):
    WaitingPayment = 1
    InAnalysis = 2
    Paid = 3
    Available = 4
    InDispute = 5
    Refunded = 6
    Canceled = 7
    Debited = 8
    TempRetention = 9

    class Labels:
        WaitingPayment = _("Aguardando pagamento")
        InAnalysis = _("Em análise")
        Paid = _("Paga")
        Available = _("Disponível")
        InDispute = _("Em disputa")
        Refunded = _("Devolvido")
        Canceled = _("Cancelada")
        Debited = _("Debitada")
        TempRetention = _("Retenção temporária")


class PagSeguroTransactionCustomerStatus(Enum):
    """
    Enum contento estado da transação vísível ao CONSUMIDOR
    """
    WaitingPayment = PagSeguroTransactionStatus.WaitingPayment.value
    InAnalysis = PagSeguroTransactionStatus.InAnalysis.value
    Paid = PagSeguroTransactionStatus.Paid.value
    Available = PagSeguroTransactionStatus.Available.value
    InDispute = PagSeguroTransactionStatus.InDispute.value
    Refunded = PagSeguroTransactionStatus.Refunded.value
    Canceled = PagSeguroTransactionStatus.Canceled.value
    Debited = PagSeguroTransactionStatus.Debited.value
    TempRetention = PagSeguroTransactionStatus.TempRetention.value

    class Labels:
        WaitingPayment = _("Aguardando pagamento")
        InAnalysis = _("Em análise")
        Paid = _("Paga")
        Available = _("Paga")
        InDispute = _("Em disputa")
        Refunded = _("Devolvido")
        Canceled = _("Cancelada")
        Debited = _("Devolvido")
        TempRetention = _("Em disputa")


class PagSeguroPaymentMethodCode(Enum):
    BoletoSantander = 202
    DebitoOnlineBradesco = 301
    DebitoOnlineItau = 302
    DebitoOnlineBB = 304
    DebitoOnlineBanrisul = 306
    DebitoOnlineHSBC = 307
    SaldoPagSeguro = 401
    DepositoBB = 701
    DepositoHSBC = 702

    class Labels:
        BoletoSantander = _("Boleto Santander")
        DebitoOnlineBradesco = _("Débito Online Bradesco")
        DebitoOnlineItau = _("Débito Online Itaú")
        DebitoOnlineBB = _("Débito Online Banco do Brasil")
        DebitoOnlineBanrisul = _("Débito Online Banrisul")
        DebitoOnlineHSBC = _("Débito Online HSBC")
        SaldoPagSeguro = _("Saldo PagSeguro")
        DepositoBB = _("Depósito em conta Banco do Brasil")
        DepositoHSBC = _("Depósito em conta HSBC")


class PagSeguroPaymentMethod(Enum):
    BOLETO = 'BOLETO'
    ONLINE_DEBIT = 'ONLINE_DEBIT'

    class Labels:
        BOLETO = _('Boleto')
        ONLINE_DEBIT = _('Débito Online')


class PagSeguroPaymentMethodIdentifier(object):
    Boleto = 'boleto'
    Debito = 'eft'


class PagSeguroBank(object):
    Bradesco = 'bradesco'
    Itau = 'itau'
    BB = 'bancodobrasil'
    Banrisul = 'banrisul'
    HSBC = 'hsbc'

    @classmethod
    def get_options(cls):
        return [cls.Bradesco, cls.Itau, cls.BB, cls.Banrisul, cls.HSBC]


PagSeguroDebitBankMap = {
    "301": PagSeguroBank.Bradesco,
    "302": PagSeguroBank.Itau,
    "304": PagSeguroBank.BB,
    "306": PagSeguroBank.Banrisul,
    "307": PagSeguroBank.HSBC
}
