/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';
import { insertAndReplace } from '@mail/model/model_field_command';
import { ThrottleCanceledError } from '@mail/utils/throttle_canceled_error';
import { ThrottleReinvokedError } from '@mail/utils/throttle_reinvoked_error';
import { nextTick } from '@mail/utils/utils';

QUnit.module('mail', {}, function () {
QUnit.module('utils', {}, function () {
QUnit.module('throttle', {}, function () {
QUnit.module('throttle_tests.js', {});

QUnit.test('single call', async function (assert) {
    assert.expect(6);

    const { advanceTime, messaging } = await start({
        hasTimeControl: true,
    });
    let hasInvokedFunc = false;
    const throttledFunc = messaging.models['Throttle'].insert({
        func: () => {
            hasInvokedFunc = true;
            return 'func_result';
        },
        qunitTestOwner1: insertAndReplace(),
    });
    assert.notOk(
        hasInvokedFunc,
        "func should not have been invoked on immediate throttle initialization"
    );

    await advanceTime(0);
    assert.notOk(
        hasInvokedFunc,
        "func should not have been invoked from throttle initialization after 0ms"
    );

    throttledFunc.do().then(res => {
        assert.step('throttle_observed_invoke');
        assert.strictEqual(
            res,
            'func_result',
            "throttle call return should forward result of inner func"
        );
    });
    await nextTick();
    assert.ok(
        hasInvokedFunc,
        "func should have been immediately invoked on first throttle call"
    );
    assert.verifySteps(
        ['throttle_observed_invoke'],
        "throttle should have observed invoked on first throttle call"
    );
});

QUnit.test('2nd (throttled) call', async function (assert) {
    assert.expect(8);

    const { advanceTime, messaging } = await start({
        hasTimeControl: true,
    });

    let funcCalledAmount = 0;
    const throttledFunc = messaging.models['Throttle'].insert({
        func: () => {
            funcCalledAmount++;
            return `func_result_${funcCalledAmount}`;
        },
        qunitTestOwner2: insertAndReplace(),
    });
    throttledFunc.do().then(result => {
        assert.step('throttle_observed_invoke_1');
        assert.strictEqual(
            result,
            'func_result_1',
            "throttle call return should forward result of inner func 1"
        );
    });
    await nextTick();
    assert.verifySteps(
        ['throttle_observed_invoke_1'],
        "inner function of throttle should have been invoked on 1st call (immediate return)"
    );

    throttledFunc.do().then(res => {
        assert.step('throttle_observed_invoke_2');
        assert.strictEqual(
            res,
            'func_result_2',
            "throttle call return should forward result of inner func 2"
        );
    });
    await nextTick();
    assert.verifySteps(
        [],
        "inner function of throttle should not have been immediately invoked after 2nd call immediately after 1st call (throttled with 1s internal clock)"
    );

    await advanceTime(999);
    assert.verifySteps(
        [],
        "inner function of throttle should not have been invoked after 999ms of 2nd call (throttled with 1s internal clock)"
    );

    await advanceTime(1);
    assert.verifySteps(
        ['throttle_observed_invoke_2'],
        "inner function of throttle should not have been invoked after 1s of 2nd call (throttled with 1s internal clock)"
    );
});

QUnit.test('throttled call reinvocation', async function (assert) {
    assert.expect(11);

    const { advanceTime, messaging } = await start({
        hasTimeControl: true,
    });

    let funcCalledAmount = 0;
    const throttledFunc = messaging.models['Throttle'].insert({
        func: () => {
            funcCalledAmount++;
            return `func_result_${funcCalledAmount}`;
        },
        hasSilentCancelationErrors: false,
        qunitTestOwner2: insertAndReplace(),
    });
    throttledFunc.do().then(result => {
        assert.step('throttle_observed_invoke_1');
        assert.strictEqual(
            result,
            'func_result_1',
            "throttle call return should forward result of inner func 1"
        );
    });
    await nextTick();
    assert.verifySteps(
        ['throttle_observed_invoke_1'],
        "inner function of throttle should have been invoked on 1st call (immediate return)"
    );

    throttledFunc.do()
        .then(() => {
            throw new Error("2nd throttle call should not be resolved (should have been canceled by reinvocation)");
        })
        .catch(error => {
            assert.ok(
                error instanceof ThrottleReinvokedError,
                "Should generate a Throttle reinvoked error (from another throttle function call)"
            );
            assert.step('throttle_reinvoked_1');
        });
    await nextTick();
    assert.verifySteps(
        [],
        "inner function of throttle should not have been immediately invoked after 2nd call immediately after 1st call (throttled with 1s internal clock)"
    );

    await advanceTime(999);
    assert.verifySteps(
        [],
        "inner function of throttle should not have been invoked after 999ms of 2nd call (throttled with 1s internal clock)"
    );

    throttledFunc.do()
        .then(result => {
            assert.step('throttle_observed_invoke_2');
            assert.strictEqual(
                result,
                'func_result_2',
                "throttle call return should forward result of inner func 2"
            );
        });
    await nextTick();
    assert.verifySteps(
        ['throttle_reinvoked_1'],
        "2nd throttle call should have been canceled from 3rd throttle call (reinvoked before cooling down phase has ended)"
    );

    await advanceTime(1);
    assert.verifySteps(
        ['throttle_observed_invoke_2'],
        "inner function of throttle should have been invoked after 1s of 1st call (throttled with 1s internal clock, 3rd throttle call re-use timer of 2nd throttle call)"
    );
});

QUnit.test('flush throttled call', async function (assert) {
    assert.expect(9);

    const { advanceTime, messaging } = await start({
        hasTimeControl: true,
    });
    const throttledFunc = messaging.models['Throttle'].insert({
        func: () => {},
        qunitTestOwner2: insertAndReplace(),
    });
    throttledFunc.do().then(() => assert.step('throttle_observed_invoke_1'));
    await nextTick();
    assert.verifySteps(
        ['throttle_observed_invoke_1'],
        "inner function of throttle should have been invoked on 1st call (immediate return)"
    );

    throttledFunc.do().then(() => assert.step('throttle_observed_invoke_2'));
    await nextTick();
    assert.verifySteps(
        [],
        "inner function of throttle should not have been immediately invoked after 2nd call immediately after 1st call (throttled with 1s internal clock)"
    );

    await advanceTime(10);
    assert.verifySteps(
        [],
        "inner function of throttle should not have been invoked after 10ms of 2nd call (throttled with 1s internal clock)"
    );

    throttledFunc.flush();
    await nextTick();
    assert.verifySteps(
        ['throttle_observed_invoke_2'],
        "inner function of throttle should have been invoked from 2nd call after flush"
    );

    throttledFunc.do().then(() => assert.step('throttle_observed_invoke_3'));
    await nextTick();
    await advanceTime(999);
    assert.verifySteps(
        [],
        "inner function of throttle should not have been invoked after 999ms of 3rd call (throttled with 1s internal clock)"
    );

    await advanceTime(1);
    assert.verifySteps(
        ['throttle_observed_invoke_3'],
        "inner function of throttle should not have been invoked after 999ms of 3rd call (throttled with 1s internal clock)"
    );
});

QUnit.test('cancel throttled call', async function (assert) {
    assert.expect(10);

    const { advanceTime, messaging } = await start({
        hasTimeControl: true,
    });
    const throttledFunc = messaging.models['Throttle'].insert({
        func: () => {},
        hasSilentCancelationErrors: false,
        qunitTestOwner2: insertAndReplace(),
    });
    throttledFunc.do().then(() => assert.step('throttle_observed_invoke_1'));
    await nextTick();
    assert.verifySteps(
        ['throttle_observed_invoke_1'],
        "inner function of throttle should have been invoked on 1st call (immediate return)"
    );

    throttledFunc.do()
        .then(() => {
            throw new Error("2nd throttle call should not be resolved (should have been canceled)");
        })
        .catch(error => {
            assert.ok(
                error instanceof ThrottleCanceledError,
                "Should generate a Throttle canceled error (from `.cancel()`)"
            );
            assert.step('throttle_canceled');
        });
    await nextTick();
    assert.verifySteps(
        [],
        "inner function of throttle should not have been immediately invoked after 2nd call immediately after 1st call (throttled with 1s internal clock)"
    );

    await advanceTime(500);
    assert.verifySteps(
        [],
        "inner function of throttle should not have been invoked after 500ms of 2nd call (throttled with 1s internal clock)"
    );

    throttledFunc.cancel();
    await nextTick();
    assert.verifySteps(
        ['throttle_canceled'],
        "2nd throttle function call should have been canceled"
    );

    throttledFunc.do().then(() => assert.step('throttle_observed_invoke_3'));
    await nextTick();
    assert.verifySteps(
        [],
        "3rd throttle function call should not have invoked inner function yet (cancel reuses inner clock of throttle)"
    );

    await advanceTime(500);
    assert.verifySteps(
        ['throttle_observed_invoke_3'],
        "3rd throttle function call should have invoke inner function after 500ms (cancel reuses inner clock of throttle which was at 500ms in, throttle set at 1ms)"
    );
});

QUnit.test('clear throttled call', async function (assert) {
    assert.expect(9);

    const { advanceTime, messaging } = await start({
        hasTimeControl: true,
    });
    const throttledFunc = messaging.models['Throttle'].insert({
        func: () => {},
        hasSilentCancelationErrors: false,
        qunitTestOwner2: insertAndReplace(),
    });
    throttledFunc.do().then(() => assert.step('throttle_observed_invoke_1'));
    await nextTick();
    assert.verifySteps(
        ['throttle_observed_invoke_1'],
        "inner function of throttle should have been invoked on 1st call (immediate return)"
    );

    throttledFunc.do()
        .then(() => {
            throw new Error("2nd throttle call should not be resolved (should have been canceled from clear)");
        })
        .catch(error => {
            assert.ok(
                error instanceof ThrottleCanceledError,
                "Should generate a Throttle canceled error (from `.clear()`)"
            );
            assert.step('throttle_canceled');
        });
    await nextTick();
    assert.verifySteps(
        [],
        "inner function of throttle should not have been immediately invoked after 2nd call immediately after 1st call (throttled with 1s internal clock)"
    );

    await advanceTime(500);
    assert.verifySteps(
        [],
        "inner function of throttle should not have been invoked after 500ms of 2nd call (throttled with 1s internal clock)"
    );

    throttledFunc.clear();
    await nextTick();
    assert.verifySteps(
        ['throttle_canceled'],
        "2nd throttle function call should have been canceled (from `.clear()`)"
    );

    throttledFunc.do().then(() => assert.step('throttle_observed_invoke_3'));
    await nextTick();
    assert.verifySteps(
        ['throttle_observed_invoke_3'],
        "3rd throttle function call should have invoke inner function immediately (`.clear()` flushes throttle)"
    );
});

});
});
});
