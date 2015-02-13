from wolfmodbot import WolfModBot, Role
from fakeirc import Event
from simplewolfplayer import SimpleWolfPlayer
from nnwolfbot import NnWolfBot
from pybrain.tools.shortcuts import buildNetwork
from pybrain import SigmoidLayer
from pybrain.structure.evolvables.cheaplycopiable import CheaplyCopiable
from pybrain.optimization import ES
from pybrain.optimization import HillClimber

class Train():
  def __init__(self):
    self.modbot = WolfModBot('chname', 'bot_nickname', 'bot_nickpass', 'server', 'port', False)
    self.players = []
    self.numGames = 100
    self.maxEvaluations = 100

  def e(self, p):
    if type(p) is int:
      return Event("privmsg", self.players[p].name, None, None)
    if type(p) is str:
      return Event("privmsg", p, None, None)
    else:
      return Event("privmsg", p.name, None, None)

  def test_1(self):
    self.players = []
    self.players.append(SimpleWolfPlayer("KillerDucky", self.modbot))
    self.players.append(SimpleWolfPlayer("Alice", self.modbot))
    self.players.append(SimpleWolfPlayer("Bob", self.modbot))
    self.players.append(SimpleWolfPlayer("Charlie", self.modbot))
    self.players.append(SimpleWolfPlayer("Doug", self.modbot))
    self.modbot.default_roles = [
      Role.Roles.Werewolf,     # 0 KD
      Role.Roles.Seer,         # 1 Alice
      Role.Roles.Robber,       # 2 Bob
      Role.Roles.Troublemaker, # 3 Charlie
      Role.Roles.Insomniac     # 4 Doug
    ]
    self.modbot.cmd_start([], self.e(0))
    self.modbot.no_shuffle = True
    for p in self.players[1:]:
      self.modbot.cmd_join([], self.e(p))
    self.modbot.cmd_start([], self.e(0))
    self.modbot.cmd_see(["left"],         self.e(0))
    self.modbot.cmd_see(["KillerDucky"],  self.e(1))
    self.modbot.cmd_rob(["KillerDucky"],  self.e(2))
    self.modbot.cmd_swap(["KillerDucky", "Bob"], self.e(3))
    self.modbot.cmd_vote(["KillerDucky"], self.e(1))
    self.modbot.cmd_vote(["KillerDucky"], self.e(2))
    self.modbot.cmd_vote(["KillerDucky"], self.e(3))
    self.modbot.cmd_vote(["KillerDucky"], self.e(4))
    self.modbot.cmd_vote(["Alice"],       self.e(0))
    self.modbot.cmd_status([], self.e(0))

  def oneAiGame(self, net):
    self.players.append(NnWolfBot(net, "nbot", self.modbot))
    self.players.append(SimpleWolfPlayer("Andy", self.modbot))
    self.players.append(SimpleWolfPlayer("Bobi", self.modbot))
    self.players.append(SimpleWolfPlayer("Chad", self.modbot))
    self.players.append(SimpleWolfPlayer("Doug", self.modbot))
    self.modbot.default_roles = [
      Role.Roles.Werewolf,
      Role.Roles.Werewolf,
      Role.Roles.Seer,
      Role.Roles.Robber,
      Role.Roles.Insomniac,
      Role.Roles.Villager,
      Role.Roles.Villager,
      Role.Roles.Villager
    ]
    self.modbot.cmd_start([], self.e(0))
    #self.modbot.no_shuffle = True
    for p in self.players[1:]:
      self.modbot.cmd_join([], self.e(p))
    while self.modbot.gamestate == self.modbot.GAMESTATE_RUNNING:
      for p in self.players:
        p.getAction()
        if self.modbot.gamestate != self.modbot.GAMESTATE_RUNNING:
          break
    bot = self.modbot.find_player("nbot")
    if (bot.curr_role == Role.Roles.Werewolf):
      correctVote = bot.voted_for.curr_role != Role.Roles.Werewolf
    else:
      correctVote = bot.voted_for.curr_role == Role.Roles.Werewolf
    correctVoteWeight = 0.5
    winWeight = 0.5
    reward = 0.
    if correctVote: reward += correctVoteWeight
    if bot.win: reward += winWeight
    self.modbot._reset_gamedata()
    return reward

  def avgOverGames(self, net, num):
    reward = 0.
    for _ in range(num):
      reward += self.oneAiGame(net)
    reward /= num
    return reward

  def f(self, net):
    print "f", net
    return self.avgOverGames(net, self.numGames)

  def trainAi(self):
    net = buildNetwork(NnWolfBot.numInputs, NnWolfBot.numOutputs, outclass = SigmoidLayer)
    net = CheaplyCopiable(net)
    print (net.name, 'has', net.paramdim, 'trainable parameters.')

    learner = ES(self.f, net, mu = 5, lambada = 5,
                 verbose = True, evaluatorIsNoisy = True,
                 maxEvaluations = self.maxEvaluations)
    #learner = HillClimber(
    #              task, net,
    #              evaluatorIsNoisy = True,
    #              maxEvaluations = maxEvaluations)

    newnet, f = learner.learn()

    print self.f(net)
    print self.f(newnet)

    for i in range(10):
      reward = self.oneAiGame(newnet)
      print reward


train = Train()
#train.test_1()
train.trainAi()
