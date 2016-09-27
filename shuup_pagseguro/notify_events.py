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

from shuup.notify.base import Event, Variable
from shuup.notify.typology import Email, Enum, Language, Model, Phone
from shuup_pagseguro.constants import PagSeguroTransactionStatus


class PagSeguroPaymentStatusChanged(Event):
    identifier = "pagseguro_payment_status_changed"
    name = _("PagSeguro: Payment Status Changed")

    order = Variable(_("Order"), type=Model("shuup.Order"))
    customer_email = Variable(_("Customer Email"), type=Email)
    customer_phone = Variable(_("Customer Phone"), type=Phone)
    language = Variable(_("Language"), type=Language)

    old_status = Variable(_("Old Status"), type=Enum(PagSeguroTransactionStatus))
    new_status = Variable(_("New Status"), type=Enum(PagSeguroTransactionStatus))
