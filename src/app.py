from flask import (Flask, 
                   render_template, 
                   request, 
                   redirect, 
                   make_response,
                   session)
from flask_socketio import SocketIO
import random
from time import sleep
from collections import defaultdict
from game import Game
import os

### FLASK SETUP ###

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fdhjdfkhv!JJJfdsjkkjnsd'
socketio = SocketIO(app)
app.config['CONTEXT_FOLDER'] = os.path.join('static', 'context')

### GLOBAL ###

NROUNDS = 30
COST_SHORT = 1
COST_LONG = 3

LINK_BONUS = "https://app.prolific.co/submissions/complete?cc=CVUISTHW"
LINK_NO_BONUS = "https://app.prolific.co/submissions/complete?cc=CLL9A10A"

experiments = defaultdict(dict)
experiments_queue = []
usernames = []

### ROUTES ###

# @app.route('/')
# def description1():
#     return render_template('description1.html')

# @app.route('/description2')
# def description2():
#     response = make_response(render_template('description2.html'))
#     return response

@app.route('/')
def description3():
    response = make_response(render_template('description3.html', 
                                             cost_long=COST_LONG, 
                                             cost_short=COST_SHORT, 
                                             nrounds=NROUNDS))
    return response

@app.route('/start', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        s = random.randint(1, 9)
        user_in = request.form['nickname']
        if user_in in usernames:
            return render_template('index.html', error='You have already completed the experiment.')
        else:
            usernames.append(user_in)
            if len(experiments_queue) > 0:
                experiment_id = experiments_queue.pop()
                experiments[experiment_id]['sender'] = user_in
                experiments[experiment_id]['set'] = s
                session['user'] = user_in
                session['experiment_id'] = experiment_id
                return make_response(redirect('/wait'))
            elif len(experiments_queue) == 0:
                experiment_id = random.randint(0, 1000000)
                experiments_queue.append(experiment_id)
                experiments[experiment_id]['receiver'] = user_in
                experiments[experiment_id]['sender'] = None
                session['user'] = user_in
                session['experiment_id'] = experiment_id
                return make_response(redirect('/wait'))
    return render_template('index.html')

@app.route('/wait')
def wait():
    user = request.cookies.get('user')
    return render_template('wait.html', 
                           user=user)

@app.route('/stand_by')
def hi():
    return render_template('stand_by.html',
                           nrounds=NROUNDS)

@app.route('/sender')
def sender():
    experiment_id = session['experiment_id']
    set = experiments[experiment_id]['set']
    return render_template('sender.html', 
                           cost_long=COST_LONG*1000, 
                           cost_short=COST_SHORT*1000, 
                           folder = f'set-{set}')

@app.route('/receiver')
def receiver():
    experiment_id = session['experiment_id']
    set = experiments[experiment_id]['set']
    return render_template('receiver.html', 
                           folder = f'set-{set}')

@app.route('/result')
def result():
    return render_template('result.html', 
                           nrounds=NROUNDS)

@app.route('/endgame')
def endgame():
    return render_template('endgame.html')

@app.route('/personal', methods=['GET', 'POST'])
def personal():
    if request.method == 'POST':
        user = session['user']
        age = request.form['age']
        gender = request.form['gender']
        tabugida = request.form['tabugida']
        rabu = request.form['rabu']

        with open('logs/personal.csv', 'a') as f:
            f.write(f'{user},{age},{gender},{tabugida},{rabu}\n')

        return redirect('/endgame')
    return render_template('personal.html')

@app.route('/timeout')
def timeout():
    user = session['user']
    return render_template('timeout.html', user=user)

@app.route('/leftgame')
def leftgame():
    return render_template('leftgame.html')

### SOCKET.IO ###

@socketio.on('readyToContinue')
def ready_to_continue():
    socketio.emit('redirect', {'url': '/start'}, room=request.sid)

@socketio.on('joinedWaiting')
def joined_waiting_room():
    user = session['user']
    experiment_id = session['experiment_id']
    print(experiment_id)
    experiments[experiment_id]['game'] = Game({'T': ['r'], 'C': ['l'], 'S': ['r', 'l']}, 
                                              rounds=NROUNDS)
    while experiments[experiment_id]['sender'] is None:
        sleep(1)
    else:
        if experiments[experiment_id]['receiver'] == user:
            socketio.emit('redirect', {'url': '/stand_by'}, room=request.sid)
        elif experiments[experiment_id]['sender'] == user:
            socketio.emit('redirect', {'url': '/sender'}, room=request.sid)

@socketio.on('timerDone')
def timer_done():
    socketio.emit('redirect', {'url': '/timeout'}, room=request.sid)

@socketio.on('timerDone2')
def timer_done():
    '''
    To-do: redirect the user that has left
    '''
    # user = session['user']
    # experiment_id = session['experiment_id']

    # # get sid of other player
    # if experiments[experiment_id]['receiver'] == user:
    #     other_sid = experiments[experiment_id]['sender_sid']
    # elif experiments[experiment_id]['sender'] == user:
    #     other_sid = experiments[experiment_id]['receiver_sid']

    # socketio.emit('redirect', {'url': '/timeout'}, room=other_sid)
    socketio.emit('redirect', {'url': '/timeout'}, room=request.sid)

@socketio.on('joinedStandBy')
def joined_stand_by():
    user = session['user']
    experiment_id = session['experiment_id']
    game = experiments[experiment_id]['game']
    score = game.score
    round_number = game.current_round
    socketio.emit('updateScoreRound', {'score': score, 'round': round_number}, 
                  room=request.sid)
    if experiments[experiment_id]['receiver'] == user:
        experiments[experiment_id]['receiver_sid'] = request.sid
    elif experiments[experiment_id]['sender'] == user:
        experiments[experiment_id]['sender_sid'] = request.sid
        

@socketio.on('joinedSender')
def joined_sender():
    experiment_id = session['experiment_id']
    game = experiments[experiment_id]['game']
    set = experiments[experiment_id]['set']
    stimulus, context = game.generate_sc()
    print(stimulus, context)
    socketio.emit('stimulus', {'st': f'static/sets/set-{set}/stimuli/{stimulus}-{context}.png'}, 
                                                  room=request.sid)

@socketio.on('buttonPressedSender')
def button_pressed(button_id):
    user = session['user']
    experiment_id = session['experiment_id']
    game = experiments[experiment_id]['game']

    button_ids = {1: 'rabu', 2: 'tabudiga'}
    game.log_word(button_ids[button_id])
    if experiments[experiment_id]['sender'] == user:
        socketio.emit('redirect', {'url': '/stand_by'}, room=request.sid)
    socketio.emit('redirect', {'url': '/receiver'}, room=experiments[experiment_id]['receiver_sid'])

@socketio.on('joinedReceiver')
def joined_receiver():
    experiment_id = session['experiment_id']
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
    button_ids = {1: 'C', 2: 'S', 3: 'T'}
    experiment_id = session['experiment_id']
    game = experiments[experiment_id]['game']
    game.c_stimulus_out = button_ids[button_id]
    socketio.emit('redirect', {'url': '/result'}, room=request.sid) 
    socketio.emit('redirect', {'url': '/result'}, room=experiments[experiment_id]['sender_sid'])

@socketio.on('joinedResult')
def joined_result():
    experiment_id = session['experiment_id']
    user = session['user']
    
    game = experiments[experiment_id]['game']
    stimulus_out = game.c_stimulus_out
    map_result = {True: 'Correct!', False: 'Incorrect!'}
    result = game.check(stimulus_out=stimulus_out)
    score = game.score
    round_number = game.current_round

    old_sender = experiments[experiment_id]['sender']
    old_receiver = experiments[experiment_id]['receiver']

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
        socketio.emit('redirect', {'url': '/personal'}, room=request.sid)
        receiver = experiments[experiment_id]['receiver']
        sender = experiments[experiment_id]['sender']
        set = experiments[experiment_id]['set']
        game.save_logs(f'{receiver}-{sender}-{set}-{COST_LONG}')
        pass

@socketio.on('joinedEndGame')
def joined_endgame():
    experiment_id = session['experiment_id']
    game = experiments[experiment_id]['game']
    socketio.emit('score', {'score': game.score}, room=request.sid)
    if game.score > 0:
        socketio.emit('prolificLink', LINK_BONUS, room=request.sid)
    else:
        socketio.emit('prolificLink', LINK_NO_BONUS, room=request.sid)
    receiver = experiments[experiment_id]['receiver']
    sender = experiments[experiment_id]['sender']
    set = experiments[experiment_id]['set']
    score = game.score
    with open('logs/participants.csv', 'a') as f:
        f.write(f'{experiment_id},{receiver},{sender},{score},set-{set}\n')

if __name__ == '__main__':
    socketio.run(app, debug=True, port=9021)