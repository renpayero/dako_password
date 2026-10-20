# -*- coding: utf-8 -*-


def migrate(cr, version):
    """From 17.0.1.x: password_changed_date did not exist.

    Creating the column fills it with its default (the upgrade time), so every
    credential would claim it was changed today. The last write of each
    credential is the closest known date of its last password change.
    """
    if not version:
        return
    cr.execute("""
        UPDATE dako_password
           SET password_changed_date = COALESCE(write_date, create_date)
    """)
