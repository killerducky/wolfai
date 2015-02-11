import random
from pybrain.utilities import abstractMethod
from pybrain.rl.environments import Environment

class WolfGame(Environment):
  def __init__(self, numPlayers, roles):
    self.numPlayers = numPlayers
    self.roles = roles
    self.reset()

  def reset(self):
    #print "WolfGame reset"
    self.done = False
    self.winner = [None]*self.numPlayers
    self.votefor = [None]*self.numPlayers
    self.votes_received = [0]*self.numPlayers
    self.turnnum = 0
    self.claim = [None]*self.numPlayers
    random.shuffle(self.roles)
    
  def gameOver(self):
    return self.done

  def getSensors(self):
    # Well the players are just looking directly at environment things...
    return None
  
  def performAction(self, action):
    self.doMove(action[0], action[1])

  def doMove(self, pnum, action):
    if (self.turnnum == 0):
      self.claim[pnum] = action
      if not None in self.claim:
        self.turnnum += 1
    elif (self.turnnum == 1):
      self.votefor[pnum] = action
      if not None in self.votefor:
        most_votes = 0
        most_voted = None
        at_least_one_wolf_died = False
        for i in range(self.numPlayers):
          self.votes_received[self.votefor[i]] += 1
          if (self.votes_received[self.votefor[i]] > most_votes):
            most_votes = self.votes_received[self.votefor[i]]
            most_voted = self.votefor[i]
        if most_votes > 1:
          for i in range(self.numPlayers):
            if most_votes > 1 and self.votes_received[i] == most_votes and self.roles[i] == "Werewolf":
              at_least_one_wolf_died = True
          for i in range(self.numPlayers):
            if self.roles[i] == "Werewolf": self.winner[i] = not at_least_one_wolf_died
            else:                           self.winner[i] = at_least_one_wolf_died
        self.done = True
    else:
      raise Exception
    #if self.done: print stateStr

  def stateStr(self):
      s = "state turnnum=%s votefor=%s winner=%s" %(self.turnnum, self.votefor, [(0,1)[x] for x in self.winner])
      s += "\nroles=" + str([("WW","VV")[x=="Villager"] for x in self.roles])
      s += "\nclaims=" + str(self.claim)
      return s

  def getWinner(self):
    return self.winner
