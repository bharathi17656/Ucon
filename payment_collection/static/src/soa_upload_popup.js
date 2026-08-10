/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SOAUploadPopup extends Component {
    setup() {
        this.state = useState({
            employee: "",
            division: "",
            customers: [
                { name: "Vector Engineering", amount: 100000 },
                { name: "HBK", amount: 200000 },
                { name: "GULF Qatar", amount: 55000 },
            ],
        });
        this.actionService = useService("action");
    }

    close() {
        this.env.services.action.doAction({ type: "ir.actions.act_window_close" });
    }

    onChangeEmployee(ev) {
        this.state.employee = ev.target.value;
    }

    onChangeDivision(ev) {
        this.state.division = ev.target.value;
    }

    onUploadFile(ev, customer) {
        alert(`Upload for ${customer.name}`);
    }
}

SOAUploadPopup.template = "payment_collection.SOAUploadPopup";
registry.category("actions").add("open_soa_upload_wizard", SOAUploadPopup);
