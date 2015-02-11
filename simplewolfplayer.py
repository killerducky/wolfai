from pybrain.rl.agents.agent import Agent
from pybrain.utilities import drawGibbs



class SimpleWolfPlayer(Agent):
  def __init__(self, game, **args):
    self.game = game
    self.pnum = None
    self.setArgs(**args)
  def getAction(self):
    if (self.game.turnnum == 0):
      #print ("simple returning", self.pnum, self.game.roles[self.pnum])
      return [self.pnum, self.game.roles[self.pnum]]
    elif (self.game.turnnum == 1):
      for i in range(self.game.numPlayers):
        if self.game.roles[i] == "Werewolf":
          return [self.pnum, i] # Vote for whoever is dumb enough to say they are werewolf
      return 0  # If no wolves just vote 0, sorry player 0!
    else:
      raise Exception
