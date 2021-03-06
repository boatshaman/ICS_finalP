# -*- coding: utf-8 -*-
"""
Created on Sun Apr  5 00:00:32 2015

@author: zhengzhang
"""
from chat_utils import *
import json
from Crypto.PublicKey import RSA

class ClientSM:
    def __init__(self, s):
        self.state = S_OFFLINE
        self.peer = []
        self.me = ''
        self.out_msg = ''
        self.s = s
        self.peer_keys = {}
        self.rsa = None

    def set_state(self, state):
        self.state = state
        
    def get_state(self):
        return self.state
    
    def set_myname(self, name):
        self.me = name

    def get_myname(self):
        return self.me

    def set_rsa(self, rsa_obj):
        self.rsa = rsa_obj
        
    def connect_to(self, peer):
        msg = M_CONNECT + peer
        mysend(self.s, msg)
        response = myrecv(self.s)
        if response == (M_CONNECT+'ok'):
            self.peer = [peer]
            self.out_msg += 'Connecting to '+ peer + '...\n'
            return (True)
        elif response == (M_CONNECT + 'busy'):
            self.out_msg += 'User is busy. Please try again later\n'
        elif response == (M_CONNECT + 'hey you'):
            self.out_msg += 'Cannot talk to yourself (sick)\n'
        else:
            self.out_msg += 'User is not online, try again later\n'
        return(False)

    def disconnect(self):
        msg = M_DISCONNECT
        mysend(self.s, msg)
        self.out_msg += 'You are disconnected from ' + ' & '.join(self.peer) + '\n'
        self.peer = []

    def req_keys(self):
        mysend(self.s, K_RECV)
        resp = myrecv(self.s)
        self.peer_keys = json.loads(resp)

    def prep_msgs(self, msg):
        msg_dic = {}
        msg = msg.encode('utf-8')
        for k, v in self.peer_keys.items():
            ciph = RSA.importKey(v)
            msg_dic[k] = str(ciph.encrypt(msg, None)[0])
        return json.dumps(msg_dic)



    def proc(self, my_msg, peer_code, peer_msg):
        self.out_msg = ''
#==============================================================================
# Once logged in, do a few things: get peer listing, connect, search
# And, of course, if you are so bored, just go
# This is event handling instate "S_LOGGEDIN"
#==============================================================================
        if self.state == S_LOGGEDIN:
            # todo: can't deal with multiple lines yet
            if len(my_msg) > 0:
                
                if my_msg == 'q':
                    self.out_msg += 'See you next time!\n'
                    self.state = S_OFFLINE
                    
                elif my_msg == 'time':
                    mysend(self.s, M_TIME)
                    time_in = myrecv(self.s)
                    self.out_msg += "Time is: " + time_in
                            
                elif my_msg == 'who':
                    mysend(self.s, M_LIST)
                    logged_in = myrecv(self.s)
                    self.out_msg += 'Here are all the users in the system:\n'
                    self.out_msg += logged_in
                            
                elif my_msg[0] == 'c':
                    peer = my_msg[1:].strip()
                    if self.connect_to(peer) == True:
                        self.req_keys()
                        self.state = S_CHATTING
                        self.out_msg += 'Connected to ' + peer + '. Chat away!\n\n'
                        self.out_msg += '-----------------------------------\n'
                    else:
                        self.out_msg += 'Connection unsuccessful\n'
                        
                elif my_msg[0] == '?':
                    term = my_msg[1:].strip()
                    mysend(self.s, M_SEARCH + term)
                    search_rslt = myrecv(self.s)[1:].strip()
                    if (len(search_rslt)) > 0:
                        self.out_msg += search_rslt + '\n\n'
                    else:
                        self.out_msg += '\'' + term + '\'' + ' not found\n\n'
                        
                elif my_msg[0] == 'p':
                    poem_idx = my_msg[1:].strip()
                    mysend(self.s, M_POEM + poem_idx)
                    poem = myrecv(self.s)[1:].strip()
                    if (len(poem) > 0):
                        self.out_msg += poem + '\n\n'
                    else:
                        self.out_msg += 'Sonnet ' + poem_idx + ' not found\n\n'
                        
                else:
                    self.out_msg += menu
                    
            if len(peer_msg) > 0:
                if peer_code == M_CONNECT:
                    self.peer = [peer_msg]
                    self.req_keys()
                    self.out_msg += 'Request from ' + peer_msg + '\n'
                    self.out_msg += 'You are connected with ' + peer_msg 
                    self.out_msg += '. Chat away!\n\n'
                    self.out_msg += '------------------------------------\n'
                    self.state = S_CHATTING
                    
#==============================================================================
# Start chatting, 'bye' for quit
# This is event handling instate "S_CHATTING"
#==============================================================================
        elif self.state == S_CHATTING:
            if len(my_msg) > 0:     # My stuff, going out
                encoded_msgs = self.prep_msgs("[" + self.me + "] " + my_msg)
                mysend(self.s, M_EXCHANGE + encoded_msgs)
                if my_msg == 'bye':
                    self.disconnect()
                    self.state = S_LOGGEDIN
                    self.peer = []
            if len(peer_msg) > 0:   # Peer's stuff, coming in
                # New peer joins
                if peer_code == M_CONNECT:
                    self.out_msg += "(" + peer_msg + " joined)\n"
                    self.peer.append(peer_msg)
                    self.req_keys() #request new set of peer public keys
                else:
                    self.out_msg += peer_msg
            # I got bumped out
            if peer_code == M_DISCONNECT:
                self.out_msg += " has disconnected\n"
                self.peer.remove(peer_msg)
                if(len(self.peer) == 0):
                    self.state = S_LOGGEDIN

            # Display the menu again
            if self.state == S_LOGGEDIN:
                self.out_msg += menu
#==============================================================================
# invalid state                       
#==============================================================================
        else:
            self.out_msg += 'How did you wind up here??\n'
            print_state(self.state)
            
        return self.out_msg
