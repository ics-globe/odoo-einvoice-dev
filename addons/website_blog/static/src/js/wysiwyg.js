odoo.define('website_blog.wysiwyg', function (require) {
'use strict';

const core = require('web.core');
const Wysiwyg = require('web_editor.wysiwyg');
const snippetsEditor = require('web_editor.snippet.editor');
require('website.editor.snippets.options');

Wysiwyg.include({
    custom_events: Object.assign({}, Wysiwyg.prototype.custom_events, {
        'set_blog_post_updated_tags': '_onSetBlogPostUpdatedTags',
    }),

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.blogTagsPerBlogPost = {};
    },
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);

        $('.js_tweet, .js_comment').off('mouseup').trigger('mousedown');

        const postContentEl = document.querySelector('.o_wblog_post_content_field');
        if (postContentEl) {
            // Adjust size of some elements once some content changes:
            // - the snippet order changes because the first text might become
            //   a different one,
            // - the class changes because this is where the content width
            //   option is set.
            this._widthObserver = new MutationObserver(records => {
                const consideredUpdates = _.any(records, record => {
                    // Only consider DOM structure modification and class
                    // changes.
                    return record.type === 'childList'
                        || (record.type === 'attributes' && record.attributeName === 'class');
                });
                if (consideredUpdates) {
                    core.bus.trigger('blog_width_update');
                }
            });
            this._widthObserver.observe(postContentEl, {
                childList: true,
                subtree: true,
                attributes: true,
            });
        }
    },
    /**
     * @override
     */
    destroy() {
        if (this._widthObserver) {
            this._widthObserver.disconnect();
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _saveViewBlocks() {
        const ret = await this._super(...arguments);
        await this._saveBlogTags(); // Note: important to be called after save otherwise cleanForSave is not called before
        return ret;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Saves the blog tags in the database.
     *
     * @private
     */
    async _saveBlogTags() {
        for (const [key, tags] of Object.entries(this.blogTagsPerBlogPost)) {
            const proms = tags.filter(tag => typeof tag.id === 'string').map(tag => {
                return this._rpc({
                    model: 'blog.tag',
                    method: 'create',
                    args: [{
                        'name': tag.name,
                    }],
                });
            });
            const createdIDs = await Promise.all(proms);

            await this._rpc({
                model: 'blog.post',
                method: 'write',
                args: [parseInt(key), {
                    'tag_ids': [[6, 0, tags.filter(tag => typeof tag.id === 'number').map(tag => tag.id).concat(createdIDs)]],
                }],
            });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSetBlogPostUpdatedTags: function (ev) {
        this.blogTagsPerBlogPost[ev.data.blogPostID] = ev.data.tags;
    },
});

snippetsEditor.SnippetsMenu.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeSnippetTemplates: function (html) {
        this._super(...arguments);
        const postContentEl = document.getElementById('o_wblog_post_content');
        if (postContentEl) {
            // Patch all droppable snippet templates.
            const usesRegularCover = document.body.querySelector('#o_wblog_post_main.container');
            const targetClass = usesRegularCover ? 'container' : 'o_container_small';
            const removedClass = usesRegularCover ? 'o_container_small' : 'container';
            for (const snippetEl of this.$snippets) {
                snippetEl.querySelectorAll([
                    `section .${removedClass}`,
                    'section .container-fluid',
                ]).forEach(el => {
                    el.classList.remove('container-fluid', removedClass);
                    el.classList.add(targetClass);
                });
            }
        }
    },
});

});
