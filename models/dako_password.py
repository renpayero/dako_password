# -*- coding: utf-8 -*-
import io
import re
import secrets
from random import SystemRandom

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import xlsxwriter

# Generator alphabets: no look-alike characters (l, I, O, 0, 1) and only symbols that
# survive copy and paste into forms, shells and spreadsheets.
LOWERCASE = 'abcdefghijkmnopqrstuvwxyz'
UPPERCASE = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
DIGITS = '23456789'
SYMBOLS = '!#%*+-=?@_'

STRENGTH_SELECTION = [('weak', 'Débil'), ('medium', 'Media'), ('strong', 'Fuerte')]
CRITICALITY_SELECTION = [
    ('low', 'Baja'),
    ('medium', 'Media'),
    ('high', 'Alta'),
    ('critical', 'Crítica'),
]
# Kanban highlight colors (Odoo color index): critical in red, high in orange.
CRITICALITY_COLORS = {'critical': 1, 'high': 2}
ACCESS_ACTIONS = ('reveal', 'copy')
URL_WITH_CREDENTIALS = re.compile(r'://[^/@\s]+:[^/@\s]*@')


def password_strength(value):
    """Return (score from 0 to 100, level) for a password."""
    value = value or ''
    score = 0
    if len(value) >= 8:
        score += 25
    if len(value) >= 12:
        score += 15
    if re.search(r'[a-z]', value) and re.search(r'[A-Z]', value):
        score += 20
    if re.search(r'\d', value):
        score += 20
    if re.search(r'[^A-Za-z0-9]', value):
        score += 20
    score = min(score, 100)
    if score >= 75:
        return score, 'strong'
    if score >= 45:
        return score, 'medium'
    return score, 'weak'


def new_password(length=20):
    """Random password with at least one character of each class."""
    classes = (LOWERCASE, UPPERCASE, DIGITS, SYMBOLS)
    alphabet = ''.join(classes)
    chars = [secrets.choice(chars_class) for chars_class in classes]
    chars += [secrets.choice(alphabet) for _i in range(length - len(chars))]
    SystemRandom().shuffle(chars)
    return ''.join(chars)


class DakoPassword(models.Model):
    _name = 'dako.password'
    _description = 'Credencial'
    _inherit = ['mail.thread']
    _order = 'name, id'
    _rec_names_search = ['name', 'purpose', 'url', 'username']

    def _default_vault_id(self):
        vaults = self.env['dako.password.vault'].search([('user_ids', 'in', self.env.uid)], limit=2)
        return vaults.id if len(vaults) == 1 else False

    name = fields.Char(string='Servicio', required=True, tracking=True)
    purpose = fields.Char(string='Propósito', tracking=True, help='Para qué se usa esta credencial.')
    url = fields.Char(
        string='Acceso', tracking=True,
        help='URL, host o forma de acceso. Ej.: https://banco.com, 192.168.1.10:3389, ssh root@servidor.',
    )
    username = fields.Char(string='Usuario / cuenta', tracking=True)
    # The stored secret. NO_ACCESS keeps it out of every regular read path (read, export,
    # search, group by, fields_get); in this module only _dako_read_passwords() reads it,
    # as superuser, after logging the access. Code running as superuser elsewhere (server
    # actions, mail templates rendered by template editors) can still read it: see the
    # manifest description. Never add a related or computed field that exposes it.
    password = fields.Char(
        string='Contraseña guardada', required=True, copy=False, prefetch=False,
        groups=fields.NO_ACCESS,
    )
    # What the views edit: always empty when read, its value is moved to `password`
    # by create() and write().
    password_input = fields.Char(
        string='Contraseña', compute='_compute_password_input', readonly=False, exportable=False,
    )
    password_changed_date = fields.Datetime(
        string='Contraseña cambiada', default=fields.Datetime.now, copy=False, readonly=True,
    )
    criticality = fields.Selection(
        CRITICALITY_SELECTION, string='Criticidad', required=True, default='medium', tracking=True,
        help='Impacto si la credencial se filtra.',
    )
    note = fields.Text(string='Notas')
    vault_id = fields.Many2one(
        'dako.password.vault', string='Vault', required=True, index=True, ondelete='restrict',
        tracking=True, default=_default_vault_id,
    )
    active = fields.Boolean(default=True, tracking=True)
    archived_with_vault = fields.Boolean(
        copy=False, readonly=True,
        help='Archivada al archivar su vault: vuelve cuando se restaura el vault.',
    )
    strength = fields.Selection(
        STRENGTH_SELECTION, string='Fortaleza', compute='_compute_strength', store=True,
    )
    strength_score = fields.Integer(
        string='Puntaje', compute='_compute_strength', store=True, aggregator='avg',
    )
    criticality_color = fields.Integer(compute='_compute_criticality_color')
    access_log_count = fields.Integer(
        string='Accesos', compute='_compute_access_log_count',
        groups='dako_password.dako_password_group_manager',
    )

    def _compute_password_input(self):
        self.password_input = False

    @api.depends('password')
    def _compute_strength(self):
        for rec in self:
            rec.strength_score, rec.strength = password_strength(rec.password)

    @api.depends('criticality')
    def _compute_criticality_color(self):
        for rec in self:
            rec.criticality_color = CRITICALITY_COLORS.get(rec.criticality, 0)

    def _compute_access_log_count(self):
        counts = dict(self.env['dako.password.access.log']._read_group(
            [('credential_id', 'in', self.ids)], ['credential_id'], ['__count'],
        ))
        for rec in self:
            rec.access_log_count = counts.get(rec._origin, 0)

    @api.depends('name', 'vault_id.name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '[%s] %s' % (rec.vault_id.name, rec.name) if rec.vault_id else rec.name

    @api.constrains('vault_id')
    def _check_vault_id(self):
        if self.env.su:
            return
        for rec in self:
            if not rec.vault_id.has_access('read'):
                raise ValidationError(self.env._(
                    "No podés guardar la credencial \"%s\" en un vault al que no tenés acceso.", rec.name,
                ))

    @api.onchange('password_input')
    def _onchange_password_input(self):
        # Live feedback while typing; the stored value is recomputed from `password`.
        for rec in self:
            if rec.password_input:
                rec.strength_score, rec.strength = password_strength(rec.password_input)
            else:
                rec.strength_score = rec._origin.strength_score
                rec.strength = rec._origin.strength

    @api.onchange('url')
    def _onchange_url(self):
        if self.url and URL_WITH_CREDENTIALS.search(self.url):
            return {'warning': {
                'title': self.env._("La dirección tiene usuario y contraseña"),
                'message': self.env._(
                    "La dirección incluye un usuario y una contraseña (usuario:clave@). "
                    "Cargalos en sus campos: el acceso se muestra sin protección."
                ),
            }}

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        for vals in vals_list:
            value = vals.pop('password_input', False) or vals.get('password')
            if not value:
                raise ValidationError(self.env._("Cargá la contraseña de la credencial."))
            vals['password'] = value
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        value = vals.pop('password_input', False)
        if 'active' in vals and 'archived_with_vault' not in vals:
            # Archived or restored by hand: no longer follows its vault.
            vals['archived_with_vault'] = False
        notes_changed = self.browse()
        if 'note' in vals:
            notes_changed = self.filtered(lambda rec: (rec.note or False) != (vals['note'] or False))
        result = super().write(vals) if vals else True
        if value:
            self._dako_set_password(value)
        if notes_changed:
            notes_changed._message_log_batch(
                {rec.id: self.env._("Modificó las notas.") for rec in notes_changed}
            )
        return result

    def copy(self, default=None):
        self.check_access('read')
        new_records = self.browse()
        for rec in self:
            values = dict(default or {})
            values.setdefault('name', self.env._("%s (copia)", rec.name))
            values['password'] = rec.sudo().password
            new_records |= super(DakoPassword, rec).copy(values)
        self._dako_log_access('duplicate')
        return new_records

    def action_open_access_logs(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('dako_password.dako_password_access_log_action')
        action['domain'] = [('credential_id', '=', self.id)]
        action['context'] = {}
        return action

    def dako_reveal(self, action='reveal'):
        """Return {id: password} for the widget; every call is logged."""
        if action not in ACCESS_ACTIONS:
            raise ValidationError(self.env._("Acción de acceso desconocida: %s", action))
        return self._dako_read_passwords(action)

    @api.model
    def generate_password(self):
        return new_password()

    def _dako_read_passwords(self, action):
        # Single read path of the secret: access check, log, then the value.
        self.check_access('read')
        self._dako_log_access(action)
        return {rec.id: rec.password for rec in self.sudo()}

    def _dako_log_access(self, action):
        if not self:
            return
        self.env['dako.password.access.log'].sudo().create([{
            'credential_id': rec.id,
            'credential_name': rec.name,
            'vault_id': rec.vault_id.id,
            'vault_name': rec.vault_id.name,
            'user_id': self.env.uid,
            'action': action,
        } for rec in self])

    def _dako_set_password(self, value):
        self.check_access('write')
        changed = self.sudo().filtered(lambda rec: rec.password != value)
        if not changed:
            return
        changed.write({'password': value, 'password_changed_date': fields.Datetime.now()})
        changed._message_log_batch({rec.id: self.env._("Cambió la contraseña.") for rec in changed})

    def _dako_export_xlsx(self):
        """Spreadsheet with the credentials in self; the export is logged."""
        passwords = self._dako_read_passwords('export')
        criticality_labels = dict(CRITICALITY_SELECTION)
        strength_labels = dict(STRENGTH_SELECTION)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
            'strings_to_urls': False,
            'strings_to_numbers': False,
        })
        sheet = workbook.add_worksheet(self.env._("Credenciales"))
        header_format = workbook.add_format({'bold': True, 'bottom': 1, 'valign': 'vcenter'})
        text_format = workbook.add_format({'valign': 'top'})
        wrap_format = workbook.add_format({'valign': 'top', 'text_wrap': True})
        date_format = workbook.add_format({'valign': 'top', 'num_format': 'dd/mm/yyyy hh:mm'})

        columns = [
            (self.env._("Vault"), 22),
            (self.env._("Servicio"), 28),
            (self.env._("Propósito"), 32),
            (self.env._("Acceso"), 36),
            (self.env._("Usuario / cuenta"), 26),
            (self.env._("Contraseña"), 26),
            (self.env._("Criticidad"), 12),
            (self.env._("Fortaleza"), 12),
            (self.env._("Contraseña cambiada"), 20),
            (self.env._("Notas"), 50),
        ]
        for col, (title, width) in enumerate(columns):
            sheet.set_column(col, col, width)
            sheet.write_string(0, col, title, header_format)

        for row, rec in enumerate(self, start=1):
            texts = [
                rec.vault_id.name, rec.name, rec.purpose, rec.url, rec.username,
                passwords[rec.id], criticality_labels.get(rec.criticality),
                strength_labels.get(rec.strength),
            ]
            for col, text in enumerate(texts):
                sheet.write_string(row, col, text or '', text_format)
            if rec.password_changed_date:
                local_date = fields.Datetime.context_timestamp(rec, rec.password_changed_date)
                sheet.write_datetime(row, 8, local_date.replace(tzinfo=None), date_format)
            sheet.write_string(row, 9, rec.note or '', wrap_format)

        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, max(len(self), 1), len(columns) - 1)
        workbook.close()
        return output.getvalue()
