/** @odoo-module **/

import { useService } from '@web/core/utils/hooks';
import { useWowlService } from '@web/legacy/utils';
import { Dialog } from '@web/core/dialog/dialog';
import { ImageSelector, createImages, imageTagNames, imageSpecificClasses } from './image_selector';
import { DocumentSelector, createDocuments, documentTagNames, documentSpecificClasses } from './document_selector';
import { IconSelector, createIcons, iconTagNames, iconSpecificClasses } from './icon_selector';
import { VideoSelector, createVideos, videoTagNames, videoSpecificClasses } from './video_selector';

const { Component, useState, useEffect, xml } = owl;

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

export class MediaDialog extends Component {
    setup() {
        this.size = 'xl';
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

        this.initialIconClasses = [];

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
            this.addTab(TABS.ICONS, {
                setInitialIconClasses: (classes) => this.initialIconClasses.push(...classes),
            });
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
                multiImages: this.props.multiImages,
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
            elements.forEach(element => {
                if (this.props.media) {
                    element.classList.add(...this.props.media.classList);
                    const style = this.props.media.getAttribute('style');
                    if (style) {
                        element.setAttribute('style', style);
                    }
                    if (this.props.media.dataset.shape) {
                        element.dataset.shape = this.props.media.dataset.shape;
                    }
                    if (this.props.media.dataset.shapeColors) {
                        element.dataset.shapeColors = this.props.media.dataset.shapeColors;
                    }
                }
                element.classList.add(...TABS[this.state.activeTab].mediaSpecificClasses);
                for (const otherTab of Object.keys(TABS).filter(key => key !== this.state.activeTab)) {
                    element.classList.remove(...TABS[otherTab].mediaSpecificClasses);
                }
                element.classList.remove(...this.initialIconClasses);
                element.classList.remove('o_modified_image_to_save');
                element.classList.remove('oe_edited_link');
            });
            if (this.props.multiImages) {
                this.props.save(elements);
            } else {
                this.props.save(elements[0]);
            }
        }
        this.props.close();
    }
}
MediaDialog.template = 'web_editor.MediaDialog';
MediaDialog.components = {
    ...Object.keys(TABS).map(key => TABS[key].Component),
    Dialog,
};

export class MediaDialogWrapper extends Component {
    setup() {
        this.dialogs = useWowlService('dialog');

        useEffect(() => {
            this.dialogs.add(MediaDialog, this.props);
        }, () => []);
    }
}
MediaDialogWrapper.template = xml``;
