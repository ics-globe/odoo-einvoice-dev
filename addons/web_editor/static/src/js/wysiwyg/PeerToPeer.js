/** @odoo-module */

window.showNotif = true;

export class PeerToPeer {
    constructor(options) {
        this.options = options;
        window.rtc = this;
        this._currentClientId = this.options.currentClientId;

        // clientId -> ClientInfos
        this.clientsInfos = {};
        this._lastRequestId = -1;
        this._pendingRequestResolver = {};
    }

    getConnectedClientIds() {
        return Object.entries(this.clientsInfos)
            .filter(
                ([id, infos]) =>
                    infos.peerConnection.iceConnectionState === 'connected' &&
                    infos.dataChannel.readyState === 'open',
            )
            .map(([id]) => id);
    }

    removeClient(clientId, { shouldNotify = true } = {}) {
        console.log(`%c REMOVE CLIENT ${clientId}`, 'background: chocolate;');
        this.notifySelf('ptp_inactive_client', clientId);
        const clientInfos = this.clientsInfos[clientId];
        if (!clientInfos) return;
        clearTimeout(clientInfos.fallbackTimeout);
        clearTimeout(clientInfos.zombieTimeout);
        clientInfos.dataChannel.close();
        if (clientInfos.peerConnection) {
            clientInfos.peerConnection.close();
        }
        delete this.clientsInfos[clientId];
    }

    closeAllConnections() {
        for (const clientId of Object.keys(this.clientsInfos)) {
            this.notifyAllClients('ptp_disconnect');
            this.removeClient(clientId);
        }
    }

    notifyAllClients(notificationName, notificationPayload, { transport = 'server' } = {}) {
        const transportPayload = {
            fromClientId: this._currentClientId,
            notificationName,
            notificationPayload,
        };
        this._simulateLatency(() => {
            if (transport === 'server') {
                this.options.broadcastAll(transportPayload);
            } else if (transport === 'rtc') {
                for (const cliendId of Object.keys(this.clientsInfos)) {
                    // todo: Handle error if it happens.
                    this._channelNotify(cliendId, transportPayload);
                }
            } else {
                throw new Error(
                    `Transport "${transport}" is not supported. Use "server" or "rtc" transport.`,
                );
            }
        });
    }

    notifyClient(clientId, notificationName, notificationPayload, { transport = 'server' } = {}) {
        if (window.showNotif) {
            if (notificationName === 'ptp_request_result') {
                console.log(
                    `%cREQUEST RESULT SEND: %c${transport}:${
                        notificationPayload.requestId
                    }:${this._currentClientId.slice('-5')}:${clientId.slice('-5')}`,
                    'color: #aaa;font-weight:bold;',
                    'color: #aaa;font-weight:normal',
                );
            } else if (notificationName === 'ptp_request') {
                console.log(
                    `%cREQUEST SEND: %c${transport}:${notificationPayload.requestName}|${
                        notificationPayload.requestId
                    }:${this._currentClientId.slice('-5')}:${clientId.slice('-5')}`,
                    'color: #aaa;font-weight:bold;',
                    'color: #aaa;font-weight:normal',
                );
            } else {
                console.log(
                    `%cNOTIFICATION SEND: %c${transport}:${notificationName}:${this._currentClientId.slice(
                        '-5',
                    )}:${clientId.slice('-5')}`,
                    'color: #aaa;font-weight:bold;',
                    'color: #aaa;font-weight:normal',
                );
            }
        }
        const transportPayload = {
            fromClientId: this._currentClientId,
            toClientId: clientId,
            notificationName,
            notificationPayload,
        };
        this._simulateLatency(() => {
            if (transport === 'server') {
                // Todo: allow to broadcast to only one client rather than all of them
                this.options.broadcastAll(transportPayload);
            } else if (transport === 'rtc') {
                this._channelNotify(clientId, transportPayload);
            } else {
                throw new Error(
                    `Transport "${transport}" is not supported. Use "server" or "rtc" transport.`,
                );
            }
        });
    }

    notifySelf(notificationName, notificationPayload) {
        this.handleNotification({ notificationName, notificationPayload });
    }

    handleNotification(notification) {
        const isInternalNotification =
            typeof notification.fromClientId === 'undefined' &&
            typeof notification.toClientId === 'undefined';
        if (
            isInternalNotification ||
            (notification.fromClientId !== this._currentClientId && !notification.toClientId) ||
            notification.toClientId === this._currentClientId
        ) {
            if (window.showNotif) {
                if (notification.notificationName === 'ptp_request_result') {
                    console.log(
                        `%cREQUEST RESULT RECEIVE: %c${
                            notification.notificationPayload.requestId
                        }:${notification.fromClientId.slice('-5')}:${notification.toClientId.slice(
                            '-5',
                        )}`,
                        'color: #aaa;font-weight:bold;',
                        'color: #aaa;font-weight:normal',
                    );
                } else if (notification.notificationName === 'ptp_request') {
                    console.log(
                        `%cREQUEST RECEIVE: %c${notification.notificationPayload.requestName}|${
                            notification.notificationPayload.requestId
                        }:${notification.fromClientId.slice('-5')}:${notification.toClientId.slice(
                            '-5',
                        )}`,
                        'color: #aaa;font-weight:bold;',
                        'color: #aaa;font-weight:normal',
                    );
                } else {
                    console.log(
                        `%cNOTIFICATION RECEIVE: %c${notification.notificationName}:${notification.fromClientId}:${notification.toClientId}`,
                        'color: #aaa;font-weight:bold;',
                        'color: #aaa;font-weight:normal',
                    );
                }
            }
            const baseMethod = this._notificationMethods[notification.notificationName];
            if (baseMethod) {
                baseMethod.call(this, notification);
            }
            if (this.options.onNotification) {
                this.options.onNotification(notification);
            }
        }
    }

    requestClient(clientId, requestName, requestPayload, { transport = 'server' } = {}) {
        return new Promise((resolve, reject) => {
            const requestId = this._getRequestId();

            const rejectTimeout = setTimeout(() => {
                reject('Request took too long (more than 10 seconds).');
                delete this._pendingRequestResolver[requestId];
            }, 10000);

            this._pendingRequestResolver[requestId] = {
                resolve,
                rejectTimeout,
            };

            this.notifyClient(
                clientId,
                'ptp_request',
                {
                    requestId,
                    requestName,
                    requestPayload,
                },
                transport,
            );
        });
    }

    _createClient(clientId, { makeOffer = true } = {}) {
        console.warn('CREATE CONNECTION with client id:', clientId);
        this.clientsInfos[clientId] = {
            makingOffer: false,
            iceCandidateBuffer: [],
            // clientMutex: new Mutex(),
        };
        const pc = new RTCPeerConnection(this.options.peerConnectionConfig);

        if (makeOffer) {
            pc.onnegotiationneeded = async () => {
                console.log(`%c NEGONATION NEEDED: ${pc.connectionState}`, 'background: deeppink;');
                try {
                    this.clientsInfos[clientId].makingOffer = true;
                    console.log(
                        `%ccreating and sending an offer`,
                        'background: darkmagenta; color: white;',
                    );
                    const offer = await pc.createOffer();
                    // Avoid race condition.
                    if (pc.signalingState !== 'stable') {
                        return;
                    }
                    await pc.setLocalDescription(offer);
                    this.notifyClient(clientId, 'rtc_signal_description', pc.localDescription);
                } catch (err) {
                    console.error(err);
                } finally {
                    this.clientsInfos[clientId].makingOffer = false;
                }
            };
        }
        pc.onicecandidate = async event => {
            if (event.candidate) {
                window.i = window.i || 0;
                window.i++;
                const cid = this._currentClientId.slice(-3) + ' : ' + i;
                console.log(`%csend candidate ${cid}`, 'background: darkturquoise;color:white;');
                this.notifyClient(clientId, 'rtc_signal_icecandidate', {
                    cid: cid,
                    cdata: event.candidate,
                });
                // this.clientsInfos[clientId].clientMutex.exec(async () => {
                //     await this.requestClient(clientId, 'rtc_signal_icecandidate', { cid: cid, cdata: event.candidate });
                // });
                // this.notifyClient(clientId, 'rtc_signal_icecandidate', { cid: cid, cdata: event.candidate });
            }
        };
        pc.oniceconnectionstatechange = async () => {
            console.log('ICE STATE UPDATE: ' + pc.iceConnectionState);

            switch (pc.iceConnectionState) {
                case 'failed':
                case 'closed':
                    this.removeClient(clientId);
                    break;
                case 'disconnected':
                    await this._recoverConnection(clientId, {
                        delay: 1000,
                        reason: 'ice connection disconnected',
                    });
                    break;
            }
        };
        // This event does not work in FF. Let's try with oniceconnectionstatechange if it is sufficient.
        pc.onconnectionstatechange = async () => {
            console.log('CONNECTION STATE UPDATE:' + pc.connectionState);

            switch (pc.connectionState) {
                case 'failed':
                case 'closed':
                    this.removeClient(clientId);
                    break;
                case 'disconnected':
                    await this._recoverConnection(clientId, {
                        delay: 500,
                        reason: 'connection disconnected',
                    });
                    break;
            }
        };
        pc.onicecandidateerror = async error => {
            console.groupCollapsed('=== ERROR: onIceCandidate ===');
            console.log(
                'connectionState: ' + pc.connectionState + ' - iceState: ' + pc.iceConnectionState,
            );
            console.trace(error);
            console.groupEnd();
            this._recoverConnection(clientId, { delay: 15000, reason: 'ice candidate error' });
        };
        const dataChannel = pc.createDataChannel('notifications', { negotiated: true, id: 1 });
        let message = [];
        dataChannel.onmessage = event => {
            if (event.data !== '-') {
                message.push(event.data);
            } else {
                this.handleNotification(JSON.parse(message.join('')));
                message = [];
            }
        };
        dataChannel.onopen = event => {
            this.notifySelf('rtc_data_channel_open', {
                connectionClientId: clientId,
            });
        };
        dataChannel.closing = event => {
            console.log('channel closing');
        };
        dataChannel.closing = error => {
            console.log('channel error');
        };
        dataChannel.closing = close => {
            console.log('channel close');
        };
        dataChannel.closing = bufferedamountlow => {
            console.log('channel bufferedamountlow');
        };
        // todo: how to handle datachannel states: bufferedamountlow, error, closing, close

        this.clientsInfos[clientId].peerConnection = pc;
        this.clientsInfos[clientId].dataChannel = dataChannel;

        return this.clientsInfos[clientId];
    }
    async _addIceCandidate(clientInfos, candidate) {
        const rtcIceCandidate = new RTCIceCandidate(candidate);
        try {
            await clientInfos.peerConnection.addIceCandidate(rtcIceCandidate);
        } catch (error) {
            // Ignored.
            console.groupCollapsed('=== ERROR: ADD ICE CANDIDATE ===');
            console.trace(error);
            console.groupEnd();
        }
    }

    _channelNotify(clientId, transportPayload) {
        const clientInfo = this.clientsInfos[clientId];
        const dataChannel = clientInfo && clientInfo.dataChannel;

        if (!dataChannel || dataChannel.readyState !== 'open') {
            console.warn(
                `Impossible to communicate with client ${clientId}. The connection be killed in 10 seconds if the datachannel state has not changed.`,
            );
            this._killPotentialZombie(clientId);
        } else {
            const str = JSON.stringify(transportPayload);
            const size = str.length;
            const maxStringLength = 5000;
            let from = 0;
            let to = maxStringLength;
            while (from < size) {
                dataChannel.send(str.slice(from, to));
                from = to;
                to = to += maxStringLength;
            }
            dataChannel.send('-');
        }
    }

    _getRequestId() {
        this._lastRequestId++;
        return this._lastRequestId;
    }

    async _onRequest(fromClientId, requestId, requestName, requestPayload) {
        const requestFunction = this.options.onRequest && this.options.onRequest[requestName];
        const result = await requestFunction({
            fromClientId,
            requestId,
            requestName,
            requestPayload,
        });
        this.notifyClient(fromClientId, 'ptp_request_result', { requestId, result });
    }
    /**
     * Attempts a connection recovery by updating the tracks, which will start a new transaction:
     * negotiationneeded -> offer -> answer -> ...
     *
     * @private
     * @param {Object} [param1]
     * @param {number} [param1.delay] in ms
     * @param {string} [param1.reason]
     */
    _recoverConnection(clientId, { delay = 0, reason = '' } = {}) {
        const clientInfos = this.clientsInfos[clientId];
        if (!clientInfos || clientInfos.fallbackTimeout) return;

        clientInfos.fallbackTimeout = setTimeout(async () => {
            clientInfos.fallbackTimeout = undefined;
            const pc = clientInfos.peerConnection;
            if (!pc || pc.iceConnectionState === 'connected') {
                return;
            }
            if (['connected', 'closed'].includes(pc.connectionState)) {
                return;
            }
            // hard reset: recreating a RTCPeerConnection
            console.log(
                `%c RTC RECOVERY: calling back client ${clientId} to salvage the connection ${pc.iceConnectionState}, reason: ${reason}`,
                'background: darkorange; color: white;',
            );
            this.removeClient(clientId);
            await this._createClient(clientId);
        }, delay);
    }
    // todo: do we try to salvage the connection after killing the zombie ?
    // Maybe the salvage should be done when the connection is dropped.
    _killPotentialZombie(clientId) {
        const clientInfos = this.clientsInfos[clientId];
        if (!clientInfos || clientInfos.zombieTimeout) {
            return;
        }

        // If there is no connection after 10 seconds, terminate.
        clientInfos.zombieTimeout = setTimeout(() => {
            if (clientInfos && clientInfos.dataChannel.readyState !== 'open') {
                console.log(`%c KILL ZOMBIE ${clientId}`, 'background: red;');
                this.removeClient(clientId);
            } else {
                console.log(`%c NOT A ZOMBIE ${clientId}`, 'background: green;');
            }
        }, 10000);
    }
    _simulateLatency(cb) {
        setTimeout(cb.bind(this), window.latency || 0);
    }

    _notificationMethods = {
        ptp_request: async notification => {
            const { requestId, requestName, requestPayload } = notification.notificationPayload;
            this._onRequest(notification.fromClientId, requestId, requestName, requestPayload);
        },
        ptp_request_result: notification => {
            const { requestId, result } = notification.notificationPayload;
            // If not in _pendingRequestResolver, it means it has timeout.
            if (this._pendingRequestResolver[requestId]) {
                clearTimeout(this._pendingRequestResolver[requestId].rejectTimeout);
                this._pendingRequestResolver[requestId].resolve(result);
                delete this._pendingRequestResolver[requestId];
            }
        },

        ptp_join: async notification => {
            this._createClient(notification.fromClientId);
        },
        ptp_disconnect: notification => {
            this.removeClient(notification.fromClientId);
        },

        rtc_signal_icecandidate: async notification => {
            const cid = notification.notificationPayload.cid;
            console.log(`%creceive candidate: ${cid}`, 'background: darkgreen; color: white;');
            const clientInfos = this.clientsInfos[notification.fromClientId];
            if (
                !clientInfos ||
                !clientInfos.peerConnection ||
                clientInfos.peerConnection.connectionState === 'closed'
            ) {
                console.groupCollapsed('=== ERROR: Handle Ice Candidate from undefined|closed ===');
                console.trace(clientInfos);
                console.groupEnd();
                return;
            }
            if (!clientInfos.peerConnection.remoteDescription) {
                clientInfos.iceCandidateBuffer.push(notification.notificationPayload.cdata);
            } else {
                this._addIceCandidate(clientInfos, notification.notificationPayload.cdata);
            }
        },
        rtc_signal_description: async notification => {
            const description = notification.notificationPayload;
            console.log(
                `%cdescription received:`,
                'background: blueviolet; color: white;',
                description,
            );

            const clientInfos =
                this.clientsInfos[notification.fromClientId] ||
                this._createClient(notification.fromClientId);
            const pc = clientInfos.peerConnection;

            if (!pc || pc.connectionState === 'closed') {
                console.groupCollapsed('=== ERROR: handle offer ===');
                console.log(
                    'An offer has been received for a non-existent peer connection - client: ' +
                        notification.fromClientId,
                );
                console.trace(pc.connectionState);
                console.groupEnd();
                return;
            }

            // Skip if we already have an offer.
            if (pc.signalingState === 'have-remote-offer') {
                return;
            }

            // If there is a racing conditing with the signaling offer (two
            // being sent at the same time). We need one client that abort by
            // rollbacking to a stable signaling state where the other is
            // continuing the process. The client that is polite is the one that
            // will rollback.
            const isPolite =
                ('' + notification.fromClientId).localeCompare('' + this._currentClientId) === 1;
            console.log(
                `%cisPolite: %c${isPolite}`,
                'background: deepskyblue;',
                `background:${isPolite ? 'green' : 'red'}`,
            );

            const isOfferRacing =
                description.type === 'offer' &&
                (clientInfos.makingOffer || pc.signalingState !== 'stable');
            // If there is a racing conditing with the signaling offer and the
            // client is impolite, we must not process this offer and wait for
            // the answer for the signaling process to continue.
            if (isOfferRacing && !isPolite) {
                console.log(
                    `%creturn because isOfferRacing && !isPolite. pc.signalingState: ${pc.signalingState}`,
                    'background: red;',
                );
                return;
            }
            console.log(`%cisOfferRacing: ${isOfferRacing}`, 'background: red;');

            if (isOfferRacing) {
                console.log(`%c SETREMOTEDESCRIPTION 1`, 'background: navy; color:white;');
                await Promise.all([
                    pc.setLocalDescription({ type: 'rollback' }),
                    pc.setRemoteDescription(description),
                ]);
            } else {
                console.log(`%c SETREMOTEDESCRIPTION 2`, 'background: navy; color:white;');
                await pc.setRemoteDescription(description);
            }
            if (clientInfos.iceCandidateBuffer.length) {
                for (const candidate of clientInfos.iceCandidateBuffer) {
                    await this._addIceCandidate(clientInfos, candidate);
                    clientInfos.iceCandidateBuffer.splice(0);
                }
            }
            if (description.type === 'offer') {
                const answerDescription = await pc.createAnswer();
                await pc.setLocalDescription(answerDescription);
                this.notifyClient(
                    notification.fromClientId,
                    'rtc_signal_description',
                    pc.localDescription,
                );
            }
        },
    };
}