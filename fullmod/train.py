from wolfmodbot import WolfModBot, Role
from fakeirc import Event
from simplewolfplayer import SimpleWolfPlayer

class Train():
  def __init__(self):
    self.modbot = WolfModBot('chname', 'bot_nickname', 'bot_nickpass', 'server', 'port', False)
    self.players = []
    self.players.append(SimpleWolfPlayer("KillerDucky", self.modbot))
    self.players.append(SimpleWolfPlayer("Alice", self.modbot))
    self.players.append(SimpleWolfPlayer("Bob", self.modbot))
    self.players.append(SimpleWolfPlayer("Charlie", self.modbot))
    self.players.append(SimpleWolfPlayer("Doug", self.modbot))

  def e(self, p):
    if type(p) is int:
      return Event("privmsg", self.players[p].name, None, None)
    if type(p) is str:
      return Event("privmsg", p, None, None)
    else:
      return Event("privmsg", p.name, None, None)

  def test_1(self):
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

  def simpleAiTest(self):
    self.modbot.default_roles = [
      Role.Roles.Werewolf,     # 0 KD
      Role.Roles.Seer,         # 1 Alice
      Role.Roles.Robber,       # 2 Bob
      Role.Roles.Troublemaker, # 3 Charlie
      Role.Roles.Insomniac     # 4 Doug
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


train = Train()
#train.test_1()
train.simpleAiTest()
