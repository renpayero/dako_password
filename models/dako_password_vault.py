# -*- coding: utf-8 -*-
from random import randint

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DakoPasswordVault(models.Model):
    _name = 'dako.password.vault'
    _description = 'Vault de credenciales'
    _inherit = ['mail.thread']
    _order = 'name, id'

    def _default_color(self):
        return randint(1, 11)

    name = fields.Char(string='Nombre', required=True, tracking=True)
    description = fields.Text(string='Descripción')
    color = fields.Integer(string='Color', default=_default_color)
    active = fields.Boolean(default=True, tracking=True)
    user_ids = fields.Many2many(
        'res.users', 'dako_password_vault_user_rel', 'vault_id', 'user_id',
        string='Usuarios autorizados', domain=[('share', '=', False)],
        default=lambda self: self.env.user, tracking=True,
        help='Solo estos usuarios ven y editan las credenciales del vault.',
    )
    password_ids = fields.One2many('dako.password', 'vault_id', string='Credenciales')
    password_count = fields.Integer(string='Cantidad de credenciales', compute='_compute_password_counts')
    critical_count = fields.Integer(string='Credenciales críticas', compute='_compute_password_counts')

    @api.depends('password_ids.criticality')
    def _compute_password_counts(self):
        totals = {}
        critical = {}
        groups = self.env['dako.password']._read_group(
            [('vault_id', 'in', self._origin.ids)], ['vault_id', 'criticality'], ['__count'],
        )
        for vault, criticality, count in groups:
            totals[vault.id] = totals.get(vault.id, 0) + count
            if criticality == 'critical':
                critical[vault.id] = count
        for vault in self:
            vault.password_count = totals.get(vault._origin.id, 0)
            vault.critical_count = critical.get(vault._origin.id, 0)

    @api.constrains('user_ids')
    def _check_user_ids(self):
        for vault in self:
            if not vault.user_ids:
                raise ValidationError(self.env._(
                    "El vault \"%s\" tiene que tener al menos un usuario autorizado.", vault.name,
                ))
            if vault.user_ids.filtered('share'):
                raise ValidationError(self.env._(
                    "El vault \"%s\" solo admite usuarios internos.", vault.name,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        if not self._dako_is_manager():
            # Whoever creates a vault keeps access to it.
            vals_list = [dict(vals) for vals in vals_list]
            for vals in vals_list:
                if 'user_ids' in vals:
                    vals['user_ids'] = list(vals['user_ids'] or []) + [Command.link(self.env.uid)]
        return super().create(vals_list)

    def write(self, vals):
        member_of = self.browse()
        if 'user_ids' in vals and not self._dako_is_manager():
            member_of = self.filtered(lambda vault: self.env.user in vault.user_ids)
        result = super().write(vals)
        # Read as superuser: after leaving, the record rules no longer let the user read it.
        left = member_of.sudo().filtered(lambda vault: self.env.user not in vault.user_ids)
        if left:
            raise UserError(self.env._(
                "No podés quitarte del vault \"%s\": perderías el acceso. "
                "Pedíselo a otro usuario del vault o a un Administrador de contraseñas.",
                left[:1].name,
            ))
        if 'active' in vals:
            # Archiving a vault archives its active credentials; restoring it brings back
            # only those, not the ones that were archived on purpose before.
            Password = self.env['dako.password'].with_context(active_test=False)
            if vals['active']:
                Password.search([('vault_id', 'in', self.ids), ('archived_with_vault', '=', True)]).write(
                    {'active': True, 'archived_with_vault': False}
                )
            else:
                Password.search([('vault_id', 'in', self.ids), ('active', '=', True)]).write(
                    {'active': False, 'archived_with_vault': True}
                )
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_with_credentials(self):
        has_credentials = self.env['dako.password'].sudo().with_context(active_test=False).search_count(
            [('vault_id', 'in', self.ids)], limit=1,
        )
        if has_credentials:
            raise UserError(self.env._(
                "No se puede borrar un vault con credenciales (también cuentan las archivadas). "
                "Archivalo o mové sus credenciales a otro vault."
            ))

    def action_open_passwords(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('dako_password.dako_password_action')
        action['name'] = self.name
        action['context'] = {
            'default_vault_id': self.id,
            'searchpanel_default_vault_id': self.id,
        }
        return action

    def _dako_is_manager(self):
        return self.env.su or self.env.user.has_group('dako_password.dako_password_group_manager')
