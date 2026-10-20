# -*- coding: utf-8 -*-
from odoo import fields, models


class DakoPasswordAccessLog(models.Model):
    _name = 'dako.password.access.log'
    _description = 'Acceso a una contraseña'
    _order = 'id desc'
    _rec_name = 'credential_name'

    credential_id = fields.Many2one(
        'dako.password', string='Credencial', index=True, ondelete='set null', readonly=True,
    )
    credential_name = fields.Char(string='Servicio', readonly=True)
    vault_id = fields.Many2one(
        'dako.password.vault', string='Vault', index='btree_not_null', ondelete='set null',
        readonly=True,
    )
    vault_name = fields.Char(string='Nombre del vault', readonly=True)
    user_id = fields.Many2one(
        'res.users', string='Usuario', required=True, index=True, ondelete='restrict', readonly=True,
    )
    action = fields.Selection(
        [('reveal', 'Vio'), ('copy', 'Copió'), ('export', 'Exportó'), ('duplicate', 'Duplicó')],
        string='Acción', required=True, readonly=True,
    )
