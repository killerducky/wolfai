import random
from pybrain.utilities import abstractMethod
from pybrain.rl.environments import Environment

class WolfGame(Environment):
  def __init__(self, numplayers, roles):
    self.numplayers = numplayers
    self.roles = roles
    self.reset()

  def reset(self):
    self.done = False
    self.winner = [None]*self.numplayers
    self.votefor = []
    self.votes_received = [0]*self.numplayers
    self.turnnum = 0
    self.claim = []
    random.shuffle(self.roles)
    
  def gameOver(self):
    return self.done
  
  def performAction(self, pnum, action):
    self.doMove(pnum, action)

  def doMove(self, pnum, action):
    if (self.turnnum == 0):
      self.claim.insert(pnum, action)
      if len(self.claim) == self.numplayers:
        self.turnnum += 1
    elif (self.turnnum == 1):
      self.votefor.insert(pnum, action)
      if len(self.votefor) == self.numplayers:
        most_votes = 0
        most_voted = None
        at_least_one_wolf_died = False
        for i in range(self.numplayers):
          self.votes_received[self.votefor[i]] += 1
          if (self.votes_received[self.votefor[i]] > most_votes):
            most_votes = self.votes_received[self.votefor[i]]
            most_voted = self.votefor[i]
        if most_votes > 1:
          for i in range(self.numplayers):
            if most_votes > 1 and self.votes_received[i] == most_votes and self.roles[i] == "Werewolf":
              at_least_one_wolf_died = True
          for i in range(self.numplayers):
            if self.roles[i] == "Werewolf": self.winner[i] = not at_least_one_wolf_died
            else:                           self.winner[i] = at_least_one_wolf_died
        self.done = True
    else:
      raise Exception
    if self.done:
      print "state", self.turnnum, self.votefor, self.claim, self.winner

  def getWinner(self):
    return self.winner
