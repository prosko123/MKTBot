'''
Created on Sep 26, 2020

@author: willg
'''
from datetime import datetime, timedelta
warn_drop_period = timedelta(minutes=25)
drop_period = timedelta(minutes=30)

class PlayerPicklable(object):
    '''
    classdocs
    '''


    def __init__(self, member_id:int, runner:bool, last_message_time, join_time, warned_already:bool, rating):
        '''
        Constructor
        '''
        self.member_id = member_id
        self.runner = runner
        self.last_message_time = last_message_time
        self.join_time = join_time
        self.warned_already = warned_already
        self.rating = rating
        
    def __str__(self):
        result_str = ""
        for k, v in self.__dict__.items():
            result_str += f"{str(k)}: {str(v)}, "
        return result_str[:-2]
    def __repr__(self):
        return str(self)
    