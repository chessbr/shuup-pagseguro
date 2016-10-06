# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import unicode_literals

from django import forms

from shuup.admin.forms import ShuupAdminForm
from shuup_pagseguro.models import PagSeguroConfig, PagSeguroPaymentProcessor


class PagSeguroPaymentProcessorForm(ShuupAdminForm):
    class Meta:
        model = PagSeguroPaymentProcessor
        exclude = ["identifier"]


class PagSeguroConfigForm(forms.ModelForm):
    class Meta:
        model = PagSeguroConfig
        exclude = []
