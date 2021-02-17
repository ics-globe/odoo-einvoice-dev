/** @odoo-module **/

import { insert, insertAndReplace } from '@mail/model/model_field_command';
import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('attachment_link_preview_tests.js');

QUnit.test('auto layout with link preview', async function(assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const irAttachmentId1 = pyEnv['ir.attachment'].create({
        description: 'test description',
        mimetype: 'application/o-linkpreview',
        name: "https://tenor.com/view/gato-gif-18532922",
        url: "https://tenor.com/view/gato-gif-18532922",
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['mail.message'].create(
        {
            attachment_ids: [irAttachmentId1],
            model: "mail.channel",
            res_id: mailChannelId1,
        }
    );
    const { afterEvent, createThreadViewComponent, messaging } = await start();
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: insert({ id: mailChannelId1, model: 'mail.channel' }),
    });
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            createThreadViewComponent(threadViewer.threadView);
        },
        message: "thread become loaded with messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === mailChannelId1
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_AttachmentLinkPreview',
        "Attachment is a link preview"
    );
});

QUnit.test('simplest layout', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const irAttachmentId1 = pyEnv['ir.attachment'].create({
        description: 'test description',
        mimetype: 'application/o-linkpreview-with-thumbnail',
        name: "https://tenor.com/view/gato-gif-18532922",
        url: "https://tenor.com/view/gato-gif-18532922",
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['mail.message'].create(
        {
            attachment_ids: [irAttachmentId1],
            model: "mail.channel",
            res_id: mailChannelId1,
        }
    );
    const { afterEvent, createThreadViewComponent, messaging } = await start({ debug: true });
    const threadViewer = messaging.models['ThreadViewer'].create({
        hasThreadView: true,
        qunitTest: insertAndReplace(),
        thread: insert({ id: mailChannelId1, model: 'mail.channel' }),
    });
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            createThreadViewComponent(threadViewer.threadView);
        },
        message: "thread become loaded with messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === mailChannelId1
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_AttachmentLinkPreview',
        "should have attachment link preview in DOM"
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentLinkPreview_title',
        "Should display the page title"
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentLinkPreview_linkImage',
        "attachment should have an image part"
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentLinkPreview_description',
        "attachment should show the link description"
    );
});

});
});
