# Modeled after /home/aolsen/workspace/pybrain/pybrain/rl/environments/twoplayergames/tasks/capturetask.py

from pybrain.rl.environments.episodic import EpisodicTask
from inspect import isclass
from pybrain.utilities import  Named
#from pybrain.rl.environments.twoplayergames.capturegameplayers import RandomCapturePlayer, ModuleDecidingPlayer
from wolfmoduledecision import WolfModuleDecidingPlayer
#from pybrain.rl.environments.twoplayergames.capturegameplayers.captureplayer import CapturePlayer
from wolfgame import WolfGame
from pybrain.structure.modules.module import Module
import random, traceback, sys


class PlayWolfTask(EpisodicTask, Named):
    """ The task of winning the maximal number of wolf games against fixed opponents. """

    averageOverGames = 100 # average over some games for evaluations, averageOverGames
    noisy = True

    def __init__(self, numPlayers, opponents, **args):
        EpisodicTask.__init__(self, WolfGame(numPlayers, ["Werewolf", "Villager", "Villager", "Villager", "Villager"]))
        self.setArgs(**args)
        self.opponents = []
        self.verbose = False
        for i in range(len(opponents)):
          self.opponents.insert(i, opponents[i](self.env))
          self.opponents[i].pnum = i+1
        self.reset()

    def reset(self):
        EpisodicTask.reset(self)

    def isFinished(self):
        res = self.env.gameOver()
        return res

    def getReward(self):
        """ Final positive reward for winner, negative for loser. """
        reward = 0.
        winWeight = 1.0
        truthWeight = 0.0
        if self.isFinished():
            if self.env.getWinner()[0]:
              reward += winWeight
            if self.env.roles[0] == self.env.claim[0]:
              reward += truthWeight
            if (self.verbose):
              print ("reward", reward, str(self.env.stateStr()))
              #print traceback.print_stack(file=sys.stdout)
        return reward

    def performAction(self, action):
        EpisodicTask.performAction(self, action)
        for opp in self.opponents:
            action = opp.getAction()
            EpisodicTask.performAction(self, action)

    def f(self, x):
        """ If a module is given, wrap it into a ModuleDecidingAgent before evaluating it.
        Also, if applicable, average the result over multiple games. """
        if isinstance(x, Module):
            agent = WolfModuleDecidingPlayer(x, self.env, greedySelection = True)
        elif isinstance(x, SimpleWolfPlayer):
            agent = x
        else:
            raise NotImplementedError('Missing implementation for '+x.__class__.__name__+' evaluation')
        res = 0
        agent.game = self.env
        agent.pnum = 0
        for _ in range(self.averageOverGames):
            x = EpisodicTask.f(self, agent)
            res += x
        res /= float(self.averageOverGames)
        #print "averageOvergames", res
        return res



