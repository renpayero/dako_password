# -*- coding: utf-8 -*-
import json
import logging

from werkzeug.exceptions import InternalServerError

from odoo import fields, http
from odoo.exceptions import AccessError, UserError
from odoo.http import content_disposition, request

_logger = logging.getLogger(__name__)

XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class DakoPasswordExport(http.Controller):

    @http.route('/dako_password/export/xlsx', type='http', auth='user', methods=['POST'])
    def export_xlsx(self, domain='[]', ids='[]', **kwargs):
        try:
            return self._export_xlsx(domain, ids)
        except (AccessError, UserError) as exc:
            raise InternalServerError(self._error_payload(exc)) from exc
        except Exception as exc:
            _logger.exception("Exportación de credenciales fallida")
            raise InternalServerError(self._error_payload(exc)) from exc

    def _export_xlsx(self, domain, ids):
        env = request.env
        if not env.user.has_group('base.group_allow_export'):
            raise AccessError(env._("No tenés permiso para exportar datos."))
        try:
            record_ids = json.loads(ids)
            search_domain = json.loads(domain)
        except ValueError as exc:
            raise UserError(env._("Pedido de exportación inválido.")) from exc
        if not isinstance(record_ids, list) or not all(isinstance(i, int) for i in record_ids):
            raise UserError(env._("Pedido de exportación inválido."))
        if not isinstance(search_domain, list):
            raise UserError(env._("Pedido de exportación inválido."))
        if record_ids:
            search_domain = [('id', 'in', record_ids)]

        records = env['dako.password'].search(search_domain, order='vault_id, name, id')
        content = records._dako_export_xlsx()
        now = fields.Datetime.context_timestamp(records, fields.Datetime.now())
        filename = 'credenciales_%s.xlsx' % now.strftime('%Y%m%d_%H%M')
        return request.make_response(content, headers=[
            ('Content-Type', XLSX_CONTENT_TYPE),
            ('Content-Disposition', content_disposition(filename)),
            ('Content-Length', len(content)),
            ('Cache-Control', 'no-store'),
        ])

    def _error_payload(self, exc):
        return json.dumps({
            'code': 200,
            'message': "Odoo Server Error",
            'data': http.serialize_exception(exc),
        })
