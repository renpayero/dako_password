/** @odoo-module **/

import { onWillStart, useState } from "@odoo/owl";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

export class DakoPasswordListController extends ListController {
    setup() {
        super.setup();
        this.ui = useService("ui");
        this.user = useService("user");
        this.reveal = useService("dako_password.reveal");
        this.revealed = useState(this.reveal.state);
        this.dakoState = useState({ canExport: false });
        onWillStart(async () => {
            this.dakoState.canExport = await this.user.hasGroup("base.group_allow_export");
        });
    }

    visibleResIds() {
        return this.model.root.records.map((record) => record.resId).filter(Boolean);
    }

    allRevealed() {
        const resIds = this.visibleResIds();
        // Read through the useState proxy so that the buttons re-render on reveal.
        return resIds.length > 0 && resIds.every((resId) => this.revealed.values[resId] !== undefined);
    }

    async onClickRevealAll() {
        const resIds = this.visibleResIds();
        if (!resIds.length) {
            return;
        }
        if (this.allRevealed()) {
            this.reveal.hide(resIds);
        } else {
            await this.reveal.reveal(resIds);
        }
    }

    /**
     * Export the selected credentials, or everything the current search shows (all
     * pages, not only the visible one).
     */
    async onClickExportXlsx() {
        const root = this.model.root;
        const resIds = root.isDomainSelected ? [] : root.selection.map((record) => record.resId);
        this.ui.block();
        try {
            await download({
                url: "/dako_password/export/xlsx",
                data: {
                    domain: JSON.stringify(root.domain),
                    ids: JSON.stringify(resIds),
                },
            });
        } finally {
            this.ui.unblock();
        }
    }
}

export const dakoPasswordListView = {
    ...listView,
    Controller: DakoPasswordListController,
    buttonTemplate: "dako_password.ListView.Buttons",
};

registry.category("views").add("dako_password_list", dakoPasswordListView);
