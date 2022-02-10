/** @odoo-module **/

import { useService } from '@web/core/utils/hooks';
import { Dialog } from '@web/core/dialog/dialog';
import { ImageSelector, createImages, imageTagNames, imageSpecificClasses } from './image_selector';
import { DocumentSelector, createDocuments, documentTagNames, documentSpecificClasses } from './document_selector';
import { IconSelector, createIcons, iconTagNames, iconSpecificClasses } from './icon_selector';
import { VideoSelector, createVideos, videoTagNames, videoSpecificClasses } from './video_selector';

const { useState } = owl;

export const TABS = {
    IMAGES: {
        id: 'IMAGES',
        title: "Images",
        Component: ImageSelector,
        createElements: createImages,
        mediaSpecificClasses: imageSpecificClasses,
        tagNames: imageTagNames,
    },
    DOCUMENTS: {
        id: 'DOCUMENTS',
        title: "Documents",
        Component: DocumentSelector,
        createElements: createDocuments,
        mediaSpecificClasses: documentSpecificClasses,
        tagNames: documentTagNames,
    },
    ICONS: {
        id: 'ICONS',
        title: "Icons",
        Component: IconSelector,
        createElements: createIcons,
        mediaSpecificClasses: iconSpecificClasses,
        tagNames: iconTagNames,
    },
    VIDEOS: {
        id: 'VIDEOS',
        title: "Videos",
        Component: VideoSelector,
        createElements: createVideos,
        mediaSpecificClasses: videoSpecificClasses,
        tagNames: videoTagNames,
    },
};

export class MediaDialog extends Dialog {
    setup() {
        super.setup();
        this.size = 'modal-xl';
        this.contentClass = 'o_select_media_dialog';
        this.title = this.env._t("Select a media");

        this.rpc = useService('rpc');
        this.orm = useService('orm');

        this.tabs = [];
        this.selectedMedia = useState({});

        const onlyImages = this.props.onlyImages || this.props.multiImages || (this.props.media && this.props.media.parentElement && (this.props.media.parentElement.dataset.oeField === 'image' || this.props.media.parentElement.dataset.oeType === 'image'));
        const noDocuments = onlyImages || this.props.noDocuments;
        const noIcons = onlyImages || this.props.noIcons;
        const noVideos = onlyImages || this.props.noVideos;

        if (!this.props.noImages) {
            this.addTab(TABS.IMAGES, {
                useMediaLibrary: this.props.useMediaLibrary,
                multiSelect: this.props.multiImages,
            });
        }
        if (!noDocuments) {
            this.addTab(TABS.DOCUMENTS);
        }
        if (!noIcons) {
            this.addTab(TABS.ICONS);
        }
        if (!noVideos) {
            this.addTab(TABS.VIDEOS, {
                vimeoPreviewIds: this.props.vimeoPreviewIds,
                isForBgVideo: this.props.isForBgVideo,
            });
        }

        this.state = useState({
            activeTab: this.initialActiveTab,
        });
    }

    get initialActiveTab() {
        if (this.props.activeTab) {
            return this.props.activeTab;
        }
        if (this.props.media) {
            const correspondingTab = Object.keys(TABS).filter(id => TABS[id].tagNames.includes(this.props.media.tagName))[0];
            if (correspondingTab) {
                return correspondingTab;
            }
        }
        return this.tabs[0].id;
    }

    addTab(tab, props) {
        this.selectedMedia[tab.id] = [];
        this.tabs.push({
            ...tab,
            props: {
                ...tab.props,
                ...props,
                id: tab.id,
                resModel: this.props.resModel,
                resId: this.props.resId,
                media: this.props.media,
                selectedMedia: this.selectedMedia,
                selectMedia: this.selectMedia.bind(this),
            },
        });
    }

    async selectMedia(media, { multiSelect = false, save = true } = {}) {
        if (multiSelect) {
            const isMediaSelected = this.selectedMedia[this.state.activeTab].map(({ id }) => id).includes(media.id);
            if (!isMediaSelected) {
                this.selectedMedia[this.state.activeTab].push(media);
            } else {
                this.selectedMedia[this.state.activeTab] = this.selectedMedia[this.state.activeTab].filter(m => m.id !== media.id);
            }
        } else {
            this.selectedMedia[this.state.activeTab] = [media];
            if (save) {
                await this.save();
            }
        }
    }

    async save() {
        const selectedMedia = this.selectedMedia[this.state.activeTab];
        if (selectedMedia.length) {
            const elements = await TABS[this.state.activeTab].createElements(selectedMedia, { rpc: this.rpc, orm: this.orm });
            if (this.props.multiImages) {
                this.props.save(elements);
            } else {
                this.props.save(elements[0]);
            }
        }
        this.close();
    }
}
MediaDialog.bodyTemplate = 'web_editor.MediaDialogBody';
MediaDialog.footerTemplate = 'web_editor.MediaDialogFooter';
MediaDialog.components = {
    ...Object.keys(TABS).map(key => TABS[key].Component),
};
