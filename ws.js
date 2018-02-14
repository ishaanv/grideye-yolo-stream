var ws = new WebSocket("ws://" + window.location.hostname + ":8888/");

Plotly.d3.json('https://raw.githubusercontent.com/plotly/datasets/master/custom_heatmap_colorscale.json', function (figure) {
    Plotly.plot('graph', [{
        type: 'heatmap',
        z: [
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0]
        ],
        zauto: false,
        zmin: 23,
        zmax: 27
    }], { height: 700, width: 700 })
})

ws.onopen = function (e){
    ws.send(JSON.stringify({'device': 'web'}))
}

ws.onmessage = function (e) {
    var json_data = JSON.parse(e.data)
    if (json_data.type == 'grideye') {
        // update thermal
        Plotly.update('graph', {
            z: [
                json_data.data
            ]
        }, [0])
    } else {
        // update image
        var baseStr64 = json_data.data;
        imgElem.setAttribute('src', "data:image/jpeg;base64," + baseStr64);
    };
}
