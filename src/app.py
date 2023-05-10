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

# to-do
# 1. instead of using game, put the global stuff in experiments[experiment_id]

### FLASK SETUP ###

set = random.randint(0, 9)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fdhjdfkhv!JJJfdsjkkjnsd'
socketio = SocketIO(app)
app.config['STIMULI_FOLDER'] = os.path.join('static', 'sets', f'set-{set}', 'stimuli')
app.config['CONTEXT_FOLDER'] = os.path.join('static', 'context')

### GLOBAL ###

NROUNDS = 25
queue = []
experiments = defaultdict(dict)
experiments_queue = []
usernames = []

### ROUTES ###

@app.route('/')
def description():
    return render_template('description.html')

@app.route('/start', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_in = request.form['nickname']
        if user_in in usernames:
            return render_template('index.html', error='You have already completed the experiment.')
        else:
            usernames.append(user_in)
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
    return render_template('receiver.html', folder = f'set-{set}')

@app.route('/result')
def result():
    return render_template('result.html')

@app.route('/endgame')
def endgame():
    return render_template('endgame.html')

@app.route('/timeout')
def timeout():
    return render_template('timeout.html')

### SOCKET.IO ###

@socketio.on('readyToContinue')
def ready_to_continue():
    socketio.emit('redirect', {'url': '/start'}, room=request.sid)

@socketio.on('joinedWaiting')
def joined_waiting_room():
    '''
    To-do:

    - How to account for randomized stimuli? One way is to have n folders with identical 
    filenames and then randomly select one of the folders.
    '''
    # global game 
    user = request.cookies.get('user')
    experiment_id = int(request.cookies.get('experiment_id'))
    experiments[experiment_id]['game'] = Game({'T': ['r'], 'C': ['l'], 'S': ['r', 'l']}, rounds=NROUNDS)
    while experiments[experiment_id]['sender'] is None:
        # waiting for receiver to join 
        sleep(1)
    else:
        if experiments[experiment_id]['receiver'] == user:
            socketio.emit('redirect', {'url': '/stand_by'}, room=request.sid)
        elif experiments[experiment_id]['sender'] == user:
            socketio.emit('redirect', {'url': '/sender'}, room=request.sid)

@socketio.on('timerDone')
def timer_done():
    socketio.emit('redirect', {'url': '/timeout'}, room=request.sid)
    socketio.emit('redirect', {'url': '/timeout'}, room=request.sid)

@socketio.on('joinedStandBy')
def joined_stand_by():
    # if the user is the receiver, save sid to dict
    user = request.cookies.get('user')
    experiment_id = int(request.cookies.get('experiment_id'))
    game = experiments[experiment_id]['game']
    score = game.score
    round_number = game.current_round
    # emit "updateScoreRound" with score and round number
    socketio.emit('updateScoreRound', {'score': score, 'round': round_number}, room=request.sid)
    if experiments[experiment_id]['receiver'] == user:
        experiments[experiment_id]['receiver_sid'] = request.sid
    elif experiments[experiment_id]['sender'] == user:
        experiments[experiment_id]['sender_sid'] = request.sid
        

@socketio.on('joinedSender')
def joined_sender():
    # global context
    # global stimulus

    experiment_id = int(request.cookies.get('experiment_id'))
    game = experiments[experiment_id]['game']
    stimulus, context = game.generate_sc()

    socketio.emit('stimulus', {'st': os.path.join(app.config['STIMULI_FOLDER'], 
                                                  f'{stimulus}-{context}.png')}, room=request.sid)

@socketio.on('buttonPressedSender')
def button_pressed(button_id):
    '''
    To-do:

    - Solve the issue with the receiver being redirected using the broadcast=True.
    '''
    # global word 

    user = request.cookies.get('user')
    experiment_id = int(request.cookies.get('experiment_id'))
    game = experiments[experiment_id]['game']

    button_ids = {1: 'rabu', 2: 'tabudiga'}
    game.log_word(button_ids[button_id])
    # word = button_ids[button_id]
    experiment_id = int(request.cookies.get('experiment_id'))
    if experiments[experiment_id]['sender'] == user:
        socketio.emit('redirect', {'url': '/stand_by'}, room=request.sid)
    socketio.emit('redirect', {'url': '/receiver'}, room=experiments[experiment_id]['receiver_sid'])

@socketio.on('joinedReceiver')
def joined_receiver():
    experiment_id = int(request.cookies.get('experiment_id')) 
    game = experiments[experiment_id]['game']
    context = game.c_context
    if context == 'r':
        socketio.emit('right', room=request.sid)
    elif context == 'l':
        socketio.emit('left', room=request.sid)
    socketio.emit('contextWord', {'img': os.path.join(app.config['CONTEXT_FOLDER'], f'{context}.png'), 
                                  'word': game.c_word}, room=request.sid)

@socketio.on('buttonPressedReceiver')
def button_pressed(button_id):
    '''
    To-do:

    - Remove the global variables and put them into the game class. 
    '''
    # # global stimulus_out 
    global old_sender
    global old_receiver

    button_ids = {1: 'C', 2: 'S', 3: 'T'}
    experiment_id = int(request.cookies.get('experiment_id'))
    game = experiments[experiment_id]['game']
    game.c_stimulus_out = button_ids[button_id]
    old_sender = experiments[experiment_id]['sender']
    old_receiver = experiments[experiment_id]['receiver']
    socketio.emit('redirect', {'url': '/result'}, room=request.sid) 
    socketio.emit('redirect', {'url': '/result'}, room=experiments[experiment_id]['sender_sid'])

@socketio.on('joinedResult')
def joined_result():
    experiment_id = int(request.cookies.get('experiment_id'))
    game = experiments[experiment_id]['game']
    stimulus_out = game.c_stimulus_out
    user = request.cookies.get('user')
    map_result = {True: 'Correct!', False: 'Incorrect!'}
    result = game.check(stimulus_out=stimulus_out)
    score = game.score
    round_number = game.current_round
    if game.current_round < NROUNDS:
        socketio.emit('resultCheck', {'message': map_result[result], 'score': score, 'round': round_number}, room=request.sid)
        sleep(2)
        if old_sender == user:
            experiments[experiment_id]['receiver'] = old_sender
            socketio.emit('redirect', {'url': '/stand_by'}, room=request.sid)
        elif old_receiver == user:
            experiments[experiment_id]['sender'] = old_receiver
            socketio.emit('redirect', {'url': '/sender'}, room=request.sid)
    else:
        socketio.emit('redirect', {'url': '/endgame'}, room=request.sid)
        receiver = experiments[experiment_id]['receiver']
        sender = experiments[experiment_id]['sender']
        game.save_logs(f'{receiver}-{sender}')
        pass

@socketio.on('joinedEndGame')
def joined_endgame():
    experiment_id = int(request.cookies.get('experiment_id'))
    game = experiments[experiment_id]['game']
    socketio.emit('score', {'score': game.score}, room=request.sid)
    # retreive names for both players
    receiver = experiments[experiment_id]['receiver']
    sender = experiments[experiment_id]['sender']
    # retreive score
    score = game.score
    # retrieve experiment id
    experiment_id = int(request.cookies.get('experiment_id'))
    # save all of this information to logs/participants.csv
    with open('logs/participants.csv', 'a') as f:
        f.write(f'{experiment_id},{receiver},{sender},{score},set-{set}\n')

if __name__ == '__main__':
    socketio.run(app, debug=False, port=9001)