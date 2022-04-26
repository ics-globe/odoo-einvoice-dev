/** @odoo-module **/

import { data } from 'mail.discuss_public_channel_template';

// ensure components are registered beforehand.
import '@mail/components/dialog_manager/dialog_manager';
import '@mail/components/discuss_public_view/discuss_public_view';
import { messagingService } from '@mail/services/messaging_service';
import { makeMessagingValuesProviderService } from '@mail/services/messaging_values_provider_service';
import { wowlEnvProviderService } from '@mail/services/wowl_env_provider_service';
import { getMessagingComponent } from '@mail/utils/messaging_component';

import { processTemplates } from '@web/core/assets';
import { MainComponentsContainer } from '@web/core/main_components_container';
import { registry } from '@web/core/registry';
import { makeEnv, startServices } from '@web/env';
import {
    makeLegacyCrashManagerService,
    makeLegacyDialogMappingService,
    makeLegacyNotificationService,
    makeLegacyRpcService,
    makeLegacySessionService,
    mapLegacyEnvToWowlEnv,
} from '@web/legacy/utils';
import { session } from '@web/session';

import * as AbstractService from 'web.AbstractService';
import * as legacyEnv from 'web.env';
import * as legacySession from 'web.session';

const { Component, mount, whenReady } = owl;

Component.env = legacyEnv;

(async function boot() {
    await whenReady();
    AbstractService.prototype.deployServices(Component.env);
    const serviceRegistry = registry.category('services');
    serviceRegistry.add('legacy_rpc', makeLegacyRpcService(Component.env));
    serviceRegistry.add('legacy_session', makeLegacySessionService(Component.env, legacySession));
    serviceRegistry.add('legacy_notification', makeLegacyNotificationService(Component.env));
    serviceRegistry.add('legacy_crash_manager', makeLegacyCrashManagerService(Component.env));
    serviceRegistry.add('legacy_dialog_mapping', makeLegacyDialogMappingService(Component.env));
    serviceRegistry.add('messaging', messagingService);
    serviceRegistry.add('messagingValuesProvider', makeMessagingValuesProviderService({ autofetchPartnerImStatus: false }));
    serviceRegistry.add('wowlEnvProviderService', wowlEnvProviderService);

    registry.category('main_components').add('DialogManager', {
        Component: getMessagingComponent('DialogManager'),
    });
    await legacySession.is_bound;
    Object.assign(odoo, {
        info: {
            db: session.db,
            server_version: session.server_version,
            server_version_info: session.server_version_info,
            isEnterprise: session.server_version_info.slice(-1)[0] === 'e',
        },
        isReady: false,
    });
    const env = makeEnv();
    const [, templates] = await Promise.all([
        startServices(env),
        odoo.loadTemplatesPromise.then(processTemplates),
    ]);
    mapLegacyEnvToWowlEnv(Component.env, env);
    odoo.isReady = true;
    await mount(MainComponentsContainer, document.body, { env, templates, dev: env.debug });
    createAndMountDiscussPublicView(env, templates);
})();

async function createAndMountDiscussPublicView(env, templates) {
    const messaging = await env.services.messaging.get();
    messaging.models['Thread'].insert(messaging.models['Thread'].convertData(data.channelData));
    const discussPublicView = messaging.models['DiscussPublicView'].create(data.discussPublicViewData);
    if (discussPublicView.shouldDisplayWelcomeViewInitially) {
        discussPublicView.switchToWelcomeView();
    } else {
        discussPublicView.switchToThreadView();
    }
    const DiscussPublicView = getMessagingComponent('DiscussPublicView');
    await mount(DiscussPublicView, document.body, {
        templates,
        env,
        dev: !!env.debug,
        props: {
            record: discussPublicView,
        },
    });
}
