from __future__ import print_function

#!/usr/bin/env python

#from pybrain.rl.environments.twoplayergames import CaptureGameTask
from pybrain.structure.evolvables.cheaplycopiable import CheaplyCopiable
from pybrain.optimization import ES
from pybrain.utilities import storeCallResults
#from pybrain.rl.environments.twoplayergames.capturegameplayers.killing import KillingPlayer

from wolfgame import WolfGame
from playwolftask import PlayWolfTask
from simplewolfplayer import SimpleWolfPlayer

# task settings
#size = 5
maxEvaluations = 50
numPlayers = 5
numInputs  = 4+numPlayers*2  # self.ww, self.v, turn1, turn2, numPlayers*(p#.claim.ww, p#.claimv)
numOutputs = 2+1*(numPlayers-1)  # claim.ww, claim.v, (numPlayers-1)*(p#.vote)
opponents = []
for dummy in range(numPlayers-1):
  opponents.append(SimpleWolfPlayer)
task = PlayWolfTask(numPlayers, opponents)

# keep track of evaluations for plotting
res = storeCallResults(task)

# simple network
from pybrain.tools.shortcuts import buildNetwork
from pybrain import SigmoidLayer
#net = buildNetwork(task.outdim, task.indim, outclass = SigmoidLayer)
#net = buildNetwork(numInputs, numInputs, numOutputs)
net = buildNetwork(numInputs, 1, numOutputs)

net = CheaplyCopiable(net)
print(net.name, 'has', net.paramdim, 'trainable parameters.')

learner = ES(task, net, mu = 5, lambada = 5,
             verbose = True, evaluatorIsNoisy = True,
             maxEvaluations = maxEvaluations)
newnet, f = learner.learn()

# plot the progression
from pylab import plot, show
plot(res)
#show()
