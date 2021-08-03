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
        console.warn("CREATE CONNECTION with client id:", clientId);
        const peerConnection = new RTCPeerConnection(this.options.peerConnectionConfig);

        peerConnection.onnegotiationneeded = async () => {
            console.log('NEGONATION NEEDED:' + peerConnection.connectionState);
            const offer = await peerConnection.createOffer();
            await peerConnection.setLocalDescription(offer);
            this.notifyClient(clientId, 'rtc_signal_offer', peerConnection.localDescription);
        };
        peerConnection.onicecandidate = async (event) => {
            console.log('ON ICE CANDIDATE with client id', clientId);
            if (!event.candidate) return;
            await this.notifyAllClients('rtc_signal_icecandidate', event.candidate);
        };
        peerConnection.oniceconnectionstatechange = async () => {
            console.log('ICE STATE UPDATE: ' + peerConnection.iceConnectionState);

            switch (peerConnection.iceConnectionState) {
                case "failed":
                case "closed":
                    this._removeClient(clientId);
                    break;
                case "disconnected":
                    await this._recoverConnection(clientId, { delay: 1000, reason: 'ice connection disconnected' });
                    break;
            }
        };
        peerConnection.onconnectionstatechange =  async () => {
            console.log('CONNECTION STATE UPDATE:' + peerConnection.connectionState);

            switch (peerConnection.connectionState) {
                case "failed":
                case "closed":
                    this._removeClient(clientId);
                    break;
                case "disconnected":
                    await this._recoverConnection(clientId, { delay: 500, reason: 'connection disconnected' });
                    break;
            }

            this.handleNotification({
                notificationName: 'rtc_connection_statechange',
                notificationPayload: peerConnection.connectionState,
            });
        };
        peerConnection.onicecandidateerror = async (error) => {
            console.groupCollapsed('=== ERROR: onIceCandidate ===');
            console.log('connectionState: ' + peerConnection.connectionState + ' - iceState: ' + peerConnection.iceConnectionState);
            console.trace(error);
            console.groupEnd();
            this._recoverConnection(token, { delay: 15000, reason: 'ice candidate error' });
        };
        const dataChannel = peerConnection.createDataChannel("notifications", { negotiated: true, id: 1 });
        dataChannel.onmessage = (event) => {
            this.handleNotification(JSON.parse(event.data));
        };

        this.clientsInfos[clientId] = {
            peerConnection,
            dataChannel,
        };
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
    _recoverConnection(clientId, { delay=0, reason='' } = {}) {
        const clientInfos = this.clientsInfos[clientId];
        if (clientInfos.fallbackTimeout) return;

        clientInfos.fallbackTimeout = setTimeout(async () => {
            clientInfos.fallbackTimeout = undefined;
            if (!clientInfos.peerConnection) {
                return;
            }
            if (clientInfos.peerConnection.iceConnectionState === 'connected') {
                return;
            }
            if (['connected', 'closed'].includes(clientInfos.peerConnection.connectionState)) {
                return;
            }
            // hard reset: recreating a RTCPeerConnection
            console.log(`RTC RECOVERY: calling back client ${clientId} to salvage the connection ${clientInfos.peerConnection.iceConnectionState}, reason: ${reason}`);
            await this.notifyClient(clientId, 'rtc_signal_disconnect');
            this._removeClient(clientId);
            await this._createClient(clientId);
            this._killPotentialZombie(clientId);
        }, delay);
    }

    _killPotentialZombie(clientId) {
        const clientInfos = this.clientsInfos[clientId];
        if (!clientInfos || clientInfos.zombieTimeout) return;

        // If there is no connection after 10 seconds, terminate
        clientInfos.zombieTimeout = setTimeout(() => {
            if (clientInfos && clientInfos.peerConnection.connectionState === 'new') {
                console.log('KILL ZOMBIE' , clientId);
                this._removeClient(clientId);
            }
        }, 10000);
    }

    _removeClient(clientId) {
        const clientInfos = this.clientsInfos[clientId];
        clearTimeout(clientInfos.fallbackTimeout);
        clientInfos.dataChannel.close();
        if (clientInfos.peerConnection) {
            clientInfos.peerConnection.close();
        }
        delete this.clientsInfos[clientId];
    }

    notifyAllClients(notificationName, notificationPayload, { transport = 'server' } = {}) {
        console.log(`notifyAllClients ${transport}:${notificationName}:${this._currentClientId}:_`, notificationPayload);
        const transportPayload = {
            fromClientId: this._currentClientId,
            notificationName,
            notificationPayload,
        };
        if (transport === 'server') {
            this.options.broadcastAll(transportPayload);
        } else if (transport === 'rtc') {
            for (const cliendId of Object.keys(this.clientsInfos)) {
                // todo: Handle error if it happens.
                this._channelNotify(cliendId, transportPayload);
            }
        } else {
            throw new Error(`Transport "${transport}" is not supported. Use "server" or "rtc" transport.`);
        }
    }

    notifyClient(clientId, notificationName, notificationPayload, { transport = 'server' } = {}) {
        console.log(`notifyClient ${transport}:${notificationName}:${this._currentClientId}:${clientId}`);
        const transportPayload = {
            fromClientId: this._currentClientId,
            toClientId: clientId,
            notificationName,
            notificationPayload,
        }
        if (transport === 'server') {
            // Todo: allow to broadcast to only one client rather than all of them
            this.options.broadcastAll(transportPayload);
        } else if (transport === 'rtc') {
            this._channelNotify(clientId, transportPayload);
        }
    }

    _channelNotify(clientId, transportPayload) {
        const clientInfo = this.clientsInfos[clientId];
        if (!clientInfo) {
            throw new Error(`Client ${clientId} has no connection.`);
        }
        const dataChannel = clientInfo.dataChannel;
        if (!dataChannel) {
            throw new Error(`Client ${clientId} has no dataChannel.`);
        }
        if (dataChannel.readyState !== 'open') {
            console.warn(`Client ${clientId} dataChannel.readyState is not open, it will be killed in 10 seconds if the stated has not changed.`);
            this._killPotentialZombie(clientId);
        } else {
            dataChannel.send(JSON.stringify(transportPayload));
        }
    }

    handleNotification(notification) {
        console.log(`HANDLE NOTIFICATION: ${notification.notificationName}:${notification.fromClientId}:${notification.toClientId}`);
        const isInternalNotification = typeof notification.fromClientId === 'undefined' && typeof notification.toClientId === 'undefined';
        if (
             isInternalNotification ||
                (notification.fromClientId !== this._currentClientId &&
                !notification.toClientId || notification.toClientId === this._currentClientId)
        ) {
            const baseMethod = this._notificationMethods[notification.notificationName];
            if (baseMethod) {
                return baseMethod.call(this, notification);
            }
            if (this.options.onNotification) {
                return this.options.onNotification(notification);
            }
        }
    }


    _notificationMethods = {
        rtc_join: async (notification) => {
            this._createClient(notification.fromClientId);
        },
        rtc_signal_offer: async (notification) => {
            const clientInfos =
                this.clientsInfos[notification.fromClientId] ||
                this._createClient(notification.fromClientId);
            const { peerConnection } = clientInfos;

            if (!peerConnection || peerConnection.connectionState === 'closed') {
                console.groupCollapsed('=== ERROR: handle offer ===');
                console.log('An offer has been received for a non-existent peer connection - client: ' + notification.fromClientId);
                console.trace(peerConnection.connectionState);
                console.groupEnd();
                return;
            }

            // Skip if we already have an offer.
            if (peerConnection.signalingState === 'have-remote-offer') return;

            await peerConnection.setRemoteDescription(new RTCSessionDescription(notification.notificationPayload));

            const description = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(description);

            this.notifyClient(notification.fromClientId, 'rtc_signal_answer', peerConnection.localDescription);
        },
        rtc_signal_answer: async (notification) => {
            const clientInfos = this.clientsInfos[notification.fromClientId];
            const { peerConnection } = clientInfos;

            if (
                !peerConnection ||
                peerConnection.connectionState === 'closed' ||
                peerConnection.signalingState === 'stable'
            ) {
                console.groupCollapsed('=== ERROR: Handle Answer from undefined|closed|stable === ');
                console.trace(peerConnection);
                console.groupEnd();
                return;
            }

            // Skip if we already have an offer.
            if (peerConnection.signalingState === 'have-remote-offer') return;

            peerConnection.setRemoteDescription(new RTCSessionDescription(notification.notificationPayload));
        },
        rtc_signal_icecandidate: async (notification) => {
            const clientInfos = this.clientsInfos[notification.fromClientId];
            if (!clientInfos || !clientInfos.peerConnection || clientInfos.peerConnection.connectionState === 'closed') {
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
                console.groupCollapsed("=== ERROR: ADD ICE CANDIDATE ===");
                console.trace(error);
                console.groupEnd();
            }
        },
        rtc_signal_disconnect: (notification) => {
            this._removeClient(notification.from_rtc_client_id)
        }
    }
}
