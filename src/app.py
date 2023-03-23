from flask import (Flask, 
                   render_template, 
                   request, 
                   redirect, 
                   make_response)
from flask_socketio import SocketIO
import random
from time import sleep
from collections import defaultdict
from game import Game
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fdhjdfkhv!JJJfdsjkkjnsd'
socketio = SocketIO(app)

### GLOBAL ###

queue = []
experiments = defaultdict(dict)
experiments_queue = []

### FOLDERS ###

STIMULI_FOLDER = os.path.join('static', 'stimuli')
app.config['STIMULI_FOLDER'] = STIMULI_FOLDER
CONTEXT_FOLDER = os.path.join('static', 'context')
app.config['CONTEXT_FOLDER'] = CONTEXT_FOLDER

### ROUTES ###

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_in = request.form['nickname']
        queue.append(user_in)
        if len(queue) % 2 == 0:
            experiment_id = experiments_queue.pop()
            experiments[experiment_id]['sender'] = user_in
            resp = make_response(redirect('/wait'))
            resp.set_cookie('user', user_in)
            resp.set_cookie('experiment_id', str(experiment_id))
            return resp
        elif len(queue) % 2 == 1:
            experiment_id = random.randint(0, 1000000)
            experiments_queue.append(experiment_id)
            experiments[experiment_id]['receiver'] = user_in
            experiments[experiment_id]['sender'] = None
            resp = make_response(redirect('/wait'))
            resp.set_cookie('user', user_in)
            resp.set_cookie('experiment_id', str(experiment_id))
            return resp
        else:
            pass
    return render_template('index.html')

@app.route('/wait')
def wait():
    user = request.cookies.get('user')
    return render_template('wait.html', user=user)

@app.route('/stand_by')
def hi():
    return render_template('stand_by.html')

@app.route('/sender')
def sender():
    return render_template('sender.html')

@app.route('/receiver')
def receiver():
    return render_template('receiver.html')

@app.route('/result')
def result():
    return render_template('result.html')

@app.route('/endgame')
def endgame():
    return render_template('endgame.html')

### SOCKET.IO ###

@socketio.on('joinedWaiting')
def joined_waiting_room():
    global game 

    sleep(5)
    user = request.cookies.get('user')
    experiment_id = int(request.cookies.get('experiment_id'))
    game = Game({'T': ['r'], 'C': ['l'], 'S': ['r', 'l']}, rounds=10)
    if experiments[experiment_id]['receiver'] == user:
        socketio.emit('redirect', {'url': '/stand_by'}, room=request.sid)
    elif experiments[experiment_id]['sender'] == user:
        socketio.emit('redirect', {'url': '/sender'}, room=request.sid)

@socketio.on('joinedSender')
def joined_sender():
    global context
    global stimulus

    stimulus, context = game.generate_sc()
    socketio.emit('stimulus', {'st': os.path.join(app.config['STIMULI_FOLDER'], 
                                                  f'{stimulus}-{context}.png')}, room=request.sid)

@socketio.on('joinedReceiver')
def joined_receiver():
    socketio.emit('contextWord', {'img': os.path.join(app.config['CONTEXT_FOLDER'], f'{context}.png'), 
                                  'word': word}, room=request.sid)

@socketio.on('buttonPressedSender')
def button_pressed(button_id):
    global word 

    button_ids = {1: 'rabu', 2: 'tabudiga'}
    game.log_word(button_ids[button_id])
    word = button_ids[button_id]
    user = request.cookies.get('user')
    experiment_id = int(request.cookies.get('experiment_id'))
    if experiments[experiment_id]['sender'] == user:
        print('b')
        socketio.emit('redirect', {'url': '/stand_by'}, room=request.sid)
    socketio.emit('redirect', {'url': '/receiver'}, include_self=False)

@socketio.on('buttonPressedReceiver')
def button_pressed(button_id):
    global stimulus_out 
    global old_sender
    global old_receiver

    button_ids = {1: 'C', 2: 'S', 3: 'T'}
    experiment_id = int(request.cookies.get('experiment_id'))
    stimulus_out = button_ids[button_id]
    socketio.emit('redirect', {'url': '/result'}, broadcast=True)
    old_sender = experiments[experiment_id]['sender']
    old_receiver = experiments[experiment_id]['receiver']

@socketio.on('joinedResult')
def joined_result():
    try:
        experiment_id = int(request.cookies.get('experiment_id'))
        user = request.cookies.get('user')
        map_result = {True: 'Correct!', False: 'Incorrect!'}
        result = game.check(stimulus_out=stimulus_out, stimulus=stimulus)
        socketio.emit('resultCheck', {'message': map_result[result]}, room=request.sid)
        print(experiments[experiment_id])
        sleep(5)
        if old_sender == user:
            experiments[experiment_id]['receiver'] = old_sender
            socketio.emit('redirect', {'url': '/stand_by'}, room=request.sid)
        elif old_receiver == user:
            experiments[experiment_id]['sender'] = old_receiver
            socketio.emit('redirect', {'url': '/sender'}, room=request.sid)
    except Exception:
        # redirect to final page with score
        socketio.emit('redirect', {'url': '/endgame'}, room=request.sid)
        game.save_logs()
        # need to be carefull here!
        # del game 
        pass

@socketio.on('joinedEndGame')
def joined_endgame():
    # divided by 2 because each user has to do 10 rounds so 2 increments
    # needs fixing
    socketio.emit('score', {'score': game.score/2}, room=request.sid)

if __name__ == '__main__':
    socketio.run(app, debug=False, port=9000)
