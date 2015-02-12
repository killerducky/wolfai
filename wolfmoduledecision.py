"""
--------------------------------------------------
Current
--------------------------------------------------
input:
0 self.ww
1 self.v
2 turn=0   maybe don't need this, lack of claims will make it obvious
3 turn=1
4 p1.claim.ww
5 p1.claim.v
6 p2.claim.ww
7 p2.claim.v

output:
0 claim.ww
1 claim.v
- vote1
- vote2
- vote3
- vote4
- p1.vote0
- p1.vote2
- p1.vote3
- p1.vote4

numInputs  = 4+numPlayers*2  # self.ww, self.v, turn1, turn2, numPlayers*(p#.claim.ww, p#.claimv)
numOutputs = 2+1*(numPlayers-1)  # claim.ww, claim.v, (numPlayers-1)*(p#.vote)

--------------------------------------------------
Full ww, s, r, tm, i, v
--------------------------------------------------
input:
        R self.myrole
          turn=-1                         receive role, output our choice. For now just hardcode that part of AI
        1 turn=0                          receive self.x input, output self.claim and self.vote
        1 turn=1                          receive other's claims and votes, update our claims and votes
        1 turn=2                          receive updates to other's claims and votes, do real vote
        R self.claimrole                  remember past self claims
    Nm1+1 self.claimrole.target1
      Nm1 self.claimrole.target2
        R self.claimrole.target1role
        R self.claimrole.target2role
Nm1*    R oppN.claimrole
Nm1*Nm1+1 oppN.claimrole.target1
Nm1*  Nm1 oppN.claimrole.target2
Nm1*    R oppN.claimrole.target1role
Nm1*    R oppN.claimrole.target2role
      Nm1 self.vote.oppN                  remember past self vote claims
Nm1*  Nm1 oppN.vote.oppN
=======
lie vectors for claims   3*Nm1 = 3*5 = 15
  0.0 = neutral
  0.1 = changed claim
  0.5 = conflicting claim
  1.0 = we know it's false
  Nm1  oppN.claimrole
  Nm1  oppN.claimrole.target1role
  Nm1  oppN.claimrole.target2role
=======
claim = 3R+2Nm1+1 = 3*6+2*4+1 = 18+8+1 = 27
all = R+3+N*claim+N*Nm1 =
      6+3+6*27+5*4
      9+162+20
      191
=======
output:
R   claimrole
Nm1 vote
"""

from __future__ import print_function
from scipy import zeros, ones
#from pybrain.rl.environments.twoplayergames import CaptureGame    # CaptureGame is an Agent
from pybrain.rl.agents.agent import Agent
#from .randomplayer import RandomCapturePlayer
from pybrain.utilities import drawGibbs  # TODO this could be useful
import random


class WolfModuleDecidingPlayer(Agent):
    """ A Capture-game player that plays according to the rules, but choosing its moves
    according to the output of a module that takes as input the current state of the board. """

    # temperature = 1 for Gibbs-sampling
    # temperature = 0 for greedy (always pick largest output in vote vector)
    temperature = 0.

    def __init__(self, module, *args, **kwargs):
        self.module = module
        self.pnum = None    # TODO it's dumb to let them know their own pnum this way

    def getAction(self):
        """ get suggested action, return them if they are legal, otherwise choose randomly. """
        # Module player is always assumed player #0
        state = [0] * (4+self.game.numPlayers*2)
        state[0] = (0,1)[self.game.roles[0] == "Werewolf"]
        state[1] = (0,1)[self.game.roles[0] == "Villager"]
        state[2] = (0,1)[self.game.turnnum == 0]
        state[3] = (0,1)[self.game.turnnum == 1]
        for i in range(len(self.game.claim)):
          state[4+i*2+0] = (0,1)[self.game.claim[i] == "Werewolf"]
          state[4+i*2+1] = (0,1)[self.game.claim[i] == "Villager"]
          #state[4+i*2+0] = (0,1)[self.game.roles[0] == "Werewolf"]
          #state[4+i*2+1] = (0,1)[self.game.roles[0] == "Villager"]
        self.module.reset()
        output = self.module.activate(state)
        result = None
        if (self.game.turnnum == 0):
          if output[0] > output[1]: result = "Werewolf"
          else                    : result = "Villager"
        else:
          votes = output[2:]
          result = drawGibbs(votes, self.temperature) + 1
          #print ("votes, result", votes, result)
        #print ()
        #print ("input", state)
        #print (self.game.stateStr())
        #print ("output", output, result)
        #print ()
        return [self.pnum, result]

    def newEpisode(self):
        self.module.reset()

    def integrateObservation(self, obs = None):
        pass


