/** @odoo-module **/

// ensure components are registered beforehand.
import '@mail/components/chat_window_manager/chat_window_manager';
import '@mail/components/dialog_manager/dialog_manager';
import { DiscussContainer } from '@mail/components/discuss_container/discuss_container';
import { messagingService } from '@mail/services/messaging_service';
import { makeMessagingValuesProviderService } from '@mail/services/messaging_values_provider_service';
import { systrayService } from '@mail/services/systray_service';
import { wowlEnvProviderService } from '@mail/services/wowl_env_provider_service';
import { getMessagingComponent } from '@mail/utils/messaging_component';

import { registry } from '@web/core/registry';

const serviceRegistry = registry.category('services');
serviceRegistry.add('messaging', messagingService);
serviceRegistry.add('messagingValuesProvider', makeMessagingValuesProviderService());
serviceRegistry.add('systray_service', systrayService);
serviceRegistry.add('wowlEnvProviderService', wowlEnvProviderService);

registry.category('actions').add('mail.action_discuss', DiscussContainer);

const mainComponentRegistry = registry.category('main_components');
mainComponentRegistry.add('ChatWindowManager', {
    Component: getMessagingComponent('ChatWindowManager'),
});
mainComponentRegistry.add('DialogManager', {
    Component: getMessagingComponent('DialogManager'),
});

