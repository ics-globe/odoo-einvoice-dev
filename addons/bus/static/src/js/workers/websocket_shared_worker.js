/* eslint-env worker */
/* eslint-disable no-restricted-globals */
/* global WebsocketWorker */
importScripts('/bus/static/src/js/workers/websocket_worker.js');



const websocketWorker = new WebsocketWorker(
    `${self.location.protocol === 'https:' ? 'wss' : 'ws'}://${self.location.host}/websocket`
);

onconnect = function (ev) {
    const currentClient = ev.ports[0];
    websocketWorker.registerClient(currentClient);
};
