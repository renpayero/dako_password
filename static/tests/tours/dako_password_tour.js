import { registry } from "@web/core/registry";

const ROW = ".o_data_row:contains('Banco A')";
const CARD = ".o_kanban_record:contains('Banco A')";

// The headless test browser has no clipboard permission: stub it to test both outcomes.
function stubClipboard(allowed) {
    return {
        content: allowed ? "The browser accepts the clipboard" : "The browser refuses the clipboard",
        trigger: "body",
        run() {
            const answer = allowed
                ? async () => {}
                : async () => {
                      throw new DOMException("Denied", "NotAllowedError");
                  };
            navigator.clipboard.write = answer;
            navigator.clipboard.writeText = answer;
        },
    };
}

registry.category("web_tour.tours").add("dako_password_desktop", {
    steps: () => [
        {
            content: "The search panel only lists the vaults of the user",
            trigger: ".o_search_panel:contains('Vault A'):not(:contains('Vault B'))",
        },
        {
            content: "The password starts masked",
            trigger: `${ROW} .o_dako_password_masked`,
        },
        {
            trigger: `${ROW} .o_dako_password_reveal`,
            run: "click",
        },
        {
            content: "Revealing does not open the record",
            trigger: `.o_list_view ${ROW} .o_dako_password_value:contains('Secreto-A-2026')`,
        },
        {
            trigger: `${ROW} .o_dako_password_reveal`,
            run: "click",
        },
        {
            trigger: `${ROW} .o_dako_password_masked`,
        },
        stubClipboard(true),
        {
            trigger: `${ROW} .o_dako_password_copy`,
            run: "click",
        },
        {
            content: "Copied without revealing it",
            trigger: ".o_notification:contains('copiada al portapapeles')",
        },
        {
            trigger: `.o_list_view ${ROW} .o_dako_password_masked`,
        },
        {
            trigger: ".o_dako_password_reveal_all:contains('Mostrar todas')",
            run: "click",
        },
        {
            trigger: `${ROW} .o_dako_password_value:contains('Secreto-A-2026')`,
        },
        {
            trigger: ".o_dako_password_reveal_all:contains('Ocultar todas')",
            run: "click",
        },
        {
            trigger: `${ROW} .o_dako_password_masked`,
        },
        stubClipboard(false),
        {
            trigger: `${ROW} .o_dako_password_copy`,
            run: "click",
        },
        {
            content: "When the browser refuses, the password is shown to copy it by hand",
            trigger: ".o_notification:contains('no dejó copiar')",
        },
        {
            trigger: `${ROW} .o_dako_password_value:contains('Secreto-A-2026')`,
        },
        {
            content: "The export button is there for users allowed to export",
            trigger: ".o_dako_password_export",
        },
        {
            trigger: `${ROW} td[name='name']`,
            run: "click",
        },
        {
            content: "Leaving the list hides the password again",
            trigger: ".o_form_view .o_field_widget[name='password_input'] .o_dako_password_masked",
        },
        {
            trigger: ".o_form_view .o_dako_password_change",
            run: "click",
        },
        {
            trigger: ".o_form_view input.o_dako_password_input",
            run: "edit Cambiada-Tour-2026!",
        },
        {
            content: "Strength follows the typed password",
            trigger: ".o_form_view .o_field_widget[name='strength'] .badge:contains('Fuerte')",
        },
        {
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "After saving, the password is masked again",
            trigger: ".o_form_view .o_dako_password_change",
        },
        {
            content: "The change is in the chatter, without the value",
            trigger: ".o-mail-Message:contains('Cambió la contraseña.'):not(:contains('Cambiada-Tour'))",
        },
    ],
});

registry.category("web_tour.tours").add("dako_password_mobile", {
    steps: () => [
        {
            content: "On a phone the credentials open as cards",
            trigger: `.o_kanban_view ${CARD}`,
        },
        {
            trigger: `${CARD} .o_dako_password_reveal`,
            run: "click",
        },
        {
            content: "Revealing from the card does not open the record",
            trigger: `.o_kanban_view ${CARD} .o_dako_password_value:contains('Secreto-A-2026')`,
        },
        stubClipboard(true),
        {
            trigger: `${CARD} .o_dako_password_copy`,
            run: "click",
        },
        {
            trigger: ".o_notification:contains('copiada al portapapeles')",
        },
        {
            trigger: `.o_kanban_view ${CARD}`,
        },
    ],
});
