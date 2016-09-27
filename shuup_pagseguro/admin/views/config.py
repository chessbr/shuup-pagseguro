# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import unicode_literals

from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic.edit import DeleteView

from shuup.admin.utils.picotable import Column, TextFilter
from shuup.admin.utils.views import CreateOrUpdateView, PicotableListView
from shuup_pagseguro.admin.forms import PagSeguroConfigForm
from shuup_pagseguro.models import PagSeguroConfig


class ConfigListView(PicotableListView):
    model = PagSeguroConfig
    default_columns = [
        Column("shop", _("Shop"), filter_config=TextFilter()),
        Column("email", _("Account email"), filter_config=TextFilter()),
    ]


class ConfigEditView(CreateOrUpdateView):
    model = PagSeguroConfig
    form_class = PagSeguroConfigForm
    template_name = "pagseguro/admin/config_edit.jinja"
    context_object_name = "config"


class ConfigDeleteView(DeleteView):
    model = PagSeguroConfig
    success_url = reverse_lazy("shuup_admin:pagseguro_config.list")
