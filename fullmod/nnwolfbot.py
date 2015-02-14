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

  numInputs = 196
  numOutputs = 41

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
    for i,p in enumerate(self.normedPlayers):
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
    bits = encodedVal[pos:pos+len(values)-1]
    result = drawGibbs(encodedVal[pos:pos+len(values)-1], self.temperature) + 1
    pos += len(values)
    return (pos, bits, values[result])

  def decodeClaim(self, output, pos):
    claim = Claim(None, [None]*2, [None]*2, [])
    (pos, _, claim.role)            = self.decode(output, pos, self.supportedRoles + [None])
    (pos, _, night_action_type)     = self.decode(output, pos, [0,1,None])
    (pos, t0bits, claim.targets[0]) = self.decode(output, pos, self.normedNames + [None])
    (pos, t1bits, claim.targets[1]) = self.decode(output, pos, self.normedNames + [None])
    (pos, _, claim.target_roles[0]) = self.decode(output, pos, self.supportedRoles + [None])
    (pos, _, claim.target_roles[1]) = self.decode(output, pos, self.supportedRoles + [None])
    if False: pass
    elif claim.role == Role.Roles.Werewolf:
      if (night_action_type == 1):
        # Lone wolf claim
        (_, _, claim.targets[0]) = self.decode(t0bits, 0, ["left", "middle", "right", None])
        claim.targets = claim.targets[:1]
      else:
        # TODO for now only handling 2 wolf case
        claim.targets = claim.targets[:1]
        claim.target_roles = claim.target_roles[:1]
    elif claim.role == Role.Roles.Seer:
      if (night_action_type == 1):
        # Seer peek middle case, reinterpret the bits
        (_, _, claim.targets[0]) = self.decode(t0bits, 0, ["left", "middle", "right", None])
        (_, _, claim.targets[1]) = self.decode(t1bits, 0, ["left", "middle", "right", None])
      else:
        claim.targets = claim.targets[:1]
        claim.target_roles = claim.targets[:1]
    elif claim.role == Role.Roles.Robber:
      if (night_action_type == 1):
        # Robber did not rob case
        claim.targets = []
        claim.target_roles = []
      else:
        claim.targets = claim.targets[:1]
        claim.target_roles = claim.targets[:1]
    elif claim.role == Role.Roles.Troublemaker:
      claim.target_roles = []
    elif claim.role == Role.Roles.Insomniac:
      claim.targets = []
      claim.target_roles = claim.target_roles[:1]
    elif claim.role == Role.Roles.Villager:
      claim.targets = []
      claim.target_roles = []
    # Remove None elements
    claim.targets = [t for t in claim.targets if t]
    claim.target_roles = [t for t in claim.target_roles if t]
    return (pos, claim)

  def encodeState(self, turnnum, normedPlayers):
    state = [0] * self.numInputs
    pos = 0
    # Inform bot what our role and night info is
    pos = self.encode(state, pos, normedPlayers[0].orig_role, self.supportedRoles)
    pos = self.encode(state, pos, normedPlayers[0].night_targets[0] if len(normedPlayers[0].night_targets)>=1 else None, self.normedNames)
    pos = self.encode(state, pos, normedPlayers[0].night_targets[1] if len(normedPlayers[0].night_targets)>=2 else None, self.normedNames)
    pos = self.encode(state, pos, normedPlayers[0].target_roles[0] if len(normedPlayers[0].target_roles)>=1 else None, self.supportedRoles)
    pos = self.encode(state, pos, normedPlayers[0].target_roles[1] if len(normedPlayers[0].target_roles)>=2 else None, self.supportedRoles)
    # What turn is it
    pos = self.encode(state, pos, turnnum, range(0,2+1))
    # What did everyone claim last turn, including myself
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
    assert pos == self.numInputs, (pos, self.numInputs)
    return state

  def decodeOutput(self, output):
    pos = 0
    (pos, claim) = self.decodeClaim(output, pos)
    votes = output[pos:pos+len(self.normedNames)-1]
    votes[0] = 0 # Do not vote for self
    pos += len(self.normedNames)
    for i,v in enumerate(votes):
      if v > 0.5: claim.votes.append(self.normedNames[i])
    assert pos == self.numOutputs
    return (claim, votes)

  def encodeOutput(self, claim, votes):
    output [Null]
    return output

  def getAction(self):
    """ get suggested action, return them if they are legal, otherwise choose randomly. """
    if not self.normedPlayers:
      self.gameStart()
    player = self.modbot.find_player(self.name)
    if self.modbot.gamestate != self.modbot.GAMESTATE_RUNNING:
      raise
    if self.modbot.time != "day":
      self.fb.getAction() # Don't use NN for this part
      return

    state = self.encodeState(self.modbot.turnnum, self.normedPlayers)
    self.module.reset()
    output = self.module.activate(state)
    (claim, votes) = self.decodeState(state)

    if (self.modbot.turnnum < 2):
      self.modbot.claim(self.fb.e, claim)
    else:
      vote = drawGibbs(votes)
      self.modbot.cmd_vote([self.normedNames[vote]], self.fb.e)
      #print ("vote", votes, vote, self.normedNames[vote])
