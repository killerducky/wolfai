"""
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
from pybrain.rl.agents.agent import Agent
from pybrain.utilities import drawGibbs
import random
from simplewolfplayer import SimpleWolfPlayer
from wolfmodbot import WolfModBot, Role, Claim


class NnWolfBot(Agent):
  """ A Capture-game player that plays according to the rules, but choosing its moves
  according to the output of a module that takes as input the current state of the board. """

  numInputs = 174
  numOutputs = 33

  # temperature = 1 for Gibbs-sampling
  # temperature = 0 for greedy (always pick largest output in vote vector)
  temperature = 0.

  def __init__(self, module, name, modbot, *args, **kwargs):
    self.module = module
    self.name   = name
    self.modbot = modbot
    self.fb     = SimpleWolfPlayer(name, modbot)
    self.supportedRoles = [
      Role.Roles.Werewolf,
      Role.Roles.Seer,
      Role.Roles.Robber,
      Role.Roles.Troublemaker,
      Role.Roles.Insomniac,
      Role.Roles.Villager
    ]
    self.gameReset()

  def gameStart(self):
    self.normedPlayers = list(self.modbot.live_players)
    #self.myidx = (i for i,p in enumerate(self.normedPlayers) if p.nickname == self.name).next()
    self.myidx = None
    print ("me=%s" % self.name)
    for i,p in enumerate(self.normedPlayers):
      print ("nick=%s" % p.nickname)
      if p.nickname == self.name:
        self.myidx = i
        break
    self.normedPlayers[0], self.normedPlayers[self.myidx] = self.normedPlayers[self.myidx], self.normedPlayers[0]
    self.normedNames = [p.nickname for p in self.normedPlayers]

  def gameReset(self):
    self.normedPlayers = None

  def encode(self, state, pos, invalue, values):
    for v in values:
      state[pos] = (0,1)[invalue == v]
      pos += 1
    return pos

  def decode(self, encodedVal, pos, values):
    result = drawGibbs(encodedVal[pos:pos+len(values)-1], self.temperature) + 1
    pos += len(values)
    return (pos, values[result])

  def getAction(self):
    """ get suggested action, return them if they are legal, otherwise choose randomly. """
    if not self.normedPlayers:
      self.gameStart()
    player = self.modbot.find_player(self.name)
    print ("getAction for name=%s role=%s" % (self.name, player.orig_role))
    if self.modbot.gamestate != self.modbot.GAMESTATE_RUNNING:
      raise
    if self.modbot.time != "day":
      print ("day")
      self.fb.getAction() # Don't use NN for this part
      return


    # Module player is always assumed player #0
    state = [0] * self.numInputs
    pos = 0
    pos = self.encode(state, pos, player.orig_role, self.supportedRoles)
    pos = self.encode(state, pos, self.modbot.turnnum, range(0,2+1))
    for p in self.normedPlayers:
      pos = self.encode(state, pos, p.claim.role,            self.supportedRoles)
      pos = self.encode(state, pos, p.claim.targets[0] if len(p.claim.targets)>=1 else None,      self.normedNames)
      pos = self.encode(state, pos, p.claim.targets[1] if len(p.claim.targets)>=2 else None,      self.normedNames)
      pos = self.encode(state, pos, p.claim.target_roles[0] if len(p.claim.target_roles)>=1 else None, self.supportedRoles)
      pos = self.encode(state, pos, p.claim.target_roles[1] if len(p.claim.target_roles)>=2 else None, self.supportedRoles)
      voteVector = [0]*len(self.normedNames)
      for i,name in enumerate(self.normedNames):
        if name in p.claim.votes:
          voteVector[i] = 1
      state[pos:pos+len(self.normedNames)] = voteVector
      pos += len(self.normedNames)
    print ("input pos = ", pos)
    self.module.reset()
    output = self.module.activate(state)
    claim = Claim(None, [None]*2, [None]*2, [])
    pos = 0
    # TODO handle cases were we don't claim things
    (pos, claim.role)            = self.decode(output, pos, self.supportedRoles)
    (pos, claim.targets[0])      = self.decode(output, pos, self.normedNames)
    (pos, claim.targets[1])      = self.decode(output, pos, self.normedNames)
    (pos, claim.target_roles[0]) = self.decode(output, pos, self.supportedRoles)
    (pos, claim.target_roles[1]) = self.decode(output, pos, self.supportedRoles)
    votes = output[pos:pos+len(self.normedNames)-1]
    votes[0] = 0 # Do not vote for self
    pos += len(self.normedNames)
    for i,v in enumerate(votes):
      if v > 0.5: claim.votes.append(self.normedNames[i])
    print ("output pos = ", pos)
    if (self.modbot.turnnum < 2):
      self.modbot.claim(self.fb.e, claim)
    else:
      vote = drawGibbs(votes)
      self.modbot.cmd_vote([self.normedNames[vote]], self.fb.e)
      print ("vote", vote, self.normedNames[vote])
    #print ()
    #print ("input", state)
    #print (self.modbot.stateStr())
    #print ("output", output, result)
    #print ()


