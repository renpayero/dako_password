/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CharField, charField } from "@web/views/fields/char/char_field";

const WEB_ADDRESS = /^https?:\/\/\S+$/i;

/**
 * Text that is copied often (access, user): a link when it is a web address, plain
 * monospace text otherwise (hosts, IPs, "ssh root@server"), always with a copy button.
 * Unlike the core url widget, it never turns a host into an http:// link.
 *
 * Odoo 17: the core CopyButton is always a btn-primary with its own icon, so the copy
 * button is drawn here, like the ones of the password widget.
 */
export class DakoCopyField extends CharField {
    static template = "dako_password.CopyField";

    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    value() {
        return this.props.record.data[this.props.name] || "";
    }

    isWebAddress() {
        return WEB_ADDRESS.test(this.value().trim());
    }

    async onClickCopy() {
        try {
            await browser.navigator.clipboard.writeText(this.value());
            this.notification.add(_t("Copiado"), { type: "success" });
        } catch {
            this.notification.add(_t("El navegador no dejó copiar."), { type: "warning" });
        }
    }
}

export const dakoCopyField = {
    ...charField,
    component: DakoCopyField,
    displayName: _t("Texto copiable"),
};

registry.category("fields").add("dako_password_copy", dakoCopyField);
