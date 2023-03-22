import numpy as np 
from collections import defaultdict
import json
from datetime import datetime

class Game:
    def __init__(self, stimuli_context, rounds=100) -> None:
        self.stimuli_context = stimuli_context
        self.stimuli_prob = {s: 1/len(stimuli_context) for s in stimuli_context}
        self.stimuli_context_prob = {s: {c: 1/len(stimuli_context[s]) for c in stimuli_context[s]} for s in stimuli_context}

        self.rounds = rounds
        self.current_round = 0
        self.score = 0

        self.LOGS = defaultdict(dict)

    def generate_sc(self):
        '''Randomly choose a stimuli context pair for the sender'''
        stimulus = np.random.choice(list(self.stimuli_context.keys()), 
                                    p=[self.stimuli_prob[s] for s in self.stimuli_context])
        context = np.random.choice(self.stimuli_context[stimulus],
                                      p=[self.stimuli_context_prob[stimulus][c] for c in self.stimuli_context[stimulus]])
        self.current_round += 1
        self.LOGS[self.current_round]['stimulus'] = stimulus
        self.LOGS[self.current_round]['context'] = context
        return stimulus, context
    
    def log_word(self, word):
        '''Log the word that was sent by the sender'''
        self.LOGS[self.current_round]['word'] = word

    def check(self, stimulus_out, stimulus):
        '''Check if the stimulus chosen by the receiver is correct'''
        if self.current_round <= self.rounds:
            self.LOGS[self.current_round]['stimulus_out'] = stimulus_out
            if stimulus_out == stimulus:
                # if correct, increment score
                self.score += 1
                self.LOGS[self.current_round]['correct'] = True
                self.LOGS[self.current_round]['score'] = self.score
                return True
            else:
                # if wrong, do not increment score
                self.LOGS[self.current_round]['correct'] = False
                self.LOGS[self.current_round]['score'] = self.score
                return False
        else:
            # remove last entry from logs
            self.LOGS.pop(self.current_round)
            # # save logs to json file
            # self.save_logs()
            raise Exception('Game has ended')
    
    def save_logs(self):
        # save logs to json file
        with open(f'logs/logging-{datetime.now().strftime("%Y%m%d%H%M%S")}.json', 'w') as f:
            json.dump(self.LOGS, f)

if __name__ == '__main__':
    a = Game({'T': ['r', 'l'], 'C': ['r'], 'S': ['l']}, rounds=10)
