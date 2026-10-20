import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { CharField, charField } from "@web/views/fields/char/char_field";

const WEB_ADDRESS = /^https?:\/\/\S+$/i;

/**
 * Text that is copied often (access, user): a link when it is a web address, plain
 * monospace text otherwise (hosts, IPs, "ssh root@server"), always with a copy button.
 * Unlike the core url widget, it never turns a host into an http:// link.
 */
export class DakoCopyField extends CharField {
    static template = "dako_password.CopyField";
    static components = { ...CharField.components, CopyButton };

    value() {
        return this.props.record.data[this.props.name] || "";
    }

    isWebAddress() {
        return WEB_ADDRESS.test(this.value().trim());
    }
}

export const dakoCopyField = {
    ...charField,
    component: DakoCopyField,
    displayName: _t("Texto copiable"),
    // In list views the copy button needs room next to the text.
    listViewWidth: [140],
};

registry.category("fields").add("dako_password_copy", dakoCopyField);
