/** @odoo-module */

export class RTC {
    constructor(options) {
        this.options = options;
        window.rtc = this;
        this._currentClientId = this.options.currentClientId;

        // clientId -> ClientInfos
        this.clientsInfos = {};
    }

    getConnectedClients() {
        return Object.entries(this.clientsInfos)
            .filter(([id, infos]) => infos.peerConnection.connectionState === 'connected')
            .map(([id]) => id);
    }

    _createClient(clientId) {
        console.warn('CREATE CONNECTION with client id:', clientId);
        this.clientsInfos[clientId] = {
            makingOffer: false,
        };
        const pc = new RTCPeerConnection(this.options.peerConnectionConfig);

        pc.onnegotiationneeded = async () => {
            console.log(`%c NEGONATION NEEDED: ${pc.connectionState}`, 'background: deeppink;');
            try {
                this.clientsInfos[clientId].makingOffer = true;
                const offer = await pc.createOffer();
                // Avoid race condition.
                if (pc.signalingState !== 'stable') {
                    return;
                }
                console.log('try to setLocalDescription');
                await pc.setLocalDescription(offer);
                console.log('pc.localDescription:', pc.localDescription);
                this.notifyClient(clientId, 'rtc_signal_description', pc.localDescription);
            } catch (err) {
                console.error(err);
            } finally {
                this.clientsInfos[clientId].makingOffer = false;
            }
        };
        pc.onicecandidate = async event => {
            console.log('ON ICE CANDIDATE with client id', clientId);
            if (event.candidate) {
                this.notifyClient(clientId, 'rtc_signal_icecandidate', event.candidate);
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
            console.log('channel open');
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
            // await this.notifyClient(clientId, 'rtc_signal_disconnect');
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

    removeClient(clientId, { shouldNotify = true } = {}) {
        // todo: insure the client properly received the rtc_close if the
        // peerConnection.connectionState is "connected".
        // todo: is it possible to have concurency issue where we will close a
        // connection that has been recovered ?
        // if (shouldNotify) this.notifyClient(clientId, 'rtc_close');
        console.log(`%c REMOVE CLIENT ${clientId}`, 'background: chocolate;');
        this.notifySelf('rtc_remove_client', clientId);
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
            this.removeClient(clientId);
        }
    }

    _simulateLatency(cb) {
        setTimeout(cb.bind(this), window.latency || 0);
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
        console.log(
            `notifyClient ${transport}:${notificationName}:${this._currentClientId}:${clientId}`,
        );
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
            const cutByteSize = 5000;
            let from = 0;
            let to = cutByteSize;
            const blobSize = new Blob([str]).size;
            console.log('sending blobSize:', blobSize);
            while (from < size) {
                dataChannel.send(str.slice(from, to));
                from = to;
                to = to += cutByteSize;
            }
            dataChannel.send('-');
            // console.log(`%c sending payload size: ${new Blob([str]).size / 8}`, 'background: chocolate; color: white');
            // dataChannel.send(new Blob([str]));
        }
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
            console.log(
                `HANDLE NOTIFICATION: ${notification.notificationName}:${notification.fromClientId}:${notification.toClientId}`,
            );
            const baseMethod = this._notificationMethods[notification.notificationName];
            if (baseMethod) {
                baseMethod.call(this, notification);
            }
            if (this.options.onNotification) {
                this.options.onNotification(notification);
            }
        }
    }

    _notificationMethods = {
        rtc_join: async notification => {
            this._createClient(notification.fromClientId);
        },
        rtc_signal_description: async notification => {
            const description = notification.notificationPayload;
            console.log('notification:', notification);

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
                ('' + notification.fromClientId).localeCompare('' + notification.toClientId) === 1;

            const isOfferRacing = description.type === 'offer' && pc.signalingState !== 'stable';
            // If there is a racing conditing with the signaling offer and the
            // client is impolite, we must not process this offer and wait for
            // the answer for the signaling process to continue.
            if (isOfferRacing && !isPolite) {
                return;
            }

            if (isOfferRacing) {
                await pc.setLocalDescription({ type: 'rollback' });
                await pc.setRemoteDescription(description);
                // await Promise.all([
                //     pc.setLocalDescription({type: "rollback"}),
                //     pc.setRemoteDescription(description),
                // ]);
            } else {
                await pc.setRemoteDescription(description);
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
        rtc_signal_icecandidate: async notification => {
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
            const rtcIceCandidate = new RTCIceCandidate(notification.notificationPayload);
            try {
                await clientInfos.peerConnection.addIceCandidate(rtcIceCandidate);
            } catch (error) {
                // Ignored.
                console.groupCollapsed('=== ERROR: ADD ICE CANDIDATE ===');
                console.trace(error);
                console.groupEnd();
            }
        },
        rtc_signal_disconnect: notification => {
            this.removeClient(notification.from_rtc_client_id);
        },
    };
}
