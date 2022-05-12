/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'RtcPeerConnection',
    identifyingFields: ['rtcSession'],
    lifecycleHooks: {
        _willDelete() {
            this.peerConnection.close();
        }
    },
    recordMethods: {
        /**
         * @param {String} trackKind
         * @returns {RTCRtpTransceiver} the transceiver used for this trackKind.
         */
        getTransceiver(trackKind) {
            const transceivers = this.peerConnection.getTransceivers();
            return transceivers[this.messaging.rtc.orderedTransceiverNames.indexOf(trackKind)];
        },
        /**
         * Sets the direction of the video transceiver of a given session.
         *
         * @param {boolean} allowReception
         */
        setVideoReceiverActivity(allowReception) {
            const rtc = this.rtcSession.rtcAsConnectedSession;
            if (!rtc) {
                return;
            }
            const transceiver = this.getTransceiver('video');
            if (!transceiver) {
                return;
            }
            if (allowReception) {
                transceiver.direction = rtc.videoTrack ? 'sendrecv' : 'recvonly';
                console.log(`download from ${this.rtcSession.name}: allowed`); // TODO remove
            } else {
                transceiver.direction = rtc.videoTrack ? 'sendonly' : 'inactive';
                console.log(`download from ${this.rtcSession.name}: disallowed`); // TODO remove
            }
        },
    },
    fields: {
        /**
         * Contains the browser.RTCPeerConnection instance of this RTC Session.
         * If unset, this RTC Session is not considered as connected
         */
        peerConnection: attr(),
        rtcSession: one('RtcSession', {
            inverse: 'rtcPeerConnection',
            readonly: true,
            required: true,
        }),
    },
});
