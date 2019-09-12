odoo.define('mail.component.DropZone', function () {
'use strict';

class DropZone extends owl.store.ConnectedComponent {
    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.template = 'mail.component.DropZone';
        this.state = { draggingInside: false };
        this._globalDragOverListener = ev => this._onDragOver(ev);
        this._globalDropListener = ev => this._onDrop(ev);
    }

    mounted() {
        document.addEventListener('dragover', this._globalDragOverListener);
        document.addEventListener('drop', this._globalDropListener);
    }

    /**
     * Making sure that dragging content is external files.
     * Ignoring other content draging like text.
     *
     * @private
     * @param {DataTransfer} dataTransfer
     * @returns {boolean}
     */
    _isDragSourceExternalFile(dataTransfer) {
        const DragDataType = dataTransfer.types;
        if (DragDataType.constructor === DOMStringList) {
            return DragDataType.contains('Files');
        }
        if (DragDataType.constructor === Array) {
            return DragDataType.indexOf('Files') !== -1;
        }
        return false;
    }

    /**
     * @param {Event} e
     * @private
     */
    _isInDropZone(e) {
        return this.el === e.target;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onDragOver(e) {
        e.preventDefault();
        this.state.draggingInside = this._isInDropZone(e);
        e.dataTransfer.dropEffect = "copy";
    }

    _onDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        if (this._isInDropZone(e)) {
            if (this._isDragSourceExternalFile(e.dataTransfer)) {
                this.trigger('o-dropzone-files-dropped', { files: e.dataTransfer.files });
            }
        }
        else {
            this.trigger('o-dropzone-outside-drop', { originalEvent: e });
        }
    }
}

return DropZone;

});
