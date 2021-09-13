/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2one } from '@mail/model/model_field';
import { clear, insert, link, replace } from '@mail/model/model_field_command';

function factory(dependencies) {

    let nextUploadingId = -1;
    function getAttachmentNextUploadingId() {
        const id = nextUploadingId;
        nextUploadingId -= 1;
        return id;
    }
    class Attachment extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickDownload = this.onClickDownload.bind(this);

            /**
             * Reconciliation between uploading attachment and real attachment.
             */
            if (this.isUploading) {
                return;
            }
            const relatedUploadingAttachment = this.messaging.models['mail.attachment']
                .find(attachment =>
                    attachment.filename === this.filename &&
                    attachment.isUploading
                );
            if (relatedUploadingAttachment) {
                const composers = relatedUploadingAttachment.composers;
                relatedUploadingAttachment.delete();
                this.update({ composers: replace(composers) });
            }
        }


        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} data
         * @return {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('filename' in data) {
                data2.filename = data.filename;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('mimetype' in data) {
                data2.mimetype = data.mimetype;
            }
            if ('name' in data) {
                data2.name = data.name;
            }

            if ('link_preview' in data) {
                data2.linkPreview = data.link_preview[0];
            }

            // relation
            if ('res_id' in data && 'res_model' in data) {
                data2.originThread = insert({
                    id: data.res_id,
                    model: data.res_model,
                });
            }

            if ('url' in data) {
                data2.url = data.url;
            }

            return data2;
        }

        /**
         * @override
         */
        static create(data) {
            const isMulti = typeof data[Symbol.iterator] === 'function';
            const dataList = isMulti ? data : [data];
            for (const data of dataList) {
                if (!data.id) {
                    data.id = getAttachmentNextUploadingId();
                }
            }
            return super.create(...arguments);
        }

        /**
         * Send the attachment for the browser to download.
         */
        download() {
            this.env.services.navigate(`/web/content/ir.attachment/${this.id}/datas`, { download: true });
        }

        /**
         * Handles click on download icon.
         *
         * @param {MouseEvent} ev
         */
        onClickDownload(ev) {
            ev.stopPropagation();
            this.download();
        }

        /**
         * View provided attachment(s), with given attachment initially. Prompts
         * the attachment viewer.
         *
         * @static
         * @param {Object} param0
         * @param {mail.attachment} [param0.attachment]
         * @param {mail.attachments[]} param0.attachments
         * @returns {string|undefined} unique id of open dialog, if open
         */
        static view({ attachment, attachments }) {
            const hasOtherAttachments = attachments && attachments.length > 0;
            if (!attachment && !hasOtherAttachments) {
                return;
            }
            if (!attachment && hasOtherAttachments) {
                attachment = attachments[0];
            } else if (attachment && !hasOtherAttachments) {
                attachments = [attachment];
            }
            if (!attachments.includes(attachment)) {
                return;
            }
            this.messaging.dialogManager.open('mail.attachment_viewer', {
                attachment: link(attachment),
                attachments: replace(attachments),
            });
        }

        /**
         * Remove this attachment globally.
         */
        async remove() {
            if (this.isUnlinkPending) {
                return;
            }
            if (!this.isUploading) {
                this.update({ isUnlinkPending: true });
                try {
                    await this.async(() => this.env.services.rpc({
                        route: `/mail/attachment/delete`,
                        params: {
                            access_token: this.accessToken,
                            attachment_id: this.id,
                        },
                    }, { shadow: true }));
                } finally {
                    this.update({ isUnlinkPending: false });
                }
            } else if (this.uploadingAbortController) {
                this.uploadingAbortController.abort();
            }
            this.delete();
        }

        /**
         * Build the attachment image URL.
         *
         * @return {String}
         */
        imageSource(size = '200x200') {
            return `/web/image/${this.id}/${size}/`;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeDefaultSource() {
            if (this.isImage) {
                return `/web/image/${this.id}?unique=1&amp;signature=${this.checksum}&amp;model=ir.attachment`;
            }
            if (this.isPdf) {
                return `/web/static/lib/pdfjs/web/viewer.html?file=/web/content/${this.id}?model%3Dir.attachment`;
            }
            if (this.isViewable) {
                return `/web/content/${this.id}?model%3Dir.attachment`;
            }
            if (this.isUrlYoutube) {
                const urlArr = this.url.split('/');
                let token = urlArr[urlArr.length - 1];
                if (token.includes('watch')) {
                    token = token.split('v=')[1];
                    const amp = token.indexOf('&');
                    if (amp !== -1) {
                        token = token.substring(0, amp);
                    }
                }
                return `https://www.youtube.com/embed/${token}`;
            }
            return clear();
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeDisplayName() {
            const displayName = this.name || this.filename;
            if (displayName) {
                return displayName;
            }
            return clear();
        }

        /**
         * @private
         * @returns {string}
         */
        _computeDownloadUrl() {
            if (!this.accessToken && this.originThread && this.originThread.model === 'mail.channel') {
                return `/mail/channel/${this.originThread.id}/attachment/${this.id}`;
            }
            const accessToken = this.accessToken ? `?access_token=${this.accessToken}` : '';
            return `/web/content/ir.attachment/${this.id}/datas${accessToken}`;
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeExtension() {
            const extension = this.filename && this.filename.split('.').pop();
            if (extension) {
                return extension;
            }
            return clear();
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasLinkPreview() {
            return !!this.url && !!this.linkPreview;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsPdf() {
            return this.mimetype === 'application/pdf';
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsImage() {
            const imageMimetypes = [
                'image/bmp',
                'image/gif',
                'image/jpeg',
                'image/png',
                'image/svg+xml',
                'image/tiff',
                'image/x-icon',
            ];
            return imageMimetypes.includes(this.mimetype);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsText() {
            const textMimeType = [
                'application/javascript',
                'application/json',
                'text/css',
                'text/html',
                'text/plain',
            ];
            return textMimeType.includes(this.mimetype);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsVideo() {
            const videoMimeTypes = [
                'audio/mpeg',
                'video/x-matroska',
                'video/mp4',
                'video/webm',
            ];
            return videoMimeTypes.includes(this.mimetype);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsUrl() {
            return this.type === 'url' && this.url;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeImageLargeUrl() {
            if (!this.accessToken && this.originThread && this.originThread.model === 'mail.channel') {
                return `/mail/channel/${this.originThread.id}/image/${this.id}/400x400`;
            }
            const accessToken = this.accessToken ? `?access_token=${this.accessToken}` : '';
            return `/web/image/${this.id}/400x400${accessToken}`;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeImageMediumUrl() {
            if (!this.accessToken && this.originThread && this.originThread.model === 'mail.channel') {
                return `/mail/channel/${this.originThread.id}/image/${this.id}/200x200`;
            }
            const accessToken = this.accessToken ? `?access_token=${this.accessToken}` : '';
            return `/web/image/${this.id}/200x200${accessToken}`;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeImageSmallUrl() {
            if (!this.accessToken && this.originThread && this.originThread.model === 'mail.channel') {
                return `/mail/channel/${this.originThread.id}/image/${this.id}/100x100`;
            }
            const accessToken = this.accessToken ? `?access_token=${this.accessToken}` : '';
            return `/web/image/${this.id}/100x100${accessToken}`;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeImageTinyUrl() {
            if (!this.accessToken && this.originThread && this.originThread.model === 'mail.channel') {
                return `/mail/channel/${this.originThread.id}/image/${this.id}/38x38`;
            }
            const accessToken = this.accessToken ? `?access_token=${this.accessToken}` : '';
            return `/web/image/${this.id}/38x38${accessToken}`;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsLinkedToComposer() {
            return this.composers.length > 0;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsViewable() {
            if (this.url && this.url.match('(.png|.jpg|.gif)')) {
                return true;
            }
            return this.isText || this.isImage || this.isVideo || this.isPdf;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsUrlYoutube() {
            return !!this.url && this.url.includes('youtu');
        }

        /**
         * @deprecated
         * @private
         * @returns {string}
         */
        _computeMediaType() {
            return this.mimetype && this.mimetype.split('/').shift();
        }

        /**
         * @private
         * @returns {AbortController|undefined}
         */
        _computeUploadingAbortController() {
            if (this.isUploading) {
                if (!this.uploadingAbortController) {
                    const abortController = new AbortController();
                    abortController.signal.onabort = () => {
                        this.messaging.messagingBus.trigger('o-attachment-upload-abort', {
                            attachment: this
                        });
                    };
                    return abortController;
                }
                return this.uploadingAbortController;
            }
            return;
        }
    }

    Attachment.fields = {
        accessToken: attr(),
        activities: many2many('mail.activity', {
            inverse: 'attachments',
        }),
        /**
         * States the attachment lists that this attachment is linked to.
         */
        attachmentList: many2many('mail.attachment_list', {
            inverse: 'attachments'
        }),
        attachmentViewer: many2many('mail.attachment_viewer', {
            inverse: 'attachments',
        }),
        checkSum: attr(),
        composers: many2many('mail.composer', {
            inverse: 'attachments',
        }),
        defaultSource: attr({
            compute: '_computeDefaultSource',
        }),
        /**
         * States the OWL ref of the "dialog" window.
         */
        dialogRef: attr(),
        displayName: attr({
            compute: '_computeDisplayName',
        }),
        downloadUrl: attr({
           compute: '_computeDownloadUrl',
        }),
        extension: attr({
            compute: '_computeExtension',
        }),
        filename: attr(),
        /**
         * Determines if the attachement has link preview informations.
         */
        hasLinkPreview: attr({
            compute: '_computeHasLinkPreview',
            default: false,
            dependencies:['url'],
        }),
        id: attr({
            required: true,
        }),
        imageLargeUrl: attr({
            compute: '_computeImageLargeUrl',
        }),
        imageMediumUrl: attr({
            compute: '_computeImageMediumUrl',
        }),
        imageSmallUrl: attr({
            compute: '_computeImageSmallUrl',
        }),
        imageTinyUrl: attr({
            compute: '_computeImageTinyUrl',
        }),
        isLinkedToComposer: attr({
            compute: '_computeIsLinkedToComposer',
        }),
        /**
         * States id the attachment is an image.
         */
        isImage: attr({
            compute: '_computeIsImage',
        }),
        /**
         * States if the attachment is a PDF file.
         */
        isPdf: attr({
            compute: '_computeIsPdf',
        }),
        /**
         * States if the attachment is a text file.
         */
        isText: attr({
            compute: '_computeIsText',
        }),
        /**
         * States if the attachment is a video.
         */
        isVideo: attr({
            compute: '_computeIsVideo',
        }),
        /**
         * States if the attachment is an url.
         */
        isUrl: attr({
            compute: '_computeIsUrl',
        }),
        /**
         * True if an unlink RPC is pending, used to prevent multiple unlink attempts.
         */
        isUnlinkPending: attr({
            default: false,
        }),
        isUploading: attr({
            default: false,
        }),
        isViewable: attr({
            compute: '_computeIsViewable',
        }),
        /**
         * Determines if the attachment is a youtube url.
         */
        isUrlYoutube: attr({
            compute: '_computeIsUrlYoutube',
        }),
        /**
         * @deprecated
         */
        mediaType: attr({
            compute: '_computeMediaType',
        }),
        messages: many2many('mail.message', {
            inverse: 'attachments',
        }),
        mimetype: attr({
            default: '',
        }),
        name: attr(),
        /**
         * Contains the link preview information.
         */
        linkPreview: attr(),
        originThread: many2one('mail.thread', {
            inverse: 'originThreadAttachments',
        }),
        size: attr(),
        threads: many2many('mail.thread', {
            inverse: 'attachments',
        }),
        type: attr(),
        /**
         * Abort Controller linked to the uploading process of this attachment.
         * Useful in order to cancel the in-progress uploading of this attachment.
         */
        uploadingAbortController: attr({
            compute: '_computeUploadingAbortController',
        }),
        url: attr(),
    };

    Attachment.modelName = 'mail.attachment';

    return Attachment;
}

registerNewModel('mail.attachment', factory);
