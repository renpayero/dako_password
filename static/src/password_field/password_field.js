import { Component, onWillUnmount, onWillUpdateProps, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { debounce } from "@web/core/utils/timing";
import { useBus, useService } from "@web/core/utils/hooks";
import { useInputField } from "@web/views/fields/input_field_hook";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const MASK = "•".repeat(8);

/**
 * Widget for `dako.password.password_input`. The stored password never comes with the
 * record: the eye and copy buttons request it from the reveal service, which logs it.
 *
 * - read only (list, kanban): mask, reveal, copy;
 * - saved record in a form: the same plus "Cambiar", which opens the input;
 * - new record or changing: empty input with show, generate, copy and cancel.
 */
export class DakoPasswordField extends Component {
    static template = "dako_password.PasswordField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.reveal = useService("dako_password.reveal");
        this.revealed = useState(this.reveal.state);
        this.state = useState({ editing: false, showTyped: false });
        this.inputRef = useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            refName: "input",
        });
        // Live strength: push the typed value to the record (and its onchange) while typing.
        this.pushTypedValue = debounce(() => this.commitTypedValue(), 300);
        // Before a save, useInputField commits the input: a late debounced push would
        // put the saved value back in the record and leave it dirty.
        useBus(this.props.record.model.bus, "NEED_LOCAL_CHANGES", () => this.pushTypedValue.cancel());

        useRecordObserver((record) => {
            // A save or a discard leaves the field empty and the record clean.
            if (!record.dirty && !record.data[this.props.name]) {
                this.pushTypedValue.cancel();
                this.state.editing = false;
                this.state.showTyped = false;
            }
        });
        onWillUpdateProps((nextProps) => {
            // Same component, other record (form pager): hide what was revealed.
            if (nextProps.record.resId !== this.props.record.resId) {
                if (this.props.record.resId) {
                    this.reveal.hide([this.props.record.resId]);
                }
                this.state.editing = false;
                this.state.showTyped = false;
            }
        });
        onWillUnmount(() => {
            this.pushTypedValue.cancel();
            if (this.props.record.resId) {
                this.reveal.hide([this.props.record.resId]);
            }
        });
    }

    isEditing() {
        return !this.props.readonly && (!this.props.record.resId || this.state.editing);
    }

    isRevealed() {
        // Read through the useState proxy so that the component re-renders on reveal.
        return this.revealed.values[this.props.record.resId] !== undefined;
    }

    displayValue() {
        const resId = this.props.record.resId;
        if (!resId) {
            return "";
        }
        return this.isRevealed() ? this.revealed.values[resId] : MASK;
    }

    typedValue() {
        return this.inputRef.el?.value || "";
    }

    async commitTypedValue() {
        const value = this.typedValue() || false;
        if (value !== (this.props.record.data[this.props.name] || false)) {
            await this.props.record.update({ [this.props.name]: value });
        }
    }

    onInput() {
        this.pushTypedValue();
    }

    async onClickReveal() {
        const resId = this.props.record.resId;
        if (this.isRevealed()) {
            this.reveal.hide([resId]);
        } else {
            await this.reveal.reveal([resId]);
        }
    }

    async onClickCopy() {
        const copied = await this.reveal.copy(this.props.record.resId);
        if (copied) {
            this.notification.add(_t("Contraseña copiada al portapapeles."), { type: "success" });
        } else {
            this.notification.add(
                _t("El navegador no dejó copiar: la contraseña queda visible 30 segundos."),
                { type: "warning" }
            );
        }
    }

    async onClickCopyTyped() {
        const value = this.typedValue();
        if (!value) {
            return;
        }
        try {
            await browser.navigator.clipboard.writeText(value);
            this.notification.add(_t("Contraseña copiada al portapapeles."), { type: "success" });
        } catch {
            this.state.showTyped = true;
            this.notification.add(
                _t("El navegador no dejó copiar: la contraseña quedó visible."),
                { type: "warning" }
            );
        }
    }

    onClickChange() {
        this.state.editing = true;
        this.state.showTyped = false;
    }

    async onClickCancel() {
        this.pushTypedValue.cancel();
        this.state.editing = false;
        this.state.showTyped = false;
        // Nothing typed: leave the record untouched (an update would mark it dirty).
        if (this.props.record.data[this.props.name]) {
            await this.props.record.update({ [this.props.name]: false });
        }
    }

    onClickToggleTyped() {
        this.state.showTyped = !this.state.showTyped;
    }

    async onClickGenerate() {
        const value = await this.orm.call("dako.password", "generate_password", []);
        this.pushTypedValue.cancel();
        if (this.inputRef.el) {
            this.inputRef.el.value = value;
        }
        this.state.showTyped = true;
        await this.props.record.update({ [this.props.name]: value });
        this.notification.add(_t("Contraseña generada: guardá para aplicarla."), { type: "info" });
    }
}

export const dakoPasswordField = {
    component: DakoPasswordField,
    displayName: _t("Contraseña protegida"),
    supportedTypes: ["char"],
    // [min, max] in list views: the mask, or a revealed password, plus two buttons.
    listViewWidth: [160, 300],
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("dako_password", dakoPasswordField);
