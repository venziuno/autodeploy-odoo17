/** @odoo-module **/
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

patch(UserMenu.prototype, {
    setup() {
        super.setup();

        const userMenuRegistry = registry.category("user_menuitems");
        const menuItemsToRemove = ["documentation", "shortcuts", "support", "odoo_account"];

        menuItemsToRemove.forEach((menuItem) => {
            userMenuRegistry.remove(menuItem);
        });
    },
}); 