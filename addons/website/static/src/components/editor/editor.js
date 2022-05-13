/** @odoo-module */
// Legacy services
import legacyEnv from 'web.commonEnv';
import { useService } from '@web/core/utils/hooks';
import { WysiwygAdapterComponent } from '../wysiwyg_adapter/wysiwyg_adapter';

const { markup, Component, useState, useChildSubEnv, useEffect, onWillStart } = owl;

export class WebsiteEditorComponent extends Component {
    setup() {
        this.websiteService = useService('website');
        this.notificationService = useService('notification');

        this.websiteContext = useState(this.websiteService.context);
        this.state = useState({
            reloading: false,
            showWysiwyg: this.websiteContext.isPublicRootReady,
        });

        useChildSubEnv(legacyEnv);

        onWillStart(async () => {
            this.Wysiwyg = await this.websiteService.loadWysiwyg();
        });

        useEffect(isPublicRootReady => {
            if (isPublicRootReady) {
                this.publicRootReady();
            }
        }, () => [this.websiteContext.isPublicRootReady]);
    }

    publicRootReady() {
        if (this.websiteService.currentWebsite.metadata.translatable) {
            this.websiteContext.edition = false;
        } else {
            this.state.showWysiwyg = true;
        }
    }

    wysiwygReady() {
        this.websiteContext.snippetsLoaded = true;
        this.state.reloading = false;
    }

    willReload(widgetEl) {
        if (widgetEl) {
            widgetEl.querySelectorAll('#oe_manipulators').forEach(el => el.remove());
            widgetEl.querySelectorAll('we-input input').forEach(input => {
                input.setAttribute('value', input.closest('we-input').dataset.selectStyle || '');
            });
            this.loadingDummy = markup(widgetEl.innerHTML);
        }
        this.state.reloading = true;
    }

    async reload(snippetOptionSelector, url) {
        this.notificationService.add(this.env._t("Your modifications were saved to apply this option."), {
            title: this.env._t("Content saved."),
            type: 'success'
        });
        this.state.showWysiwyg = false;
        await this.props.reloadIframe(url);
        this.reloadSelector = snippetOptionSelector;
    }

    async quit() {
        await this.props.reloadIframe();
        document.body.classList.remove('editor_has_snippets');
        this.websiteContext.snippetsLoaded = false;
        setTimeout(() => {
            this.destroyAfterTransition();
        }, 400);
    }

    destroyAfterTransition() {
        this.websiteContext.edition = false;
    }
}
WebsiteEditorComponent.components = { WysiwygAdapterComponent };
WebsiteEditorComponent.template = 'website.WebsiteEditorComponent';
