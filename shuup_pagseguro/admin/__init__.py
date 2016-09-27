# -*- coding: utf-8 -*-
# This file is part of Shuup PagSeguro.
#
# Copyright (c) 2016, Rockho Team. All rights reserved.
# Author: Christian Hess
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.

from django.utils.translation import ugettext_lazy as _

from shuup.admin.base import AdminModule, MenuEntry
from shuup.admin.currencybound import CurrencyBound
from shuup.admin.utils.permissions import get_default_model_permissions
from shuup.admin.utils.urls import admin_url, derive_model_url, get_edit_and_list_urls
from shuup_pagseguro.models import PagSeguroConfig


class PagSeguroModule(CurrencyBound, AdminModule):
    name = _("PagSeguro")
    breadcrumbs_menu_entry = MenuEntry(name, url="shuup_admin:pagseguro.dashboard")

    def get_urls(self):
        return [
            admin_url(
                "^pagseguro/payment/refresh/$",
                "shuup_pagseguro.admin.views.PaymentRefreshView",
                name="pagseguro.payment_refresh"
            ),
            admin_url(
                "^pagseguro/$",
                "shuup_pagseguro.admin.views.DashboardView",
                name="pagseguro.dashboard"
            ),
        ]

    def get_menu_entries(self, request):
        category = _("PagSeguro")
        return [
            MenuEntry(
                text=_("General"),
                icon="fa fa-dollar",
                url="shuup_admin:pagseguro.dashboard",
                category=category,
                aliases=[_("General")]
            ),
        ]


class PagSeguroBaseAdminModule(AdminModule):
    category = _("PagSeguro")
    model = None
    name = None
    url_prefix = None
    view_template = None
    name_template = None
    menu_entry_url = None
    url_name_prefix = None
    icon = None

    def get_urls(self):
        permissions = self.get_required_permissions()
        return [
            admin_url(
                "%s/(?P<pk>\d+)/delete/$" % self.url_prefix,
                self.view_template % "Delete",
                name=self.name_template % "delete",
                permissions=permissions
            )
        ] + get_edit_and_list_urls(
            url_prefix=self.url_prefix,
            view_template=self.view_template,
            name_template=self.name_template,
            permissions=permissions
        )

    def get_menu_entries(self, request):
        return [
            MenuEntry(
                text=self.name,
                url=self.menu_entry_url,
                icon=self.icon,
                category=self.category
            )
        ]

    def get_required_permissions(self):
        return get_default_model_permissions(self.model)

    def get_model_url(self, obj, kind):
        return derive_model_url(self.model, self.url_name_prefix, obj, kind)

    def get_menu_category_icons(self):
        return {self.category: "fa fa-dollar", self.name: self.icon}


class PagSeguroConfigModule(PagSeguroBaseAdminModule):
    name = _("Configurations")
    model = PagSeguroConfig

    icon = "fa fa-cogs"
    breadcrumbs_menu_entry = MenuEntry(name, url="shuup_admin:pagseguro_config.list")
    url_name_prefix = "shuup_admin:pagseguro_config"
    url_prefix = "^pagseguro/config"
    view_template = "shuup_pagseguro.admin.views.config.Config%sView"
    name_template = "pagseguro_config.%s"
    menu_entry_url = "shuup_admin:pagseguro_config.list"
