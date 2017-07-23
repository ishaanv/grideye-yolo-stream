# TODO add requriements file

from flask import Flask, render_template
from flask_sockets import Sockets

app = Flask(__name__)
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
sockets = Sockets(app)

QUESTIONS = [
    'What is your name?',
    'Are you male or female?',
    'When were you born? (dd-mm-yyyy)',
    'Are you a smoker?',
]


@sockets.route('/chat')
def qa_socket(ws):
    answers = []
    while not ws.closed:
        ws.send('Hello, I am going to ask you few questions that will help me know you better?')
        for question in QUESTIONS:
            ws.send(question)
            message = ws.receive()
            answers.append(message)
        ws.send('Thank you. Press "Done" for results.')

        # wait for 'done'
        while not ws.closed:
            if ws.receive() == 'done':
                # fix last answer
                answers[-1] = 'smoker' if answers[-1].lower() == 'yes' else 'non-smoker'
                ws.send("{0} was born in {2} and is a {1} {3}.".format(*answers))


@app.route('/')
def hello():
    return render_template('index.html')


if __name__ == "__main__":
    # TODO understand where gevent fits into the whole picture
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('', 9000), app, handler_class=WebSocketHandler)
    server.serve_forever()
