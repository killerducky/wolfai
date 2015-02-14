from wolfmodbot import WolfModBot, Role, Player, Claim
from fakeirc import Event
from simplewolfplayer import SimpleWolfPlayer
from nnwolfbot import NnWolfBot
from pybrain.tools.shortcuts import buildNetwork
from pybrain import SigmoidLayer
from pybrain.structure.evolvables.cheaplycopiable import CheaplyCopiable
from pybrain.optimization import ES
from pybrain.optimization import HillClimber

class WolfSupervisor():
  def __init__(self):
    self.net = buildNetwork(NnWolfBot.numInputs, NnWolfBot.numInputs/2, NnWolfBot.numOutputs, outclass = SigmoidLayer)
    self.net = CheaplyCopiable(self.net)
    print (self.net.name, 'has', self.net.paramdim, 'trainable parameters.')
    modbot = WolfModBot('chname', 'bot_nickname', 'bot_nickpass', 'server', 'port', False)
    nnwolfbot = NnWolfBot(self.net, "nbot", modbot)

    self.turnnum = 0
    self.players = []

    p = Player("nbot")
    p.orig_role = Role.Roles.Seer
    p.night_targets = ["Andy"]
    p.target_roles  = [Role.Roles.Werewolf]
    self.players.append(p)

    p = Player("Andy")
    p.orig_role = Role.Roles.Werewolf
    p.claim = Claim()
    self.players.append(p)

    Player("Bobi")
    p.orig_role = Role.Roles.Villager
    p.claim = Claim()
    self.players.append(p)

    Player("Chad")
    p.orig_role = Role.Roles.Villager
    p.claim = Claim()
    self.players.append(p)

    Player("Doug")
    p.orig_role = Role.Roles.Villager
    p.claim = Claim()
    self.players.append(p)

    nnwolfbot.normedPlayers = self.players
    nnwolfbot.normedNames = [p.nickname for p in nnwolfbot.normedPlayers]


    state = nnwolfbot.encodeState(self.turnnum, self.players)
    print ("state=", state)
    self.net.reset()
    output = self.net.activate(state)
    print ("output=", output)
    (claim, votes) = nnwolfbot.decodeOutput(state)
    print ("claim=", str(claim))
    print ("votes=", votes)

#p.Claim(Role.Roles.Seer, [0], [Role.Roles.Werewolf], [])  # TODO: Need separate input for actual received Night info


wolfSupervisor = WolfSupervisor()

