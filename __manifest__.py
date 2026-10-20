# -*- coding: utf-8 -*-
{
    'name': 'Dako Password Manager',
    'version': '19.0.2.0.1',
    'summary': 'Credenciales del equipo en vaults, con control de acceso y auditoría',
    'description': """
Gestor de credenciales del equipo
=================================

Cada credencial (servicio, propósito, acceso, usuario, contraseña, criticidad y notas)
vive en un vault, y solo la ven los usuarios anotados en ese vault. El grupo
*Administrador de contraseñas* ve y gestiona todos los vaults.

Cómo se protege la contraseña
-----------------------------
* El campo almacenado no se puede leer por las vías normales (lectura, exportación,
  búsqueda, agrupación): solo se entrega al revelarla o copiarla, y cada entrega queda
  en el registro de accesos, que consulta el Administrador desde *Auditoría*.
* Los cambios (incluido "cambió la contraseña", nunca su valor) quedan en el chatter.
* Las bases neutralizadas (staging de Odoo.sh) reemplazan todas las contraseñas.

Riesgos que el módulo no cubre
------------------------------
* Quien puede correr código como superusuario lee las contraseñas sin dejar registro:
  los administradores (Ajustes), quien crea acciones de servidor o campos con Studio,
  y los editores de plantillas de correo (grupo *Mail Template Editor*), que pueden
  usar sudo() dentro de una plantilla. Mantener activo "Restringir el renderizado de
  plantillas" (Ajustes > Conversaciones) y ese grupo solo en administradores.
* Quien accede a la base de datos o a sus copias de seguridad ve las contraseñas
  guardadas en texto plano.
* Lo que se copia queda en el portapapeles del sistema operativo.
* El registro distingue "Vio" de "Copió" según lo que informa el navegador; la entrega
  de la contraseña queda registrada siempre.
""",
    'author': 'DakoDev',
    'category': 'Productivity',
    'depends': ['mail'],
    'data': [
        'security/dako_password_security.xml',
        'security/ir.model.access.csv',
        'views/dako_password_views.xml',
        'views/dako_password_vault_views.xml',
        'views/dako_password_access_log_views.xml',
        'views/dako_password_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dako_password/static/src/**/*',
        ],
        'web.assets_tests': [
            'dako_password/static/tests/tours/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
