'''
Created on Sep 26, 2020

@author: willg
'''

class TierMogiPicklable(object):

    def __init__(self, mogi_list, channel_id:int, llt, lmlt, lmllut, st, lpt, bagger_count, runner_count, host, mogi_format, votes):
        '''
        Constructor
        '''
        self.mogi_list = mogi_list
        self.channel_id = channel_id
        self.last_list_time = llt
        self.last_ml_time = lmlt
        self.last_mllu_time = lmllut
        self.start_time = st
        self.last_ping_time = lpt
        self.bagger_count = bagger_count
        self.runner_count = runner_count
        self.host = host
        self.mogi_format = mogi_format
        self.votes = votes
        
    def __str__(self):
        result_str = ""
        for k, v in self.__dict__.items():
            result_str += f"{str(k)}: {str(v)}, "
        return result_str[:-2]
    def __repr__(self):
        return str(self)
    
    
    
    