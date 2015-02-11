#from pybrain.rl.environments.twoplayergames.twoplayergame import TwoPlayerGame
from pybrain.utilities import Named


class Tournament(Named):
    """ the tournament class is a specific kind of experiment, that takes a pool of agents
    and has them compete against each other in a WolfGame. TODO: Generalize to n-player game """

    def __init__(self, env, agents):
        self.env = env
        self.agents = agents
        for a in agents:
            a.game = self.env
        self.reset()

    def reset(self):
        self.results = []
        self.rounds = 0
        self.numGames = 0

    def _oneGame(self, agents):
        """ play one game between two agents p1 and p2."""
        self.numGames += 1
        self.env.reset()
        players = tuple(agents)
        i = 0
        for i in range(len(players)):
          players[i].pnum = i
        while not self.env.gameOver():
            p = players[i]
            act = p.getAction()
            self.env.performAction(i, act)
            i = (i + 1) % len(players)

        winners = self.env.getWinner()
        self.results.append(winners)

    def organize(self, repeat=1):
        """ have all agents play all others in all orders, and repeat. """
        for dummy in range(repeat):
            self.rounds += 1
            #for p1, p2 in self._produceAllPairs():
                #self._oneGame(p1, p2)
            self._oneGame(self.agents)
        return self.results

    def __str__(self):
        s = 'Tournament results (' + str(self.rounds) + ' rounds, ' + str(self.numGames) + ' games):\n'
        for i in range(len(self.agents)):
          wins = len([x for x in self.results if x[i]])
          losses = len([x for x in self.results if not x[i]])
          s += ' ' * 3 + str(i) + ' won ' + str(wins) + ' times and lost ' + str(losses) + ' times \n'
        return s
