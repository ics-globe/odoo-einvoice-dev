/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, useRef } = owl;


export class RtcVideo extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useUpdate({ func: () => this._update() });
        //this._zoomerRef = useRef('input1');
    }

    async perform(net) {

        var localVideo = $('video.o_RtcVideo')[0];
        var outputCtx = $( '.output-canvas canvas' )[ 0 ];
        while (true) {
          const segmentation = await net.segmentPerson(localVideo);
      
          const backgroundBlurAmount = 26;
          const edgeBlurAmount = 2;
          const flipHorizontal = false;
      
          bodyPix.drawBokehEffect(
            outputCtx, localVideo, segmentation, backgroundBlurAmount,
            edgeBlurAmount, flipHorizontal);
        }
      }
      


    drawToCanvas() {

        let options = {
            multiplier: 0.75,
            stride: 32,
            quantBytes: 4
          }
        bodyPix.load(options)
        .then(net => this.perform(net))
        .catch(err => console.log(err))

        function localFunc() {
            var localVideo = $('video.o_RtcVideo')[0];
            //var inputCtx = $( '.input-canvas canvas' )[ 0 ].getContext( '2d' );
            var outputCtx = $( '.output-canvas canvas' )[ 0 ].getContext( '2d' );
            // draw video to input canvas
            //inputCtx.drawImage( localVideo, 0, 0, localVideo.width, localVideo.height );
    
            // get pixel data from input canvas
            //var pixelData = inputCtx.getImageData( 0, 0, localVideo.width, localVideo.height );

    
            //outputCtx.putImageData( pixelData, 0, 0 );
            //requestAnimationFrame(localFunc);
        }

        //requestAnimationFrame(localFunc);
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {RtcSession|undefined}
     */
    get rtcSession() {
        return this.messaging.models['RtcSession'].get(
            this.props.rtcSessionLocalId
        );
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _update() {
        this._loadVideo();
    }

    /**
     * Since it is not possible to directly put a mediaStreamObject as the src
     * or src-object of the template, the video src is manually inserted into
     * the DOM.
     *
     */
    _loadVideo() {
        if (!this.root.el) {
            return;
        }
        if (!this.rtcSession || !this.rtcSession.videoStream) {
            this.root.el.srcObject = undefined;
        } else {
            this.root.el.srcObject = this.rtcSession.videoStream;
            this.drawToCanvas();
        }
        this.root.el.load();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Plays the video as some browsers may not support or block autoplay.
     *
     * @private
     * @param {Event} ev
     */
    async _onVideoLoadedMetaData(ev) {
        try {
            await ev.target.play();
        } catch (error) {
            if (typeof error === 'object' && error.name === 'NotAllowedError') {
                // Ignored as some browsers may reject play() calls that do not
                // originate from a user input.
                return;
            }
            throw error;
        }
    }
}

Object.assign(RtcVideo, {
    props: { rtcSessionLocalId: String },
    template: 'mail.RtcVideo',
});

registerMessagingComponent(RtcVideo);
