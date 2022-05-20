/** @odoo-module **/

import ActivityMenu from '@mail/js/systray/systray_activity_menu';
import { start } from '@mail/../tests/helpers/test_utils';

import { Items as legacySystrayItems } from 'web.SystrayMenu';
import testUtils from 'web.test_utils';

QUnit.module('note', {}, function () {
QUnit.module("ActivityMenu");

QUnit.test('note activity menu widget: create note from activity menu', async function (assert) {
    assert.expect(15);

    legacySystrayItems.push(ActivityMenu);
    const { target } = await start();

    assert.containsOnce(target, '.o_mail_systray_item',
        'should contain an instance of widget');
    await testUtils.nextTick();
    assert.strictEqual(target.querySelector('.o_notification_counter').innerText, '0',
        "should not have any activity notification initially");

    // toggle quick create for note
    await testUtils.dom.click(target.querySelector('.dropdown-toggle[title="Activities"]'));
    assert.containsOnce(target, '.o_no_activity',
        "should not have any activity preview");
    assert.doesNotHaveClass(target.querySelector('.o_note_show'), 'd-none',
        'ActivityMenu should have Add new note CTA');
    await testUtils.dom.click(target.querySelector('.o_note_show'));
    assert.hasClass(target.querySelector('.o_note_show'), 'd-none',
        'ActivityMenu should hide CTA when entering a new note');
    assert.doesNotHaveClass(target.querySelector('.o_note'), 'd-none',
        'ActivityMenu should display input for new note');

    // creating quick note without date
    await testUtils.fields.editInput(target.querySelector("input.o_note_input"), "New Note");
    await testUtils.dom.click(target.querySelector(".o_note_save"));
    assert.strictEqual(target.querySelector('.o_notification_counter').innerText, '1',
        "should increment activity notification counter after creating a note");
    assert.containsOnce(target, '.o_mail_preview[data-res_model="note.note"]',
        "should have an activity preview that is a note");
    assert.strictEqual(target.querySelector('.o_activity_filter_button[data-filter="today"]').innerText.trim(),
        "1 Today",
        "should display one note for today");

    assert.doesNotHaveClass(target.querySelector('.o_note_show'), 'd-none',
        'ActivityMenu add note button should be displayed');
    assert.hasClass(target.querySelector('.o_note'), 'd-none',
        'ActivityMenu add note input should be hidden');

    // creating quick note with date
    await testUtils.dom.click(target.querySelector('.o_note_show'));
    target.querySelector('input.o_note_input').value = "New Note";
    await testUtils.dom.click(target.querySelector(".o_note_save"));
    assert.strictEqual(target.querySelector('.o_notification_counter').innerText, '2',
        "should increment activity notification counter after creating a second note");
    assert.strictEqual(target.querySelector('.o_activity_filter_button[data-filter="today"]').innerText.trim(),
        "2 Today",
        "should display 2 notes for today");
    assert.doesNotHaveClass(target.querySelector('.o_note_show'), 'd-none',
        'ActivityMenu add note button should be displayed');
    assert.hasClass(target.querySelector('.o_note'), 'd-none',
        'ActivityMenu add note input should be hidden');
});
});
