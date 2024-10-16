from flask import (Flask, 
                   render_template, 
                   request, 
                   redirect, 
                   make_response,
                   session)
from flask_socketio import SocketIO
import random
from time import sleep
import datetime
from collections import defaultdict
from game import Game
import os
import pickle

### FLASK SETUP ###

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fdhjdfkhv!JJJfdsjkkjnsd'
socketio = SocketIO(app, ping_timeout=5000, ping_interval=10000)
app.config['CONTEXT_FOLDER'] = os.path.join('static', 'context')


### GLOBAL ###

NROUNDS = 42
# COST_SHORT = 1
# COST_LONG = 4
COST_SHORT = 3.6
COST_LONG = 8.4

LINK_BONUS = "https://app.prolific.com/submissions/complete?cc=C73N4S3V"
LINK_NO_BONUS = "https://app.prolific.com/submissions/complete?cc=CS7YZZVX"

experiments = defaultdict(dict)
experiments_queue = []
usernames = []

rgb_hex = {'red': '#ff0000', 
           'green': '#0b7821', 
           'blue': '#0000ff', 
           'yellow': '#ffff00',
           'purple': '#ff00ff'}

# short_words = ['cauv', 'urbe', 'fusk', 'tarb', 'demb', 
#                'gyte', 'kilv', 'yirv', 'weff', 'ciff']
# long_words = ['ghrertch', 'chawntch', 'wroarnte', 'shoughse', 'thwisque', 
#               'strourgn', 'sprource', 'ghleente', 'phroughm', 'ghleuche']

short_words = ['diz', 'bib', 'kle', 'sca', 'fli', 
               'nif', 'pit', 'own', 'zep', 'tue']
long_words = ['rewakes', 'chatial', 'ligorir', 'untubeg', 'derotfo', 
               'ableick', 'soculif', 'oasepud', 'corgora', 'adafule']

### ROUTES ###

@app.route('/')
def description1():
    response = make_response(render_template('description1.html', 
                                             cost_long=COST_LONG, 
                                             cost_short=COST_SHORT, 
                                             nrounds=NROUNDS))
    return response

@app.route('/description2')
def description2():
    return render_template('description2.html')

@app.route('/description3')
def description3():
    return render_template('description3.html')

@app.route('/start', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        s = random.randint(1, 9)
        w_i = random.randint(0, 9)
        short_word = short_words[w_i]
        long_word = long_words[w_i]
        user_in = request.form['nickname']
        if user_in in usernames:
            return render_template('index.html', error='You have already completed the experiment.')
        else:
            usernames.append(user_in)
            if len(experiments_queue) > 0:
                experiment_id = experiments_queue.pop()
                experiments[experiment_id]['sender'] = user_in
                experiments[experiment_id]['set'] = s
                experiments[experiment_id]['short_word'] = short_word
                experiments[experiment_id]['long_word'] = long_word
                experiments[experiment_id]['left'] = False
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
def stand_by():
    return render_template('stand_by.html',
                           nrounds=NROUNDS)

@app.route('/sender')
def sender():
    experiment_id = session['experiment_id']
    set = experiments[experiment_id]['set']
    game = experiments[experiment_id]['game']

    short_word = experiments[experiment_id]['short_word']
    long_word = experiments[experiment_id]['long_word']

    if game.current_round == 0:
        session['start_time'] = datetime.datetime.now()
    return render_template('sender.html', 
                           cost_long=COST_LONG*1000, 
                           cost_short=COST_SHORT*1000, 
                           folder = f'set-{set}',
                           short = short_word,
                           long = long_word)

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
    # get short and long words from experiments
    experiment_id = session['experiment_id']
    short_word = experiments[experiment_id]['short_word']
    long_word = experiments[experiment_id]['long_word']
    if request.method == 'POST':
        user = session['user']
        age = request.form['age']
        gender = request.form['gender']
        tabugida = request.form['tabugida']
        rabu = request.form['rabu']

        with open('logs/personal.csv', 'a') as f:
            f.write(f'{user},{age},{gender},{tabugida},{rabu}\n')

        return redirect('/endgame')
    return render_template('personal.html', short = short_word, long = long_word)

@app.route('/timeout')
def timeout():
    user = session['user']
    return render_template('timeout.html', user=user, link=LINK_NO_BONUS)

@app.route('/leftgame')
def leftgame():
    return render_template('leftgame.html', link=LINK_NO_BONUS)

### SOCKET.IO ###

@socketio.on('readyToContinue')
def ready_to_continue():
    socketio.emit('redirect', {'url': '/start'}, room=request.sid)

@socketio.on('joinedWaiting')
def joined_waiting_room():
    user = session['user']
    experiment_id = session['experiment_id']
    experiments[experiment_id]['game'] = Game({'T': ['r'], 'C': ['l'], 'S': ['r', 'l']}, 
                                              rounds=NROUNDS)
    while experiments[experiment_id]['sender'] is None:
        sleep(1)
    if experiments[experiment_id]['receiver'] == user:
        socketio.emit('redirect', {'url': '/stand_by'}, room=request.sid)
    elif experiments[experiment_id]['sender'] == user:
        socketio.emit('redirect', {'url': '/sender'}, room=request.sid)

@socketio.on('timerDone')
def timer_done():
    '''If no one joins the user after 15 minutes'''
    socketio.emit('redirect', {'url': '/timeout'}, room=request.sid)

@socketio.on('timerDone2')
def timer_done2():
    '''If one of the players leaves the game'''
    experiment_id = session['experiment_id']
    if experiments[experiment_id]['left'] is False:
        experiments[experiment_id]['left'] = True
        socketio.emit('redirect', {'url': '/timeout'}, room=request.sid)

    if experiments[experiment_id]['left'] is True:
        socketio.emit('redirect', {'url': '/leftgame'}, room=request.sid)
    else:
        experiments[experiment_id]['left'] = True
        socketio.emit('redirect', {'url': '/timeout'}, room=request.sid)

# @socketio.on('UserLeftClicked')
# def user_left_clicked():
#     user = session['user']
#     experiment_id = session['experiment_id']
#     if experiments[experiment_id]['receiver'] == user:
#         print('receiver left')
#         socketio.emit('redirect', {'url': '/leftgame'}, namespace = '/sender', room=experiments[experiment_id]['sender_sid'])
#     else:
#         print('sender left')
#         socketio.emit('redirect', {'url': '/leftgame'}, namespace='/receiver', room=experiments[experiment_id]['receiver_sid'])

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
    socketio.emit('stimulus', {'st': f'static/sets/set-{set}/stimuli/{stimulus}-{context}.png'}, 
                                                  room=request.sid)

@socketio.on('buttonPressedSender')
def button_pressed_sender(button_id):
    user = session['user']
    experiment_id = session['experiment_id']
    game = experiments[experiment_id]['game']

    button_ids = {1: experiments[experiment_id]['short_word'], 2: experiments[experiment_id]['long_word']}
    game.log_word(button_ids[button_id])
    if experiments[experiment_id]['sender'] == user:
        if experiments[experiment_id]['left'] is True:
            socketio.emit('redirect', {'url': '/leftgame'}, room=request.sid)
        else:
            socketio.emit('redirect', {'url': '/stand_by'}, room=request.sid)
    socketio.emit('redirect', {'url': '/receiver'}, room=experiments[experiment_id]['receiver_sid'])

@socketio.on('joinedReceiver')
def joined_receiver():
    experiment_id = session['experiment_id']
    game = experiments[experiment_id]['game']
    context = game.c_context

    set = experiments[experiment_id]['set']
    # open file filenames.pickle
    with open(f'static/sets/set-{set}/filenames.pkl', 'rb') as f:
        filenames = pickle.load(f)

    socketio.emit('contextWord', {'color': filenames[context], 
                                  'word': game.c_word,
                                  'hex': rgb_hex[filenames[context]]}, room=request.sid)

@socketio.on('buttonPressedReceiver')
def button_pressed_receiver(button_id):
    button_ids = {1: 'C', 2: 'S', 3: 'T'}
    experiment_id = session['experiment_id']
    game = experiments[experiment_id]['game']
    game.c_stimulus_out = button_ids[button_id]
    if experiments[experiment_id]['left'] is True:
        socketio.emit('redirect', {'url': '/leftgame'}, room=request.sid)
    else:
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
    socketio.run(app, debug=False, port=9022)
