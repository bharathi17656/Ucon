/** @odoo-module **/
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";

async function forwardMessage(message, actionService) {
    console.log("Forwarding message:", message);

    try {
        const action = await rpc('/web/dataset/call_kw', {
            model: 'mail.message',
            method: 'action_wizard_forward',
            args: [message.id],
            kwargs: {},
        });

        console.log("Action received:", action);

        if (action) {
            actionService.doAction(action);  // ✅ Execute the action to open the form
        } else {
            console.error("No action returned from the server.");
        }

    } catch (error) {
        console.error("Error forwarding message:", error);
    }
}

async function sentStageQuotation(message, actionService) {
    console.log("sentStageQuotation message:", message);

    try {
        const action = await rpc('/web/dataset/call_kw', {
            model: 'crm.lead',
            method: 'sent_stage_quotation',
            args: [[],message.res_id,message.model],
            kwargs: {},
        });

        console.log("sentStageQuotation received:", action);
       return action

       

    } catch (error) {
        console.error("Error sentStageQuotation message:", error);
    }
}

async function updateState(message, actionService) {
    console.log("updateState message:", message);

    try {
        const action = await rpc('/web/dataset/call_kw', {
            model: 'crm.lead',
            method: 'quotation_stage_update',
            args: [message.id],
            kwargs: {},
        });

        console.log("updateState received:", action);
        

       

    } catch (error) {
        console.error("Error updateState message:", error);
    }
}

messageActionsRegistry.add("forward_message", {
    condition: () => true,
    icon: "fa fa-forward",
    title: () => _t("Forward Message"),
    async onClick(event) {
        const actionService = event.env.services.action;  
        const message = event.props.message;
        const dialogService = event.env.services.dialog;  // ✅ Correct way to access dialog service

         console.log("Message model:", message.model);  // Debugging
         
        if (message.model === "sale.order" ||  message.model === 'crm.lead') {  // ✅ Only show popup for sale orders
            let res=await  sentStageQuotation(message, actionService)
            setTimeout(()=>{
           
            console.log("thi s is our stage ",res)
            
            if (res == 'draft'){
                
            dialogService.add(ConfirmationDialog, {
                body: _t("Should the Enquiry be changed to 'Quote Submitted'?"),
                confirmClass: "btn-primary",
                confirmLabel: _t("Yes"),
                confirm: () => {
                    console.log("User confirmed update for Sale Order");
                    updateState(message, actionService);  // Update Enquiry Stage
                    forwardMessage(message, actionService);  // Forward Message
                },
                cancelLabel: _t("No"),
                cancel: () => {
                    console.log("User canceled update, only forwarding message");
                    forwardMessage(message, actionService);
                },
            });
        }else {
            // ✅ If not a Sale Order, just forward the message directly
            forwardMessage(message, actionService);
        }

                 },700)
            
        }
        else {
            // ✅ If not a Sale Order, just forward the message directly
            forwardMessage(message, actionService);
        }
    },
    sequence: 0,
});
