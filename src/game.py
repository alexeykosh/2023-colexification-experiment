import numpy as np 
from collections import defaultdict
import json
from datetime import datetime

class Game:
    def __init__(self, stimuli_context, rounds=100):
        self.stimuli_context = stimuli_context
        # self.stimuli_prob = {s: 1/len(stimuli_context) for s in stimuli_context}
        # self.stimuli_context_prob = {s: {c: 1/len(stimuli_context[s]) for c in stimuli_context[s]} for s in stimuli_context}
        ind = int(rounds / 3)
        self.stimuli_arr = self.shuffle_stimuli(['T-r'] * ind + ['C-l'] * ind + ['S-r'] * int(ind/2) + ['S-l'] * int(ind/2))

        self.rounds = rounds
        self.current_round = 0
        self.score = 0

        self.n_checks = 0
        self.c_stimulus = None
        self.c_context = None
        self.c_word = None
        self.c_stimulus_out = None
        self.LOGS = defaultdict(dict)



    # def generate_sc(self):
    #     '''Randomly choose a stimuli context pair for the sender'''
    #     self.n_checks += 1
    #     if self.n_checks == 1:
    #         stimulus = np.random.choice(list(self.stimuli_context.keys()), 
    #                                     p=[self.stimuli_prob[s] for s in self.stimuli_context])
    #         context = np.random.choice(self.stimuli_context[stimulus],
    #                                     p=[self.stimuli_context_prob[stimulus][c] for c in self.stimuli_context[stimulus]])
    #         # if new stimulus and context are the same as the previous round, generate new ones
    #         while stimulus == self.c_stimulus and context == self.c_context:
    #             stimulus = np.random.choice(list(self.stimuli_context.keys()), 
    #                                         p=[self.stimuli_prob[s] for s in self.stimuli_context])
    #             context = np.random.choice(self.stimuli_context[stimulus],
    #                                         p=[self.stimuli_context_prob[stimulus][c] for c in self.stimuli_context[stimulus]])
    #         if self.n_checks == 1:
    #             self.current_round += 1
    #         self.LOGS[self.current_round]['stimulus'] = stimulus
    #         self.LOGS[self.current_round]['context'] = context
            
    #         self.c_stimulus = str(stimulus)
    #         self.c_context = str(context)
    #         return str(stimulus), str(context)
    #     else:
    #         return self.c_stimulus, self.c_context

    @staticmethod
    def shuffle_stimuli(stimuli_arr):
        rounds = len(stimuli_arr)
        while any([stimuli_arr[i] == stimuli_arr[i+1] == 
                   stimuli_arr[i+2] for i in range(rounds-2)]):
            stimuli_arr = np.random.permutation(stimuli_arr)
        return stimuli_arr

    def generate_sc(self):
        self.n_checks += 1
        if self.n_checks == 1:
            stimulus_context = self.stimuli_arr[self.current_round]

            if self.n_checks == 1:
                self.current_round += 1
            
            self.LOGS[self.current_round]['stimulus'] = stimulus_context[0]
            self.LOGS[self.current_round]['context'] = stimulus_context[2]

            self.c_stimulus = str(stimulus_context[0])
            self.c_context = str(stimulus_context[2])

            return str(stimulus_context[0]), str(stimulus_context[2])
        else:
            return self.c_stimulus, self.c_context
            
    
    def log_word(self, word):
        '''Log the word that was sent by the sender'''
        self.LOGS[self.current_round]['word'] = word
        self.c_word = word

    def check(self, stimulus_out):
        '''Check if the stimulus chosen by the receiver is correct'''
        self.n_checks += 1
        self.LOGS[self.current_round]['stimulus_out'] = stimulus_out
        if stimulus_out == self.c_stimulus:
            if self.n_checks == 2:
                self.score += 1
            self.LOGS[self.current_round]['correct'] = True
            self.LOGS[self.current_round]['score'] = self.score
            self.n_checks = 0
            return True
        else:
            self.LOGS[self.current_round]['correct'] = False
            self.LOGS[self.current_round]['score'] = self.score
            self.n_checks = 0
            return False
    
    def save_logs(self, name):
        # save logs to json file
        with open(f'logs/{name}-{datetime.now().strftime("%Y%m%d%H%M%S")}.json', 'w') as f:
            json.dump(self.LOGS, f)