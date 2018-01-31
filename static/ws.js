var ws;

function openSocket(url) {
    ws = new WebSocket(url);
    // ws.binaryType = 'arraybuffer'; // default is 'blob'

    ws.onopen = function() {
        sessionStorage.echoServer = url;
    };

    ws.onclose = function() {
        log('close');
    };

    ws.onmessage = function(e) {
        log(e.data);
    };

    ws.onerror = function() {
        log('error');
    };
}

function closeSocket() {
    log('closing');
    ws.close();
}

function sendText() {
    var message = document.getElementById('message').value;
    // log('sending: ' + message);
    ws.send(message);
    document.getElementById('message').value = '';
}

function finalOutput() {
    ws.send('done');
}

function decodeHexString(text) {
    if (text.search(/[^0-9a-f\s]/i) !== -1) {
        alert('Can\'t decode "' + text + '" as hexadecimal...');
    } else {
        text = text.replace(/\s/g, '');
        if (text.length % 2 === 1) {
            text = '0' + text;
        }
        var data = [];
        for (var i = 0, len = text.length; i < len; i += 2) {
            data.push(parseInt(text.substr(i, 2), 16));
        }
        return data;
    }
}

function encodeHexString(data) {
    var bytes = [];
    for (var i = 0, len = data.length; i < len; i++) {
        var value = data[i];
        bytes[i] = value.toString(16);
        if (value < 16) {
            bytes[i] = '0' + bytes[i];
        }
    }
    return bytes.join(' ');
}

function log(message) {
    var li = document.createElement('li');
    li.innerHTML = message;
    document.getElementById('messages').appendChild(li);
}

$(document).ready(function() {
    openSocket('ws://localhost:8585/serve_data');
});

$(document).keypress(function(e) {
    if (e.which == 13) {
        sendText();
    }
});