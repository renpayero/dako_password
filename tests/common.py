# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests.common import new_test_user

from odoo.addons.base.tests.common import BaseCommon


class DakoPasswordData:
    """User A belongs to vault A, user B to vault B, M is Administrador de contrasenas."""

    @classmethod
    def _dako_setup_data(cls):
        user_context = {'no_reset_password': True}
        cls.user_a = new_test_user(
            cls.env, login='dako_a', groups='base.group_user,base.group_allow_export', context=user_context,
        )
        cls.user_b = new_test_user(cls.env, login='dako_b', groups='base.group_user', context=user_context)
        cls.manager = new_test_user(
            cls.env, login='dako_m',
            groups='base.group_user,base.group_allow_export,dako_password.dako_password_group_manager',
            context=user_context,
        )
        Vault = cls.env['dako.password.vault']
        cls.vault_a = Vault.create({'name': 'Vault A', 'user_ids': [Command.set(cls.user_a.ids)]})
        cls.vault_b = Vault.create({'name': 'Vault B', 'user_ids': [Command.set(cls.user_b.ids)]})
        Password = cls.env['dako.password']
        cls.cred_a = Password.create({
            'name': 'Banco A',
            'purpose': 'Pagos a proveedores',
            'url': 'https://banco.example.com',
            'username': 'tesoreria@example.com',
            'password_input': 'Secreto-A-2026',
            'criticality': 'critical',
            'vault_id': cls.vault_a.id,
        })
        cls.cred_b = Password.create({
            'name': 'Servidor B',
            'url': '192.168.1.10:3389',
            'username': 'root',
            'password_input': 'Secreto-B-2026',
            'vault_id': cls.vault_b.id,
        })
        cls.Log = cls.env['dako.password.access.log']

    def _logs(self, credential, action=None):
        domain = [('credential_id', '=', credential.id)]
        if action:
            domain.append(('action', '=', action))
        return self.Log.search(domain)

    def _flush_tracking(self):
        self.env.flush_all()
        self.env.cr.precommit.run()


class DakoPasswordCommon(BaseCommon, DakoPasswordData):

    @classmethod
    def default_env_context(cls):
        # Tracking stays on: the chatter is part of the audit trail under test.
        return {'no_reset_password': True}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._dako_setup_data()
