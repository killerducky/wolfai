from __future__ import print_function

#!/usr/bin/env python

#from pybrain.rl.environments.twoplayergames import CaptureGame
#from pybrain.rl.environments.twoplayergames.capturegameplayers import RandomCapturePlayer, KillingPlayer, ModuleDecidingPlayer
#from pybrain.rl.environments.twoplayergames.capturegameplayers.clientwrapper import ClientCapturePlayer
from wolfgame import WolfGame
from simplewolfplayer import SimpleWolfPlayer
from tournament import Tournament
from pybrain.tools.shortcuts import buildNetwork
from pybrain import SigmoidLayer

#game = WolfGame(5, ["Werewolf", "Werewolf", "Seer", "Robber", "Troublemaker", "Insomniac", "Villager", "Villager"])
game = WolfGame(5, ["Werewolf", "Werewolf", "Seer", "Villager", "Villager"])

# the network's outputs are probabilities of choosing the action, thus a sigmoid output layer
#net = buildNetwork(game.outdim, game.indim, outclass = SigmoidLayer)
#netAgent = ModuleDecidingPlayer(net, game, name = 'net')

# same network, but greedy decisions:
#netAgentGreedy = ModuleDecidingPlayer(net, game, name = 'greedy', greedySelection = True)

agents = []
for dummy in range(5):
  agents.append(SimpleWolfPlayer(game))

print()
print('Starting tournament...')
tourn = Tournament(game, agents)
tourn.organize(5)
print(tourn)



