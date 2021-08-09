import {
    createDOMPathGenerator,
    DIRECTIONS,
    leftDeepFirstInlinePath,
    OdooEditor,
} from '../../src/OdooEditor.js';
import { sanitize } from '../../src/utils/sanitize.js';
import {
    insertCharsAt,
    parseMultipleTextualSelection,
    setSelection,
    targetDeepest,
} from '../utils.js';

const getIncomingStep = (previousStepId, id = '328e7db4-6abf-48e5-88de-2ac505323735') => ({
    cursor: { anchorNode: 1, anchorOffset: 2, focusNode: 1, focusOffset: 2 },
    mutations: [
        {
            type: 'add',
            append: 1,
            id: '199bee91-e88e-4681-a2f7-54ec8fe6fe3c',
            node: {
                nodeType: 1,
                oid: '199bee91-e88e-4681-a2f7-54ec8fe6fe3c',
                tagName: 'B',
                children: [
                    {
                        nodeType: 3,
                        oid: '76498319-5fea-4fda-abf9-9cbd10a279f8',
                        textValue: 'foo',
                    },
                ],
                attributes: {},
            },
        },
    ],
    id,
    userId: '268d771b-4467-4963-98e3-707c7d05501c',
    previousStepId,
});

const testCommandSerialization = (content, commandCb) => {
    const editable = document.createElement('div');
    editable.innerHTML = content;
    document.body.appendChild(editable);
    const selection = parseTextualSelection(editable);

    const receivingNode = document.createElement('div');
    document.body.appendChild(receivingNode);

    const receivingEditor = new OdooEditor(receivingNode, {
        toSanitize: false,
        collaborative: {
            send: () => {},
            requestSynchronization: () => {},
        },
    });
    if (selection) {
        setSelection(selection);
    } else {
        document.getSelection().removeAllRanges();
    }
    const editor = new OdooEditor(editable, {
        toSanitize: false,
        collaborative: {
            send: s => {
                receivingEditor.onExternalHistoryStep(s);
            },
        },
    });
    editor.keyboardType = 'PHYSICAL_KEYBOARD';
    receivingEditor.historyResetAndSync(editor.historyGetSnapshot());
    commandCb(editor);
    window.chai.expect(editable.innerHTML).to.equal(receivingNode.innerHTML);
};

const overridenDomClass = [
    'HTMLBRElement',
    'HTMLHeadingElement',
    'HTMLParagraphElement',
    'HTMLPreElement',
    'HTMLQuoteElement',
    'HTMLTableCellElement',
    'Text',
];

const testFunction = spec => {
    const clientInfos = [];
    // window.clientInfos = clientInfos;
    const clientIds = Object.keys(spec.concurentActions);
    for (const clientId of clientIds) {
        const testInfo = {
            clientId,
            historySteps: [],
        };
        testInfo.iframe = document.createElement('iframe');
        if (navigator.userAgent.toLowerCase().indexOf('firefox') > -1) {
            // Firefox reset the page without this hack.
            // With this hack, chrome does not render content.
            testInfo.iframe.setAttribute('src', ' javascript:void(0);');
        }
        document.body.appendChild(testInfo.iframe);

        testInfo.editable = document.createElement('div');
        testInfo.editable.setAttribute('contenteditable', 'true');
        testInfo.editable.innerHTML = spec.contentBefore;

        const iframeWindow = testInfo.iframe.contentWindow;

        for (const overridenClass of overridenDomClass) {
            const windowClassPrototype = window[overridenClass].prototype;
            const iframeWindowClassPrototype = iframeWindow[overridenClass].prototype;
            const iframePrototypeMethodNames = Object.keys(iframeWindowClassPrototype);

            for (const methodName of Object.keys(windowClassPrototype)) {
                if (!iframePrototypeMethodNames.includes(methodName)) {
                    iframeWindowClassPrototype[methodName] = windowClassPrototype[methodName];
                }
            }
        }

        // we have to sanitize after having put the cursor
        // sanitize(editor.editable);
        clientInfos.push(testInfo);
    }

    let shouldListenSteps = false;

    // Init the editors
    for (const clientInfo of clientInfos) {
        const selections = parseMultipleTextualSelection(clientInfo.editable);
        const iframeWindow = clientInfo.iframe.contentWindow;
        const iframeDocument = iframeWindow.document;
        iframeDocument.body.appendChild(clientInfo.editable);

        // Insure all the client will have the same starting id.
        let nextId = 1;
        OdooEditor.prototype._makeNodeId = () => 'fake_id_' + nextId++;

        clientInfo.editor = new OdooEditor(clientInfo.editable, {
            toSanitize: false,
            document: iframeDocument,
            collaborationClientId: clientInfo.clientId,
            onHistoryStep: step => {
                if (shouldListenSteps) {
                    clientInfo.historySteps.push(step);
                }
            },
        });
        clientInfo.editor.keyboardType = 'PHYSICAL_KEYBOARD';
        const selection = selections[clientInfo.clientId];
        if (selection) {
            setSelection(selection, iframeDocument);
        } else {
            iframeDocument.getSelection().removeAllRanges();
        }
        // Flush the history so that steps generated by the parsing of the
        // selection and the editor loading are not recorded.
        clientInfo.editor.observerFlush();
    }

    shouldListenSteps = true;

    // From now, any any step from a client must have a different ID.
    let concurentNextId = 1;
    OdooEditor.prototype._makeNodeId = () => 'fake_concurent_id_' + concurentNextId++;

    for (const clientInfo of clientInfos) {
        console.log('clientInfo:', clientInfo);
        spec.concurentActions[clientInfo.clientId](clientInfo.editor);
    }

    for (const clientInfoA of clientInfos) {
        for (const clientInfoB of clientInfos) {
            if (clientInfoA === clientInfoB) {
                continue;
            }
            for (const step of clientInfoA.historySteps) {
                clientInfoB.editor.onExternalHistoryStep(step);
            }
        }
    }

    shouldListenSteps = false;

    // Render textual selection.

    const cursorNodes = {};
    for (const clientInfo of clientInfos) {
        const iframeDocument = clientInfo.iframe.contentWindow.document;
        const clientSelection = iframeDocument.getSelection();

        const [anchorNode, anchorOffset] = targetDeepest(
            clientSelection.anchorNode,
            clientSelection.anchorOffset,
        );
        const [focusNode, focusOffset] = targetDeepest(
            clientSelection.focusNode,
            clientSelection.focusOffset,
        );

        const clientId = clientInfo.clientId;
        cursorNodes[focusNode.oid] = cursorNodes[focusNode.oid] || [];
        cursorNodes[focusNode.oid].push({ type: 'focus', clientId, offset: focusOffset });
        cursorNodes[anchorNode.oid] = cursorNodes[anchorNode.oid] || [];
        cursorNodes[anchorNode.oid].push({ type: 'anchor', clientId, offset: anchorOffset });
    }

    for (const nodeOid of Object.keys(cursorNodes)) {
        cursorNodes[nodeOid] = cursorNodes[nodeOid].sort((a, b) => {
            return b.offset - a.offset || b.clientId.localeCompare(a.clientId);
        });
    }

    for (const clientInfo of clientInfos) {
        clientInfo.editor.observerUnactive();
        for (const [nodeOid, cursorsData] of Object.entries(cursorNodes)) {
            const node = clientInfo.editor.idFind(nodeOid);
            for (const cursorData of cursorsData) {
                const cursorString =
                    cursorData.type === 'anchor'
                        ? `[${cursorData.clientId}}`
                        : `{${cursorData.clientId}]`;
                insertCharsAt(cursorString, node, cursorData.offset);
            }
        }
    }

    for (const clientInfo of clientInfos) {
        const value = clientInfo.editable.innerHTML;
        window.chai
            .expect(value)
            .to.be.equal(spec.contentAfter, `error with client ${clientInfo.clientId}`);
    }
    for (const clientInfo of clientInfos) {
        clientInfo.editor.destroy();
        clientInfo.iframe.remove();
    }
};

describe('Collaboration', () => {
    describe('Receive step', () => {
        it('should apply a step when receving a step that is not in the history yet', () => {
            const testNode = document.createElement('div');
            testNode.setAttribute('contenteditable', 'true');
            document.body.appendChild(testNode);
            document.getSelection().setPosition(testNode);
            const synchRequestSpy = window.sinon.fake();
            const sendSpy = window.sinon.fake();
            const editor = new OdooEditor(testNode, {
                toSanitize: false,
                collaborative: {
                    send: sendSpy,
                    requestSynchronization: synchRequestSpy,
                },
            });
            editor.keyboardType = 'PHYSICAL_KEYBOARD';
            const observerUnactiveSpy = window.sinon.spy(editor, 'observerUnactive');
            const historyApplySpy = window.sinon.spy(editor, 'historyApply');
            const historyRevertSpy = window.sinon.spy(editor, 'historyRevert');
            const observerActiveSpy = window.sinon.spy(editor, 'observerActive');

            const incomingStep = getIncomingStep(editor._historySteps[0].id);
            const historyStepsBeforeReceive = [...editor._historySteps];
            editor.onExternalHistoryStep(incomingStep);

            window.chai.expect(synchRequestSpy.callCount).to.equal(0);
            window.chai.expect(sendSpy.callCount).to.equal(0);
            window.chai.expect(observerUnactiveSpy.callCount).to.equal(1);
            window.chai
                .expect(historyApplySpy.getCall(0).firstArg)
                .to.deep.equal(incomingStep.mutations);
            window.chai.expect(historyRevertSpy.callCount).to.equal(0);
            window.chai.expect(observerActiveSpy.callCount).to.equal(1);
            window.chai
                .expect(editor._historySteps)
                .to.deep.equal([...historyStepsBeforeReceive, incomingStep]);
        });
        it('should reorder steps on incoming conflict (incoming before local)', () => {
            const testNode = document.createElement('div');
            document.body.appendChild(testNode);
            document.getSelection().setPosition(testNode);
            const synchRequestSpy = window.sinon.fake();
            const sendSpy = window.sinon.fake();
            const editor = new OdooEditor(testNode, {
                toSanitize: false,
                collaborative: {
                    send: sendSpy,
                    requestSynchronization: synchRequestSpy,
                },
            });
            editor.keyboardType = 'PHYSICAL_KEYBOARD';
            editor.execCommand('insertHTML', '<b>foo</b>');
            editor.execCommand('insertHTML', '<b>bar</b>');
            editor.execCommand('insertHTML', '<b>baz</b>');
            sendSpy.resetHistory();
            const observerUnactiveSpy = window.sinon.spy(editor, 'observerUnactive');
            const historyApplySpy = window.sinon.spy(editor, 'historyApply');
            const historyRevertSpy = window.sinon.spy(editor, 'historyRevert');
            const observerActiveSpy = window.sinon.spy(editor, 'observerActive');

            const incomingStep = getIncomingStep(editor._historySteps[0].id, 'a');
            const historyStepsBeforeReceive = [...editor._historySteps];
            // Take everything but the "init" step.
            const existingSteps = editor._historySteps.slice(1);
            existingSteps[0].id = 'b';
            const incomingSecondStep = { ...incomingStep };
            editor.onExternalHistoryStep(incomingSecondStep);

            window.chai.expect(synchRequestSpy.callCount).to.equal(0);
            window.chai.expect(observerUnactiveSpy.callCount).to.equal(1);
            window.chai
                .expect(historyApplySpy.getCall(0).firstArg)
                .to.deep.equal(incomingStep.mutations);
            existingSteps.forEach((step, i) => {
                // getCall i + 1 because of the new step that is applied first
                window.chai
                    .expect(historyApplySpy.getCall(i + 1).firstArg, 'should have reapplied step')
                    .to.deep.equal(step.mutations);
                window.chai
                    .expect(
                        historyRevertSpy.getCall(2 - i).firstArg,
                        'should have reverted steps in the inverse apply order',
                    )
                    .to.be.equal(step);
            });
            window.chai.expect(observerActiveSpy.callCount).to.equal(1);
            window.chai
                .expect(editor._historySteps.map(({ id }) => id))
                .to.deep.equal([
                    historyStepsBeforeReceive.shift().id,
                    incomingSecondStep.id,
                    ...existingSteps.map(({ id }) => id),
                ]);
        });
        it('should reorder steps on incoming conflict (local before incoming)', () => {
            const testNode = document.createElement('div');
            document.body.appendChild(testNode);
            document.getSelection().setPosition(testNode);
            const synchRequestSpy = window.sinon.fake();
            const sendSpy = window.sinon.fake();
            const editor = new OdooEditor(testNode, {
                toSanitize: false,
                collaborative: {
                    send: sendSpy,
                    requestSynchronization: synchRequestSpy,
                },
            });
            editor.keyboardType = 'PHYSICAL_KEYBOARD';
            editor.execCommand('insertHTML', '<b>foo</b>');
            sendSpy.resetHistory();
            const observerUnactiveSpy = window.sinon.spy(editor, 'observerUnactive');
            const historyApplySpy = window.sinon.spy(editor, 'historyApply');
            const historyRevertSpy = window.sinon.spy(editor, 'historyRevert');
            const observerActiveSpy = window.sinon.spy(editor, 'observerActive');

            const incomingStep = getIncomingStep(editor._historySteps[0].id, 'b');
            const historyStepsBeforeReceive = [...editor._historySteps];
            // Take everything but the "init" step.
            const existingSteps = editor._historySteps.slice(1);
            existingSteps[0].id = 'a';
            editor.onExternalHistoryStep(incomingStep);

            window.chai.expect(synchRequestSpy.callCount).to.equal(0);
            window.chai.expect(observerUnactiveSpy.callCount).to.equal(1);
            window.chai
                .expect(historyApplySpy.getCall(0).firstArg)
                .to.deep.equal(existingSteps[0].mutations);
            existingSteps.forEach((step, i) => {
                // getCall i + 1 because of the new step that is applied first
                window.chai
                    .expect(historyApplySpy.getCall(i).firstArg, 'should have reapplied step')
                    .to.deep.equal(step.mutations);
            });
            window.chai.expect(historyRevertSpy.getCall(0).firstArg).to.be.equal(existingSteps[0]);
            window.chai.expect(observerActiveSpy.callCount).to.equal(1);
            window.chai
                .expect(editor._historySteps.map(({ id }) => id))
                .to.deep.equal([
                    historyStepsBeforeReceive.shift().id,
                    ...existingSteps.map(({ id }) => id),
                    incomingStep.id,
                ]);
        });
        it('should request a synchronization if it receives a step it can not apply', () => {
            const testNode = document.createElement('div');
            document.body.appendChild(testNode);
            document.getSelection().setPosition(testNode);
            const synchRequestSpy = window.sinon.fake();
            const sendSpy = window.sinon.fake();
            const editor = new OdooEditor(testNode, {
                toSanitize: false,
                collaborative: {
                    send: sendSpy,
                    requestSynchronization: synchRequestSpy,
                },
            });
            editor.keyboardType = 'PHYSICAL_KEYBOARD';
            const observerUnactiveSpy = window.sinon.spy(editor, 'observerUnactive');
            const historyApplySpy = window.sinon.spy(editor, 'historyApply');
            const historyRevertSpy = window.sinon.spy(editor, 'historyRevert');
            const observerActiveSpy = window.sinon.spy(editor, 'observerActive');

            // Impossible previousStepId. Real life scenario would be the uuid
            // of a step generated by another client that somehow was not
            // transmitted
            const incomingStep = getIncomingStep('42');
            const historyStepsBeforeReceive = [...editor._historySteps];
            const incoming6thStep = { ...incomingStep, index: 5 };
            editor.onExternalHistoryStep(incoming6thStep);

            window.chai.expect(synchRequestSpy.callCount).to.equal(1);
            window.chai.expect(sendSpy.callCount).to.equal(0);
            window.chai.expect(observerUnactiveSpy.callCount).to.equal(1);
            window.chai.expect(historyApplySpy.callCount).to.equal(0);
            window.chai.expect(historyRevertSpy.callCount).to.equal(0);
            window.chai.expect(observerActiveSpy.callCount).to.equal(1);
            window.chai.expect(editor._historySteps).to.deep.equal(historyStepsBeforeReceive);
        });
    });
    describe('snapshot', () => {
        it('should make a snaphshot that represents the entire document', () => {
            const testNode = document.createElement('div');
            document.body.appendChild(testNode);
            document.getSelection().setPosition(testNode);
            const editor = new OdooEditor(testNode, {
                toSanitize: false,
                collaborative: {
                    send: () => {},
                    requestSynchronization: () => {},
                },
            });
            editor.keyboardType = 'PHYSICAL_KEYBOARD';
            editor.execCommand('insertHTML', '<b>foo</b>');
            editor.execCommand('insertHTML', '<b>bar</b>');
            editor.execCommand('insertHTML', '<b>baz</b>');

            const snap = editor.historyGetSnapshot();
            const virtualNode = document.createElement('div');

            const secondEditor = new OdooEditor(virtualNode, {
                toSanitize: false,
                collaborative: {
                    send: () => {},
                    requestSynchronization: () => {},
                },
            });
            secondEditor.historyResetAndSync(snap);
            var origIt = document.createNodeIterator(testNode);
            var destIt = document.createNodeIterator(virtualNode);
            var res;
            do {
                res = [origIt.nextNode(), destIt.nextNode()];
                window.chai.expect(res[0] && res[0].oid).to.eql(res[1] && res[1].oid);
            } while (res[0] && res[1]);
            window.chai.expect(testNode.innerHTML).to.equal(virtualNode.innerHTML);
        });
    });
    describe('serialization', () => {
        it('should serialize insertText correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('insertText', 'abc');
            });
        });

        it('should serialize insertFontAwesome correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('insertFontAwesome', 'fa fa-pastafarianism');
            });
        });

        it('should serialize undo correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('insertText', 'abc');
                editor.execCommand('undo');
            });
        });

        it('should serialize redo correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('insertText', 'abc');
                editor.execCommand('undo');
                editor.execCommand('redo');
            });
        });

        it('should serialize setTag correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('setTag', 'p');
            });
        });

        it('should serialize bold correctly', () => {
            testCommandSerialization('<p>[Ah.]</p>', editor => {
                editor.execCommand('bold');
            });
        });

        it('should serialize italic correctly', () => {
            testCommandSerialization('<h3>[Ah.]</h3>', editor => {
                editor.execCommand('italic');
            });
        });

        it('should serialize underline correctly', () => {
            testCommandSerialization('<h3>[Ah.]</h3>', editor => {
                editor.execCommand('underline');
            });
        });

        it('should serialize strikeThrough correctly', () => {
            testCommandSerialization('<h3>[Ah.]</h3>', editor => {
                editor.execCommand('strikeThrough');
            });
        });

        it('should serialize removeFormat correctly', () => {
            testCommandSerialization(
                '<p><span style="font-weight: bold;">[Ah.]</span></p>',
                editor => {
                    editor.execCommand('removeFormat');
                },
            );
        });

        it('should serialize justifyLeft correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('justifyLeft');
            });
        });

        it('should serialize justifyRight correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('justifyRight');
            });
        });

        it('should serialize justifyCenter correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('justifyCenter');
            });
        });

        it('should serialize justifyFull correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('justifyFull');
            });
        });

        it('should serialize setFontSize correctly', () => {
            testCommandSerialization('<h3>[Ah.]</h3>', editor => {
                editor.execCommand('setFontSize', '3em');
            });
        });

        it('should serialize createLink correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('createLink', 'https://example.com', 'example');
            });
        });

        it('should serialize unlink correctly', () => {
            testCommandSerialization(
                '<h3><a href="https://example.com">example[]</a></h3>',
                editor => {
                    editor.execCommand('unlink');
                },
            );
        });

        it('should serialize indentList correctly', () => {
            testCommandSerialization('<ul><li>Ah.[]</li></ul>', editor => {
                editor.execCommand('indentList');
            });
        });

        it('should serialize toggleList correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('toggleList');
            });
        });

        it('should serialize applyColor correctly', () => {
            testCommandSerialization('<h3>[Ah.]</h3>', editor => {
                editor.execCommand('applyColor', '#F00', 'color');
            });
        });

        it('should serialize insertTable correctly', () => {
            testCommandSerialization('<p>Ah.[]</p>', editor => {
                editor.execCommand('insertTable', { rowNumber: 2, colNumber: 2 });
            });
        });

        it('should serialize addColumnLeft correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('addColumnLeft');
                },
            );
        });

        it('should serialize addColumnRight correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('addColumnRight');
                },
            );
        });

        it('should serialize addRowAbove correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('addRowAbove');
                },
            );
        });

        it('should serialize addRowBelow correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('addRowBelow');
                },
            );
        });

        it('should serialize removeColumn correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('removeColumn');
                },
            );
        });

        it('should serialize removeRow correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('removeRow');
                },
            );
        });

        it('should serialize deleteTable correctly', () => {
            testCommandSerialization(
                `<table class="table table-bordered">
                    <tbody>
                        <tr><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td>[]<br></td></tr>
                    </tbody>
                </table>`,
                editor => {
                    editor.execCommand('deleteTable');
                },
            );
        });

        it('should serialize insertHorizontalRule correctly', () => {
            testCommandSerialization('<p>Ah.[]</p>', editor => {
                editor.execCommand('insertHorizontalRule');
            });
        });

        it('should serialize oEnter correctly', () => {
            testCommandSerialization('<h3>Ah.[]</h3>', editor => {
                editor.execCommand('oEnter');
            });
        });
        it('should serialize oShiftEnter correctly', () => {
            testCommandSerialization('<p>[]<br></p>', editor => {
                editor.execCommand('oShiftEnter');
            });
        });
        it('should serialize insertHtml correctly', () => {
            testCommandSerialization('<p>[test]<br></p>', editor => {
                editor.execCommand('insertHTML', '<b>lol</b>');
            });
        });
    });
    describe.only('Conflict resolution', () => {
        it('should 2 client insertText in 2 different paragraph', () => {
            testFunction({
                contentBefore: '<p>ab[c1}{c1]</p><p>cd[c2}{c2]</p>',
                concurentActions: {
                    c1: editor => {
                        editor.execCommand('insertText', 'e');
                    },
                    c2: editor => {
                        editor.execCommand('insertText', 'f');
                    },
                },
                contentAfter: '<p>abe[c1}{c1]</p><p>cdf[c2}{c2]</p>',
            });
        });
        it('should 2 client insertText twice in 2 different paragraph', () => {
            testFunction({
                contentBefore: '<p>ab[c1}{c1]</p><p>cd[c2}{c2]</p>',
                concurentActions: {
                    c1: editor => {
                        editor.execCommand('insertText', 'e');
                        editor.execCommand('insertText', 'f');
                    },
                    c2: editor => {
                        editor.execCommand('insertText', 'g');
                        editor.execCommand('insertText', 'h');
                    },
                },
                contentAfter: '<p>abef[c1}{c1]</p><p>cdgh[c2}{c2]</p>',
            });
        });
        it('should properly change the selection of other clients', () => {
            testFunction({
                contentBefore: 'ab[c1}{c1][c2}{c2]c',
                concurentActions: {
                    c1: editor => {
                        console.log('inserttext');
                        editor.execCommand('insertText', 'd');
                    },
                    c2: editor => {
                        console.log('oDeleteBackward');
                    },
                },
                contentAfter: 'abd[c1}{c1][c2}{c2]c',
            });
        });
        it('should insertText with client 1 and deleteBackward with client 2', () => {
            testFunction({
                contentBefore: 'ab[c1}{c1][c2}{c2]c',
                concurentActions: {
                    c1: editor => {
                        editor.execCommand('insertText', 'd');
                    },
                    c2: editor => {
                        editor.execCommand('oDeleteBackward');
                    },
                },
                contentAfter: 'a[c2}{c2]cd[c1}{c1]c',
            });
        });
        it('should insertText twice with client 1 and deleteBackward twice with client 2', () => {
            testFunction({
                contentBefore: 'ab[c1}{c1][c2}{c2]c',
                concurentActions: {
                    c1: editor => {
                        editor.execCommand('insertText', 'd');
                        editor.execCommand('insertText', 'e');
                    },
                    c2: editor => {
                        editor.execCommand('oDeleteBackward');
                        editor.execCommand('oDeleteBackward');
                    },
                },
                contentAfter: 'ab[c1}{c1][c2}{c2]c',
            });
        });
    });
});
