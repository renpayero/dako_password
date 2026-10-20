# -*- coding: utf-8 -*-
from odoo import models


class ResGroups(models.Model):
    _inherit = 'res.groups'

    def _get_hidden_extra_categories(self):
        # The "Contraseñas" role selector of the user form only shows in debug mode.
        return super()._get_hidden_extra_categories() + ['dako_password.dako_password_module_category']
