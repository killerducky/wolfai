from pybrain.utilities import drawGibbs
import random
from wolfmodbot import Role
from fakeirc import Event

class SimpleWolfPlayer():
  def __init__(self, name, modbot):
    self.name = name
    self.modbot = modbot
    self.e = Event("privmsg", self.name, None, None)
  def getOtherPlayers(self):
    return [p for p in self.modbot.live_players if p.nickname != self.name]
  def getAction(self):
    player = self.modbot.find_player(self.name)
    print "getAction for name=%s role=%s" % (self.name, player.orig_role)
    if self.modbot.gamestate != self.modbot.GAMESTATE_RUNNING:
      raise
    if self.modbot.time == "day":
      self.modbot.cmd_vote([random.choice(self.getOtherPlayers()).nickname], self.e)
    else:
      if not player.night_done:
        if player.orig_role == Role.Roles.Werewolf:
          self.modbot.cmd_see([random.choice(["left", "middle", "right"])], self.e)
        if player.orig_role == Role.Roles.Seer:
          self.modbot.cmd_see([random.choice(self.getOtherPlayers()).nickname], self.e)
        if player.orig_role == Role.Roles.Robber:
          self.modbot.cmd_rob([random.choice(self.getOtherPlayers()).nickname], self.e)
        if player.orig_role == Role.Roles.Troublemaker:
          self.modbot.cmd_swap([p.nickname for p in random.sample(self.getOtherPlayers(), 2)], self.e)
