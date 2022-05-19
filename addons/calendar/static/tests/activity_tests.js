/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('calendar', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('activity', {}, function () {
QUnit.module('activity_tests.js');

QUnit.test('calendar rendering activity', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const { click, createChatterContainerComponent } = await start();
    await createChatterContainerComponent({
        threadId: resPartnerId1,
        threadModel: 'res.partner',
    });
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonScheduleActivity',
        "should have schedule activity component"
    );
    await click('.o_ChatterTopbar_buttonScheduleActivity');
    assert.containsOnce(
        document.body,
        '.modal-content',
        "should have activity schedule wizard opened"
    );
    await click('.o_field_many2one[name="activity_type_id"] a.o_dropdown_button');
    assert.containsOnce(
        document.body,
        '.modal-content',
        "should have activity schedule wizard opened"
    );
});

});
});
});
