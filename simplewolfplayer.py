from pybrain.rl.agents.agent import Agent
from pybrain.utilities import drawGibbs
import random



class SimpleWolfPlayer(Agent):
  def __init__(self, game, **args):
    self.game = game
    self.pnum = None
    self.setArgs(**args)
  def getAction(self):
    if (self.game.turnnum == 0):
      if self.game.roles[self.pnum] == "Werewolf":
        if random.random() < 0.95:
          return [self.pnum, "Werewolf"]
        else:
          return [self.pnum, "Villager"]
      return [self.pnum, self.game.roles[self.pnum]]
    elif (self.game.turnnum == 1):
      for i in range(self.game.numPlayers):
        if self.game.claim[i] == "Werewolf":
          if self.pnum >=1 and self.pnum <=2:
            return [self.pnum, i] # Two players vote for whoever is dumb enough to say they are werewolf
      return [self.pnum, (self.pnum-1)%self.game.numPlayers]  # Circle vote
    else:
      raise Exception
