# --------------------------------------------------------------------------------------------------------------------
# Copyright (C) Microsoft Corporation.  All rights reserved.
# --------------------------------------------------------------------------------------------------------------------

# The "Cliff Walking" example using Q-learning.
# From pages 148-150 of:
# Richard S. Sutton and Andrews G. Barto
# Reinforcement Learning, An Introduction
# MIT Press, 1998

import MalmoPython
import json
import logging
import os
import random
import sys
import time
import Tkinter as tk

class TabQAgent:
    """Tabular Q-learning agent for discrete state/action spaces."""

    def __init__(self, actions=[], epsilon=0.1, alpha=0.1, gamma=1.0, debug=False, canvas=None, root=None):
        self.epsilon = epsilon
        self.alpha = alpha
        self.gamma = gamma
        self.training = True

        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.logger.handlers = []
        self.logger.addHandler(logging.StreamHandler(sys.stdout))

        self.actions = actions
        self.q_table = {}
        self.canvas = canvas
        self.root = root

    def loadModel(self, model_file):
        """load q table from model_file"""
        with open(model_file) as f:
            self.q_table = json.load(f)

    def training(self):
        """switch to training mode"""
        self.training = True


    def evaluate(self):
        """switch to evaluation mode (no training)"""
        self.training = False

    def act(self, world_state, agent_host, current_r ):
        """take 1 action in response to the current world state"""
        
        obs_text = world_state.observations[-1].text
        obs = json.loads(obs_text) # most recent observation
        self.logger.debug(obs)
        if not u'XPos' in obs or not u'ZPos' in obs:
            self.logger.error("Incomplete observation received: %s" % obs_text)
            return 0
        current_s = "%d:%d" % (int(obs[u'XPos']), int(obs[u'ZPos']))
        self.logger.debug("State: %s (x = %.2f, z = %.2f)" % (current_s, float(obs[u'XPos']), float(obs[u'ZPos'])))
        if not self.q_table.has_key(current_s):
            self.q_table[current_s] = ([0] * len(self.actions))

        # update Q values
        if self.training and self.prev_s is not None and self.prev_a is not None:
            old_q = self.q_table[self.prev_s][self.prev_a]
            self.q_table[self.prev_s][self.prev_a] = old_q + self.alpha * (current_r
                + self.gamma * max(self.q_table[current_s]) - old_q)

        self.drawQ( curr_x = int(obs[u'XPos']), curr_y = int(obs[u'ZPos']) )

        # select the next action
        rnd = random.random()
        if rnd < self.epsilon:
            a = random.randint(0, len(self.actions) - 1)
            self.logger.info("Random action: %s" % self.actions[a])
        else:
            m = max(self.q_table[current_s])
            self.logger.debug("Current values: %s" % ",".join(str(x) for x in self.q_table[current_s]))
            l = list()
            for x in range(0, len(self.actions)):
                if self.q_table[current_s][x] == m:
                    l.append(x)
            y = random.randint(0, len(l)-1)
            a = l[y]
            self.logger.info("Taking q action: %s" % self.actions[a])

        # try to send the selected action, only update prev_s if this succeeds
        try:
            agent_host.sendCommand(self.actions[a])
            self.prev_s = current_s
            self.prev_a = a

        except RuntimeError as e:
            self.logger.error("Failed to send command: %s" % e)

        return current_r

    def run(self, agent_host):
        """run the agent on the world"""

        total_reward = 0
        
        self.prev_s = None
        self.prev_a = None
        
        is_first_action = True
        
        # main loop:
        world_state = agent_host.getWorldState()
        while world_state.is_mission_running:

            current_r = 0
            
            if is_first_action:
                # wait until have received a valid observation
                while True:
                    time.sleep(0.1)
                    world_state = agent_host.getWorldState()
                    for error in world_state.errors:
                        self.logger.error("Error: %s" % error.text)
                    for reward in world_state.rewards:
                        current_r += reward.value
                    if world_state.is_mission_running and len(world_state.observations)>0 and not world_state.observations[-1].text=="{}":
                        total_reward += self.act(world_state, agent_host, current_r)
                        break
                    if not world_state.is_mission_running:
                        break
                is_first_action = False
            else:
                # wait for non-zero reward
                while world_state.is_mission_running and current_r == 0:
                    time.sleep(0.1)
                    world_state = agent_host.getWorldState()
                    for error in world_state.errors:
                        self.logger.error("Error: %s" % error.text)
                    for reward in world_state.rewards:
                        current_r += reward.value
                # allow time to stabilise after action
                while True:
                    time.sleep(0.1)
                    world_state = agent_host.getWorldState()
                    for error in world_state.errors:
                        self.logger.error("Error: %s" % error.text)
                    for reward in world_state.rewards:
                        current_r += reward.value
                    if world_state.is_mission_running and len(world_state.observations)>0 and not world_state.observations[-1].text=="{}":
                        total_reward += self.act(world_state, agent_host, current_r)
                        break
                    if not world_state.is_mission_running:
                        break

        # process final reward
        self.logger.debug("Final reward: %d" % current_r)
        total_reward += current_r

        # update Q values
        if self.training and self.prev_s is not None and self.prev_a is not None:
            old_q = self.q_table[self.prev_s][self.prev_a]
            self.q_table[self.prev_s][self.prev_a] = old_q + self.alpha * ( current_r - old_q )
            
        self.drawQ()
    
        return total_reward
        
    def drawQ( self, curr_x=None, curr_y=None ):
        if self.canvas is None or self.root is None:
            return
        self.canvas.delete("all")
        action_inset = 0.1
        action_radius = 0.1
        curr_radius = 0.2
        action_positions = [ ( 0.5, action_inset ), ( 0.5, 1-action_inset ), ( action_inset, 0.5 ), ( 1-action_inset, 0.5 ) ]
        # (NSWE to match action order)
        min_value = -20
        max_value = 20
        for x in range(world_x):
            for y in range(world_y):
                s = "%d:%d" % (x,y)
                self.canvas.create_rectangle( x*scale, y*scale, (x+1)*scale, (y+1)*scale, outline="#fff", fill="#000")
                for action in range(4):
                    if not s in self.q_table:
                        continue
                    value = self.q_table[s][action]
                    color = 255 * ( value - min_value ) / ( max_value - min_value ) # map value to 0-255
                    color = max( min( color, 255 ), 0 ) # ensure within [0,255]
                    color_string = '#%02x%02x%02x' % (255-color, color, 0)
                    self.canvas.create_oval( (x + action_positions[action][0] - action_radius ) *scale,
                                             (y + action_positions[action][1] - action_radius ) *scale,
                                             (x + action_positions[action][0] + action_radius ) *scale,
                                             (y + action_positions[action][1] + action_radius ) *scale, 
                                             outline=color_string, fill=color_string )
        if curr_x is not None and curr_y is not None:
            self.canvas.create_oval( (curr_x + 0.5 - curr_radius ) * scale, 
                                     (curr_y + 0.5 - curr_radius ) * scale, 
                                     (curr_x + 0.5 + curr_radius ) * scale, 
                                     (curr_y + 0.5 + curr_radius ) * scale, 
                                     outline="#fff", fill="#fff" )
        self.root.update()

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately

agent_host = MalmoPython.AgentHost()

# add some args
agent_host.addOptionalStringArgument('mission_file',
    'Path/to/file from which to load the mission.', '../Sample_missions/cliff_walking_1.xml')
agent_host.addOptionalFloatArgument('alpha',
    'Learning rate of the Q-learning agent.', 0.1)
agent_host.addOptionalFloatArgument('epsilon',
    'Exploration rate of the Q-learning agent.', 0.01)
agent_host.addOptionalFloatArgument('gamma', 'Discount factor.', 1.0)
agent_host.addOptionalFlag('load_model', 'Load initial model from model_file.')
agent_host.addOptionalStringArgument('model_file', 'Path to the initial model file', '')
agent_host.addOptionalFlag('debug', 'Turn on debugging.')

try:
    agent_host.parse( sys.argv )
except RuntimeError as e:
    print 'ERROR:',e
    print agent_host.getUsage()
    exit(1)
if agent_host.receivedArgument("help"):
    print agent_host.getUsage()
    exit(0)

# -- set up the python-side drawing -- #
scale = 40
world_x = 6
world_y = 14
root = tk.Tk()
root.wm_title("Q-table")
canvas = tk.Canvas(root, width=world_x*scale, height=world_y*scale, borderwidth=0, highlightthickness=0, bg="black")
canvas.grid()
root.update()

imap = 0
while True: # for demo purposes, leave running on different missions each time
    
    imap += 1

    # -- set up the agent -- #
    #actionSet = ["movenorth 1", "movesouth 1", "movewest 1", "moveeast 1", "turn 1", "turn -1"]
    actionSet = ["movenorth 1", "movesouth 1", "movewest 1", "moveeast 1"]

    agent = TabQAgent(
        actions=actionSet,
        epsilon=agent_host.getFloatArgument('epsilon'),
        alpha=agent_host.getFloatArgument('alpha'),
        gamma=agent_host.getFloatArgument('gamma'),
        debug = agent_host.receivedArgument("debug"),
        canvas = canvas,
        root = root)

    # -- set up the mission -- #
    mission_file = agent_host.getStringArgument('mission_file')
    with open(mission_file, 'r') as f:
        print "Loading mission from %s" % mission_file
        mission_xml = f.read()
        my_mission = MalmoPython.MissionSpec(mission_xml, True)
    my_mission.removeAllCommandHandlers()
    my_mission.allowAllDiscreteMovementCommands()
    my_mission.requestVideo( 320, 240 )
    # add 20% holes for interest
    for x in range(1,4):
        for z in range(1,13):
            if random.random()<0.1:
                my_mission.drawBlock( x,45,z,"lava")

    my_clients = MalmoPython.ClientPool()
    my_clients.add(MalmoPython.ClientInfo('127.0.0.1', 10000)) # add Minecraft machines here as available

    max_retries = 3
    agentID = 0
    expID = 'tabular_q_learning'

    num_repeats = 150
    cumulative_rewards = []
    for i in range(num_repeats):
        
        print "\nMap %d - Mission %d of %d:" % ( imap, i+1, num_repeats )

        my_mission_record = MalmoPython.MissionRecordSpec( "./save_%s-map%d-rep%d.tgz" % (expID, imap, i) )
        my_mission_record.recordCommands()
        my_mission_record.recordMP4(20, 400000)
        my_mission_record.recordRewards()
        my_mission_record.recordObservations()

        for retry in range(max_retries):
            try:
                agent_host.startMission( my_mission, my_clients, my_mission_record, agentID, "%s-%d" % (expID, i) )
                break
            except RuntimeError as e:
                if retry == max_retries - 1:
                    print "Error starting mission:",e
                    exit(1)
                else:
                    time.sleep(2.5)

        print "Waiting for the mission to start",
        world_state = agent_host.getWorldState()
        while not world_state.is_mission_running:
            sys.stdout.write(".")
            time.sleep(0.1)
            world_state = agent_host.getWorldState()
            for error in world_state.errors:
                print "Error:",error.text
        print

        # -- run the agent in the world -- #
        cumulative_reward = agent.run(agent_host)
        print 'Cumulative reward: %d' % cumulative_reward
        cumulative_rewards += [ cumulative_reward ]

        # -- clean up -- #
        time.sleep(0.5) # (let the Mod reset)

    print "Done."

    print
    print "Cumulative rewards for all %d runs:" % num_repeats
    print cumulative_rewards

#root.mainloop() # keep the visualization window alive for viewing until closed