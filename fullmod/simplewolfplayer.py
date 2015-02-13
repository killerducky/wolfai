from pybrain.utilities import drawGibbs
import random
from wolfmodbot import Role, Claim
from fakeirc import Event

class SimpleWolfPlayer():
  def __init__(self, name, modbot):
    self.name = name
    self.modbot = modbot
    self.e = Event("privmsg", self.name, None, None)
  def getOtherPlayers(self):
    return [p for p in self.modbot.live_players if p.nickname != self.name]
  def getVoteCandidates(self, player):
    voteCandidates = self.getOtherPlayers()
    # If WW, don't vote for your teammate
    if player.orig_role == Role.Roles.Werewolf:
      voteCandidates = [p for p in voteCandidates if p.orig_role != Role.Roles.Werewolf]
    # If Seer sees WW, vote for him
    if player.orig_role == Role.Roles.Seer and player.night_targets[0].orig_role == Role.Roles.Werewolf:
      voteCandidates = [player.night_targets[0]]
    return voteCandidates
  def getAction(self):
    player = self.modbot.find_player(self.name)
    if self.modbot.gamestate != self.modbot.GAMESTATE_RUNNING:
      raise
    if self.modbot.time == "day":
      if (self.modbot.turnnum < 2):
        if player.orig_role == Role.Roles.Werewolf:
          self.modbot.claim(self.e, Claim(Role.Roles.Villager, [], [], self.getOtherPlayers()))
        else:
          self.modbot.claim(self.e, Claim(player.orig_role, player.night_targets, [t.orig_role.name for t in player.night_targets], self.getVoteCandidates(player)))
        if (self.modbot.turnnum > 0):
          self.votes = [p.nickname for p in self.getVoteCandidates(player)]
      else:
        self.modbot.cmd_vote([random.choice(self.getVoteCandidates(player)).nickname], self.e)
    else:
      if not player.night_done:
        if player.orig_role == Role.Roles.Werewolf:
          self.modbot.cmd_see([random.choice(["left", "middle", "right"])], self.e)
        elif player.orig_role == Role.Roles.Seer:
          self.modbot.cmd_see([random.choice(self.getOtherPlayers()).nickname], self.e)
        elif player.orig_role == Role.Roles.Robber:
          self.modbot.cmd_rob([random.choice(self.getOtherPlayers()).nickname], self.e)
        elif player.orig_role == Role.Roles.Troublemaker:
          self.modbot.cmd_swap([p.nickname for p in random.sample(self.getOtherPlayers(), 2)], self.e)
