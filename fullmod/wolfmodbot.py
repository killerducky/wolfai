#!/usr/bin/env python
#
# Bot to moderate a game of "Werewolf".
#

""" A bot to moderate a game of "Werewolf".

The main commands are:
    start  -- start a new werewolf game.
    end    -- quit the current werewolf game (you must have started it)
    status -- print information about state of game-in-progress.

Role specific commands:
    Werewolf     -- see plus center location (left, middle, or right)
    Seer         -- see name        (or "see" plus two of "left", "middle", "right")
    Robber       -- rob name        (or "rob -" to decline robbing)
    Troublemaker -- swap name name  (or "swap -" to decline swapping)
    Drunk        -- swap left|middle|right

(Somewhat) Tested roles:
  Werewolf
  Seer
  Robber
  Troublemaker
  Insomniac
  Villager

Need to add:
  Mason
  Drunk
  Tanner
  Hunter
  Minion
  Doppelganger
"""

import sys, string, random, time
#from ircbot import SingleServerIRCBot
#import irclib
#from irclib import nm_to_n, nm_to_h, irc_lower, parse_channel_modes, Event
#from botcommon import OutputManager
from fakeirc import SingleServerIRCBot, OutputManager, Event, nm_to_n
from enum import Enum

#---------------------------------------------------------------------

minUsers=2
maxUsers=5
defaultPort=6667

#svn_url = \
#"$URL$"
#svn_url = svn_url[svn_url.find(' ')+1:svn_url.rfind('/')+1]

REAL_IRC = False

if REAL_IRC:
  IRC_BOLD = "\x02"
else:
  IRC_BOLD = ""

class StringMatch():
  @staticmethod
  def match(str, list):
    def lower(str): return str.lower()
    def nop(str): return str
    for f in (nop, lower):
      partial_matches = []
      tmp_str = f(str)
      for i in list:
        tmp_i = f(i)
        if tmp_i==tmp_str:
          return [i]
        if tmp_i.startswith(tmp_str):
          partial_matches.append(i)
      if len(partial_matches)>0:
        return partial_matches
    return partial_matches

  @staticmethod
  def min_chars(list):
    list.sort()
    prev_matching_chars = 0
    for k1,v1 in enumerate(list):
      next_matching_chars = 0
      if len(list)>k1+1:
        v2 = list[k1+1]
        while (len(v1)>next_matching_chars and len(v2)>next_matching_chars and v1[next_matching_chars] == v2[next_matching_chars]):
          next_matching_chars +=1
      print max(prev_matching_chars, next_matching_chars), prev_matching_chars, next_matching_chars, v1
      prev_matching_chars = next_matching_chars

  @staticmethod
  def test():
    list = ["abcd", "abc", "xyz", "xyz22", "34322", "dfdfasf"]
    min_chars(list)
    print match("abc", list)
    print match("xyz2", list)
    print match("a", list)
    print match("", list)
    print match("y", list)

    print match("ABC", list)
    print match("XYZ2", list)
    print match("A", list)
    print match("Y", list)


class Player():
  def __init__(self, nickname):
    self.nickname       = nickname
    self.orig_role      = None
    self.curr_role      = None
    self.night_targets  = []
    self.night_done     = False
    self.voted_for      = None
    self.received_votes = 0
    self.win            = False
    self.claim          = Claim()
    self.claim_done     = False
  def __str__(self):
    return "%s" % self.nickname
  def verbose_str(self):
    s = "%s is a %s, and %s the game." % (self.nickname, self.curr_role.name, ("won" if self.win else "lost"))
    if self.curr_role != self.orig_role:
      s += " Was originally a %s." % (self.orig_role.name)
    if self.orig_role == Role.Roles.Werewolf:
      if len(self.night_targets) == 1: # Lone wolf peek
        s += " Saw unused card %s was %s." % (self.night_targets[0])
    if self.orig_role == Role.Roles.Seer:
      # TODO: Should probably log night actions for when it becomes more complicated
      for target in self.night_targets:
        s += " Saw %s was a %s." % (self.night_targets[0].nickname, self.night_targets[0].orig_role.name)
    if self.orig_role == Role.Roles.Robber:
      if len(self.night_targets) == 0:
        s += " Did not steal."
      else:
        s += " Stole from %s." % (self.night_targets[0].nickname)
    if self.orig_role == Role.Roles.Troublemaker:
      if len(self.night_targets) == 0:
        s += " Did not swap."
      else:
        s += " Swapped %s." % (" and ".join(str(p) for p in self.night_targets))
    if self.voted_for:
      s += " Voted for %s." % (self.voted_for.nickname)
    s += " Received %d votes." % (self.received_votes)
    return s

class Claim():
  def __init__(self, role=None, targets=[], target_roles=[], votes=[]):
    self.role = role
    self.targets = targets
    self.target_roles = target_roles
    self.votes = votes
  def __str__(self):
    s = "myrole=%s" % self.role
    for t in self.targets:
      s += " target=%s" % t
    for r in self.target_roles:
      s += " target_role=%s" % r
    if len(self.votes):
      s += " will vote for"
    for v in self.votes:
      s += " %s" % v
    return s

class Role():
  Roles = Enum("Roles", "Doppelganger Werewolf Minion Mason Seer Robber Troublemaker Drunk Insomniac Tanner Hunter Villager")
  def __init__(self, role):
    self.role = role
  def __str__(self):
    return str(self.role.name)

class WolfModBot(SingleServerIRCBot):
  GAMESTATE_NONE, GAMESTATE_STARTING, GAMESTATE_RUNNING, GAMESTATE_DONE = range(4)
  Center_Locations = Enum("Center", "left middle right")

  def __init__(self, channel, nickname, nickpass, server, port=defaultPort, debug=False):
    SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
    self.channel = channel
    # self.nickname is the nickname we _want_. The nickname we actually
    # have at any particular time is c.get_nickname().
    self.nickname = nickname
    self.nickpass = nickpass
    self.debug = debug
    self.moderation = True
    self._reset_gamedata()
    self.queue = OutputManager(self.connection)
    self.queue.start()
    self.default_roles = [
      Role.Roles.Werewolf,
      Role.Roles.Werewolf,
      Role.Roles.Seer,
      Role.Roles.Robber,
      Role.Roles.Insomniac
    ]
    try:
      self.start()
    except KeyboardInterrupt:
      self.connection.quit("Ctrl-C at console")
      print "Quit IRC."
    except Exception, e:
      self.connection.quit("%s: %s" % (e.__class__.__name__, e.args))
      raise


  _uninteresting_events = {
    'all_raw_messages': None,
    'yourhost': None,
    'created': None,
    'myinfo': None,
    'featurelist': None,
    'luserclient': None,
    'luserop': None,
    'luserchannels': None,
    'luserme': None,
    'n_local': None,
    'n_global': None,
    'luserconns': None,
    'motdstart': None,
    'motd': None,
    'endofmotd': None,
    'topic': None,
    'topicinfo': None,
    'ping': None,
    }
  def _dispatcher(self, c, e):
    if self.debug:
      eventtype = e.eventtype()
      if eventtype not in self._uninteresting_events:
        source = e.source()
        if source is not None:
          source = nm_to_n(source)
        else:
          source = ''
        print "E: %s (%s->%s) %s" % (eventtype, source, e.target(), e.arguments())
    SingleServerIRCBot._dispatcher(self, c, e)

  def on_nicknameinuse(self, c, e):
    c.nick(c.get_nickname() + "_")

  def _renameUser(self, old, new):
    for player in (self.live_players):
      if player.nickname == old:
        player.nickname = new
        break

  def _removeUser(self, nick):
    self.say_public("%s left" % nick)
    # !! todo if user is gone, random vote for him?
    #if nick == self.game_starter:
    #  self.game_starter = None

  def on_join(self, c, e):
    nick = nm_to_n(e.source())
    if nick == c.get_nickname():
      chan = e.target()
      self.connection.mode(self.channel, '')

  def on_channelmodeis(self, c, e):
    c._handle_event(irclib.Event("mode", e.source(), e.arguments()[0], [e.arguments()[1]]))
    self.fix_modes()

  def on_mode(self, c, e):
    if e.target() == self.channel:
      try:
        if parse_channel_modes(e.arguments()[0]) == ['+','o',c.get_nickname()]:
          self.fix_modes()
      except IndexError:
        pass

  def on_quit(self, c, e):
    source = nm_to_n(e.source())
    self._removeUser(source)
    if source == self.nickname:
      # Our desired nick just quit - take the nick back
      c.nick(self.nickname)

  def on_nick(self, c, e):
    self._renameUser(nm_to_n(e.source()), e.target())

  def on_welcome(self, c, e):
    c.join(self.channel)
    if c.get_nickname() != self.nickname:
      # Reclaim our desired nickname
      c.privmsg('nickserv', 'ghost %s %s' % (self.nickname, self.nickpass))

  def fix_modes(self):
    chobj = self.channels[self.channel]
    is_moderated = chobj.is_moderated()
    should_be_moderated = (self.gamestate == self.GAMESTATE_RUNNING and self.moderation)
    #!!! don't bother with moderation/voicing
    #if is_moderated and not should_be_moderated:
    #  self.connection.mode(self.channel, '-m')
    #elif not is_moderated and should_be_moderated:
    #  self.connection.mode(self.channel, '+m')
    #
    #voice = []
    #devoice = []
    #for user in chobj.users():
    #  is_live = user in self.live_players
    #  is_voiced = chobj.is_voiced(user)
    #  if is_live and not is_voiced:
    #    voice.append(user)
    #  elif not is_live and is_voiced:
    #    devoice.append(user)
    #self.multimode('+v', voice)
    #self.multimode('-v', devoice)


  # Only used by the voice code
  def multimode(self, mode, nicks):
    max_batch = 4 # FIXME: Get this from features message
    assert len(mode) == 2
    assert mode[0] in ('-', '+')
    while nicks:
      batch_len = len(nicks)
      if batch_len > max_batch:
        batch_len = max_batch
      tokens = [mode[0] + (mode[1]*batch_len)]
      while batch_len:
        tokens.append(nicks.pop(0))
        batch_len -= 1
      self.connection.mode(self.channel, ' '.join(tokens))

  def on_privnotice(self, c, e):
    source = e.source()
    if source and irc_lower(nm_to_n(source)) == 'nickserv':
      if e.arguments()[0].find('IDENTIFY') >= 0:
        # Received request to identify
        if self.nickpass and self.nickname == c.get_nickname():
          self.queue.send('identify %s' % self.nickpass, 'nickserv')


  GAME_STARTER_TIMEOUT_MINS = 4
  def check_game_control(self, e):
    "Implement a timeout for game controller."
    if self.game_starter is None:
      return
    nick = nm_to_n(e.source())
    if self.game_starter == nick:
      self.game_starter_last_seen = time.time()
    else:
      if self.game_starter_last_seen < (
          time.time() - self.GAME_STARTER_TIMEOUT_MINS * 60):
        self.say_public("Game starter '%s' has been silent for %d minutes. "
            "Game control is now open to all." % (self.game_starter,
              self.GAME_STARTER_TIMEOUT_MINS))
        self.game_starter = None

  def on_privmsg(self, c, e):
    self.check_game_control(e)
    self.do_command(e, e.arguments()[0])

  def on_part(self, c, e):
    self._removeUser(nm_to_n(e.source()))

  def on_kick(self, c, e):
    self._removeUser(nm_to_n(e.arguments()[0]))

  def on_pubmsg(self, c, e):
    self.check_game_control(e)
    s = e.arguments()[0]
    a = string.split(s, ":", 1)
    if len(a) > 1 and irc_lower(a[0]) == irc_lower(c.get_nickname()):
      self.do_command(e, string.strip(a[1]))
    if s[0]=='!' and (len(s) > 1) and s[1]!='!':
      self.do_command(e, string.strip(s[1:]))

  def _reset_gamedata(self):
    self.gamestate = self.GAMESTATE_NONE
    self.time = "night"
    self.turnnum = 0                    # Formal phase number
    self.game_starter = None
    self.game_starter_last_seen = 0
    self.live_players = []
    self.roles_list = []
    self.unused_roles = []
    self.orig_werewolves = []
    self.example_game = False
    self.no_shuffle = False

  def find_player(self, nickname):
    "Find player by nickname. Return None if not found"
    # This is inefficient, should do it one step...
    matches = StringMatch.match(nickname, [p.nickname for p in self.live_players])
    if len(matches) != 1:
      return None  # TODO some way to tell user if they matched multiple names or none
    for p in self.live_players:
      if p.nickname == matches[0]:
        return p
    raise # Should never get here

  def say_public(self, text):
    "Print TEXT into public channel, for all to see."
    if self.debug: print "say_public %s" % (text)
    self.queue.send(IRC_BOLD+text, self.channel)


  def say_private(self, nick, text):
    "Send private message of TEXT to NICK."
    if self.debug: print "say_private %s %s" % (nick, text)
    self.queue.send(IRC_BOLD+text,nick)
    if self.example_game:
      self.say_public("Sent %s this message: %s" % (nick, text))


  def reply(self, e, text):
    "Send TEXT to public channel or as private msg, in reply to event E."
    if e.eventtype() == "pubmsg":
      self.say_public("%s: %s" % (nm_to_n(e.source()), text))
    else:
      self.say_private(nm_to_n(e.source()), text)


  def start_game(self, game_starter):
    "Initialize a werewolf game -- assign roles and notify all players."
    chname, chobj = self.channels.items()[0]

    if self.gamestate == self.GAMESTATE_RUNNING:
      self.say_public("A game started by %s is in progress; "
          "that person must end it." % self.game_starter)
      return

    if self.gamestate == self.GAMESTATE_NONE or self.gamestate == self.GAMESTATE_DONE:
      self._reset_gamedata()
      self.gamestate = self.GAMESTATE_STARTING
      self.game_starter = game_starter
      self.game_starter_last_seen = time.time()
      self.live_players.append(Player(game_starter))
      self.say_public("A new game has been started by %s; "
          "say '%s: join' to join the game."
          % (self.game_starter, self.connection.get_nickname()))
      self.say_public("%s: Say '%s: start' when everyone has joined."
          % (self.game_starter, self.connection.get_nickname()))
      self.fix_modes()
      return

    if self.gamestate == self.GAMESTATE_STARTING:
      if self.game_starter and game_starter and game_starter != self.game_starter:
        self.say_public("Game startup was begun by %s; "
            "that person must finish starting it." % self.game_starter)
        return
      self.game_starter = game_starter
      self.game_starter_last_seen = time.time()

      if len(self.live_players) < minUsers:
        self.say_public("Sorry, to start a game, there must be " + \
                        "at least active %d players."%(minUsers))
        self.say_public(("I count only %d active players right now: %s."
          % (len(self.live_players), self.player_list_to_str(self.live_players))))

      else:
        # !! TODO Better role picking
        self.roles_list = self.default_roles[:]
        while (len(self.roles_list) < len(self.live_players)+3):
          self.roles_list.append(Role.Roles.Villager)

        # Assign roles
        self.say_public("A new game has begun with %s" % self.player_list_to_str(self.live_players))
        self.say_public("The possible roles are: %s" % " ".join(r.name for r in self.roles_list))
        for p in self.live_players:
          self.say_private(p.nickname, "A new game has begun with %s" % self.player_list_to_str(self.live_players))
          self.say_private(p.nickname, "The possible roles are: %s" % " ".join(r.name for r in self.roles_list))

        self.unused_roles = self.roles_list[:]  # Copy the list
        if not self.no_shuffle:
           random.shuffle(self.unused_roles)
        for p in self.live_players:
          p.curr_role = p.orig_role = self.unused_roles.pop(0)
          if (p.curr_role == Role.Roles.Werewolf):
            self.orig_werewolves.append(p)

        for p in self.live_players:
          if (p.curr_role == Role.Roles.Werewolf):
            if (len(self.orig_werewolves)>1):
              other_werewolves = [ww for ww in self.orig_werewolves if p.nickname != ww.nickname]
              self.say_private(p.nickname, ("You and %s are Werewolves." % self.player_list_to_str(other_werewolves)))
              p.night_done = True
            else:
              # !! TODO: Allow lone wolf to pick his view
              self.say_private(p.nickname, ("You are the only Werewolf. PM 'see' plus one of <left|middle|right> to see one of the unused roles."))
          elif (p.curr_role == Role.Roles.Seer):
            self.say_private(p.nickname, ("You are the Seer. Send me a PM 'see <name>' to see that player's role."))
            self.say_private(p.nickname, ("Or you can look at two unused cards: 'see' plus two of <left|middle|right>."))
          elif (p.curr_role == Role.Roles.Robber):
            self.say_private(p.nickname, ("You are the Robber. Send me a PM 'rob <name>' to swap roles with that player."))
            self.say_private(p.nickname, ("Or you can choose not to rob anyone: 'rob -'"))
          elif (p.curr_role == Role.Roles.Troublemaker):
            self.say_private(p.nickname, ("You are the Troublemaker. Send me a PM 'swap <name> <name>' to swap those player's roles."))
            self.say_private(p.nickname, ("Or you can choose not to swap anyone: 'swap -'"))
          elif (p.curr_role == Role.Roles.Drunk):
            self.say_private(p.nickname, ("You are the Drunk. Send me a PM 'swap <left|middle|right>' to chose which unused card you want to swap with"))
          elif (p.curr_role == Role.Roles.Insomniac):
            self.say_private(p.nickname, ("You are the Insomniac. Later I will tell you if your role was changed by someone."))
          elif (p.curr_role == Role.Roles.Villager):
            self.say_private(p.nickname, ("You are a Villager."))
            p.night_done = True

        self.gamestate = self.GAMESTATE_RUNNING
        self.check_night_done()

        self.fix_modes()


  def end_game(self, game_ender):
    "End the game"

    if self.gamestate == self.GAMESTATE_NONE:
      self.say_public("No game is in progress.  Use 'start' to begin a game.")
    elif self.game_starter and game_ender and game_ender != self.game_starter:
      self.say_public(("Sorry, only the starter of the game (%s) may end it." % self.game_starter))
    else:
      if game_ender:
        self.say_public("%s ended the game early")
        if self.gamestate == self.GAMESTATE_RUNNING:
          self.reveal_all_identities()
      else:
        self.say_public("The votes are in.")
        victims = self.check_votes()
        num_werewolves_voted_for = len([p for p in victims if p.curr_role == Role.Roles.Werewolf])
        if len(victims)==0:
          self.say_public(("Everyone received exactly 1 vote, no one was killed"))
          if len(self.orig_werewolves)==0:
            # TODO: Tanner
            self.say_public(("There were no Werewolves, so everyone wins!"))
            for p in self.live_players:
              p.win = True
          else:
            self.say_public(("The Werewolves (%s) win!" % self.player_list_to_str(self.orig_werewolves)))
            for p in self.live_players:
              if p.curr_role == Role.Roles.Werewolf:
                p.win = True
        else:
          self.say_public(("The majority has voted to lynch %s." % self.player_list_to_str(victims)))
          if num_werewolves_voted_for > 0:
            self.say_public(("%s were Werewolves, so the Village (%s) wins!" % (
                self.player_list_to_str([ww for ww in self.live_players if ww.curr_role == Role.Roles.Werewolf]),
                self.player_list_to_str([ww for ww in self.live_players if ww.curr_role != Role.Roles.Werewolf]))))
            for p in self.live_players:
              if p.curr_role != Role.Roles.Werewolf:
                p.win = True
          else:
            self.say_public(("The Werewolves (%s) are alive and win!" % (
                self.player_list_to_str([ww for ww in self.live_players if ww.curr_role == Role.Roles.Werewolf]))))
            for p in self.live_players:
              if p.curr_role == Role.Roles.Werewolf:
                p.win = True
        self.reveal_all_identities()

      self.gamestate = self.GAMESTATE_DONE
      self.fix_modes()

  def reveal_all_identities(self):
    for p in self.live_players:
      self.say_public(p.verbose_str())
    self.say_public("Unused roles: %s" % " ".join(r.name for r in self.unused_roles))

  def check_night_done(self):
    "Check if nighttime is over."

    for p in self.live_players:
      if not p.night_done and (p.orig_role != Role.Roles.Insomniac):
        return False
    # Everyone except Insomniacs are done.

    # TODO: Doppleganger... ugh
    # Werewolves were done immediately
    # Robbing was done immediately

    # Do the troublemaker swap
    for p in self.live_players:
      if p.orig_role == Role.Roles.Troublemaker and p.night_targets:
        p.night_targets[0].curr_role, p.night_targets[1].curr_role = \
        p.night_targets[1].curr_role, p.night_targets[0].curr_role

    # TODO: Drunk

    # Tell Insomniac who they are
    for p in self.live_players:
      if p.orig_role == Role.Roles.Insomniac:
        if p.orig_role == p.curr_role:
          self.say_private(p.nickname, ("You are still the Insomniac"))
        else:
          self.say_private(p.nickname, ("During the night you became the %s" % p.curr_role))
        p.night_done = True
    self.time = "day"
    self.say_public("It is now day time.")


  def rob(self, e, who):
    "Allow a Robber to 'rob' somebody."

    player = self.find_player(nm_to_n(e.source()))
    target = self.find_player(who)
    if (player == None):
      self.reply(e, "You are not playing this game.")
    elif (player.orig_role != Role.Roles.Robber):
      self.reply(e, "You are not the Robber.")
    elif (player.night_done):
      self.reply(e, "You cannot do this action again.")
    elif (target == None):
      if who != "-":
        self.reply(e, "%s is not playing this game" % who)
      else:
        self.reply(e, "You have choosen not to Rob anyone")
        player.night_done = True
    else:
      player.night_targets.append(target)
      self.reply(e, "You Robbed %s's role. You are now the %s" % (target.nickname, target.curr_role.name))
      # Swap current roles
      player.curr_role, target.curr_role = target.curr_role, player.curr_role
      player.night_done = True
      self.check_night_done()

  def swap(self, e, who):
    player = self.find_player(nm_to_n(e.source()))
    if (player == None):
      self.replay(e, "You are not playing this game.")
    elif (player.orig_role != Role.Roles.Troublemaker):
      self.reply(e, "You are not the Troublemaker.")
    elif (player.night_done):
      self.reply(e, "You cannot do this action again.")
    elif len(who) == 1:
      if who == "-":
        self.reply(e, "You have choosen not to Swap anyone")
        player.night_done = True
        self.check_night_done()
      else:
        self.reply(e, "Invalid Rob command.")
    else:
      target = [self.find_player(who[0]), self.find_player(who[1])]
      if (target[0] == None):
        self.reply(e, "%s is not playing this game" % who[0])
      elif (target[1] == None):
        self.reply(e, "%s is not playing this game" % who[1])
      else:
        player.night_targets += target
        self.reply(e, "You swapped %s and %s's roles." % (who[0], who[1]))
        player.night_done = True
        self.check_night_done()

  def find_unused(self, who):
    tmp = [x.name for x in self.Center_Locations]
    for i, w in enumerate(who):
      w_complete = StringMatch.match(w, tmp)
      if len(w_complete)==1:
        who[i] = w_complete[0]
      else:
        who[i] = None

  def claim(self, e, claim):
    "Formal claim registration"
    player = self.find_player(nm_to_n(e.source()))
    player.claim = claim
    player.claim_done = True
    self.say_public("%s claims: %s" % (player.nickname, claim))
    if not False in [p.claim_done for p in self.live_players]:
      for p in self.live_players: p.claim_done = False
      self.turnnum += 1

  def see(self, e, who):
    "Allow a Seer to 'see' somebody."

    player = self.find_player(nm_to_n(e.source()))
    target = self.find_player(who[0])
    if (player == None):
      self.reply(e, "You are not playing this game.")
    elif (player.orig_role != Role.Roles.Seer and player.orig_role != Role.Roles.Werewolf):
      self.reply(e, "You are not the Seer.")
    elif (player.night_done):
      self.reply(e, "You have already had your vision.")
    elif (player.orig_role == Role.Roles.Seer):
      if len(who)==2:
        self.find_unused(who)
        if not who[0] or not who[1]:
          self.reply(e, "Invalid unused locations. Please pick left, middle, or right. e.g 'see left right'")
        else:
          self.reply(e, "%s=%s %s=%s" % (who[0], self.pick_unused_role(who[0]).name, who[1], self.pick_unused_role(who[1]).name))
          player.night_done = True
          self.check_night_done()
      else:
        if (target == None):
          self.reply(e, "%s is not playing this game" % who)
        else:
          player.night_targets.append(target)
          self.reply(e, "%s is the %s" % (target.nickname, target.curr_role.name))
          player.night_done = True
          self.check_night_done()
    # Lone Werewolf also uses the see command
    elif (len(self.orig_werewolves) != 1):
      self.reply(e, "Only a lone Werewolf can see a card in the middle")
    else:
      self.find_unused(who)
      if not who[0]:
        self.reply(e, "Invalid unused location. Please pick left, middle, or right. e.g 'see left'")
      else:
        self.reply(e, "%s=%s" % (who[0], self.pick_unused_role(who[0]).name))
        player.night_done = True
        self.check_night_done()

  def pick_unused_role(self, location_name):
    return self.unused_roles[self.Center_Locations[location_name].value-1]

  def check_votes(self):
    "Return list of players with the most votes. Return [] if everyone received exactly 1 vote"

    # Clear votes
    for p in self.live_players:
      p.received_votes = 0
    # Tally votes
    for p in self.live_players:
      p.voted_for.received_votes += 1

    # Find player with most votes
    most_votes = 0
    most_voted_players = []
    for p in self.live_players:
      if p.received_votes > most_votes:
        most_votes = p.received_votes
        most_voted_players = [p]
      elif p.received_votes == most_votes:
        most_voted_players.append(p)
    if most_votes == 1:
      return []
    else:
      return most_voted_players



  def match_name(self, nick):
    "TODO: For now skip the matching part"
    return nick
    """Match NICK to a username in users(), insensitively.  Return
    matching nick, or None if no match."""

    chname, chobj = self.channels.items()[0]
    users = chobj.users()
    users.remove(self._nickname)

    for user in users:
      if user.upper() == nick.upper():
        return user
    return None

  def player_list_to_str(self, player_list, join_str=" and "):
    return join_str.join(str(p) for p in player_list)

  def vote(self, e, voted_for_str):
    "Register a vote to lynch voted_for."

    voter     = self.find_player(nm_to_n(e.source()))
    voted_for = self.find_player(voted_for_str)
    # sanity checks
    if self.time != "day":
      self.reply(e, ("Sorry, voting only happens during the day."))
    elif voter == None:
      self.reply(e, ("You are not playing this game."))
    elif voted_for == None:
      self.reply(e, ("%s is not playing this game." % voted_for_str))
    elif voted_for == voter:
      self.reply(e, ("You can't vote for yourself."))

    else:
      voter.voted_for = voted_for
      all_voted = True
      for p in self.live_players:
        if p.voted_for == None:
          all_voted = False
          break
      if all_voted:
        self.end_game(None)


  def test_sanity_checks(self, e):
    print "\n\ntest_sanity_checks"
    self.cmd_status([], e)
    e._event_type = "privmsg";
    self.cmd_see(["KillerDucky"], e)
    self.cmd_rob(["KillerDucky"], e)
    self.default_roles = [
      Role.Roles.Werewolf,
      Role.Roles.Werewolf,
      Role.Roles.Seer,
      Role.Roles.Robber,
      Role.Roles.Insomniac
    ]
    self.cmd_start([], e)
    self.cmd_example_game(["1"], e)
    self.cmd_see(["KillerDucky"], e)
    self.cmd_rob(["KillerDucky"], e)
    e._source = "Alice"  ; self.cmd_join([], e)
    e._source = "Bob"    ; self.cmd_join([], e)
    e._source = "Charlie"; self.cmd_join([], e)
    e._source = "KillerDucky"
    self.cmd_status([], e)
    self.cmd_start([], e)
    e._source = "Bob"    ; e._eventtype = "pubmsg" ; self.cmd_see(["KillerDucky"], e)
    e._source = "Bob"    ; e._eventtype = "privmsg"; self.cmd_see(["KillerDucky"], e)
    e._source = "Bob"    ; e._eventtype = "privmsg"; self.cmd_see(["KillerDucky"], e)
    e._source = "Charlie"; e._eventtype = "pubmsg" ; self.cmd_rob(["Bob"], e)
    e._source = "Charlie"; e._eventtype = "privmsg"; self.cmd_rob(["Bob"], e)
    e._source = "Charlie"; e._eventtype = "privmsg"; self.cmd_rob(["Bob"], e)
    self.cmd_end([], e)
    e._source = "Alice"      ; e._eventtype = "pubmsg" ; self.cmd_vote(["KillerDucky"], e)
    e._source = "Alice"      ; e._eventtype = "privmsg"; self.cmd_vote(["Alice"], e)
    e._source = "Alice"      ; e._eventtype = "privmsg"; self.cmd_vote(["KillerDucky"], e)
    e._source = "Bob"        ; e._eventtype = "privmsg"; self.cmd_vote(["KillerDucky"], e)
    e._source = "Charlie"    ; e._eventtype = "privmsg"; self.cmd_vote(["KillerDucky"], e)
    e._source = "KillerDucky"; e._eventtype = "privmsg"; self.cmd_vote(["Alice"], e)
    self.cmd_status([], e)

  def test_1(self, e):
    print "\n\ntest_1"
    self.default_roles = [
      Role.Roles.Werewolf,     # KD
      Role.Roles.Seer,         # Alice
      Role.Roles.Robber,       # Bob
      Role.Roles.Troublemaker, # Charlie
      Role.Roles.Insomniac     # Doug
    ]
    self.cmd_start([], e)
    self.cmd_example_game(["1"], e)
    e._source = "Alice"  ; self.cmd_join([], e)
    e._source = "Bob"    ; self.cmd_join([], e)
    e._source = "Charlie"; self.cmd_join([], e)
    e._source = "Doug"   ; self.cmd_join([], e)
    e._source = "KillerDucky"
    self.cmd_status([], e)
    self.cmd_start([], e)
    e._source = "KillerDucky"; e._eventtype = "privmsg"; self.cmd_see(["left"], e)
    e._source = "Alice"      ; e._eventtype = "privmsg"; self.cmd_see(["KillerDucky"], e)
    e._source = "Bob"        ; e._eventtype = "privmsg"; self.cmd_rob(["KillerDucky"], e)
    e._source = "Charlie"    ; e._eventtype = "privmsg"; self.cmd_swap(["KillerDucky", "Bob"], e)
    e._source = "Alice"      ; e._eventtype = "privmsg"; self.cmd_vote(["KillerDucky"], e)
    e._source = "Bob"        ; e._eventtype = "privmsg"; self.cmd_vote(["KillerDucky"], e)
    e._source = "Charlie"    ; e._eventtype = "privmsg"; self.cmd_vote(["KillerDucky"], e)
    e._source = "Doug"       ; e._eventtype = "privmsg"; self.cmd_vote(["KillerDucky"], e)
    e._source = "KillerDucky"; e._eventtype = "privmsg"; self.cmd_vote(["Alice"], e)
    self.cmd_status([], e)

  def test_inaction(self, e):
    print "\n\ntest_inaction"
    self.default_roles = [
      Role.Roles.Werewolf,     # KD
      Role.Roles.Seer,         # Alice
      Role.Roles.Robber,       # Bob
      Role.Roles.Troublemaker, # Charlie
      Role.Roles.Insomniac,    # Doug
      Role.Roles.Mason,        # left
      Role.Roles.Villager,     # middle
      Role.Roles.Doppelganger  # right
    ]
    self.cmd_start([], e)
    self.cmd_example_game(["1"], e)
    self.no_shuffle = True
    e._source = "Alice"  ; self.cmd_join([], e)
    e._source = "Bob"    ; self.cmd_join([], e)
    e._source = "Charlie"; self.cmd_join([], e)
    e._source = "Doug"   ; self.cmd_join([], e)
    e._source = "KillerDucky"
    e._source = "KillerDucky"; e._eventtype = "privmsg"; self.cmd_see(["rt"], e)
    e._source = "KillerDucky"; e._eventtype = "privmsg"; self.cmd_see(["right"], e)
    e._source = "Alice"      ; e._eventtype = "privmsg"; self.cmd_see(["lt", "mie"], e)
    e._source = "Alice"      ; e._eventtype = "privmsg"; self.cmd_see(["left", "middle"], e)
    e._source = "Bob"        ; e._eventtype = "privmsg"; self.cmd_rob(["-"], e)
    e._source = "Charlie"    ; e._eventtype = "privmsg"; self.cmd_swap(["-"], e)
    e._source = "Alice"      ; e._eventtype = "privmsg"; self.cmd_vote(["KillerDucky"], e)
    e._source = "Bob"        ; e._eventtype = "privmsg"; self.cmd_vote(["KillerDucky"], e)
    e._source = "Charlie"    ; e._eventtype = "privmsg"; self.cmd_vote(["KillerDucky"], e)
    e._source = "Doug"       ; e._eventtype = "privmsg"; self.cmd_vote(["KillerDucky"], e)
    e._source = "KillerDucky"; e._eventtype = "privmsg"; self.cmd_vote(["Alice"], e)
    self.cmd_status([], e)

  def test_2player_game(self, e):
    print "\n\ntest_2player_game"
    self.default_roles = [
      Role.Roles.Werewolf,     # KD
      Role.Roles.Seer,         # Alice
      Role.Roles.Robber,       # Bob
      Role.Roles.Troublemaker, # Charlie
      Role.Roles.Insomniac,    # Doug
    ]
    self.cmd_start([], e)
    self.cmd_example_game(["1"], e)
    self.no_shuffle = True
    e._source = "Alice"  ; self.cmd_join([], e)
    e._source = "KillerDucky"
    self.cmd_start([], e)
    e._source = "KillerDucky"; e._eventtype = "privmsg"; self.cmd_see(["m"], e)
    e._source = "Alice"      ; e._eventtype = "privmsg"; self.cmd_see(["l", "m"], e)
    e._source = "Alice"      ; e._eventtype = "privmsg"; self.cmd_vote(["k"], e)
    e._source = "KillerDucky"; e._eventtype = "privmsg"; self.cmd_vote(["a"], e)
    self.cmd_status([], e)

  def cmd_test(self, args, e):
    self.no_shuffle = True
    #self.test_inaction(e)
    #self.test_sanity_checks(e)
    #self.test_1(e)
    self.test_2player_game(e)
    self.no_shuffle = False

  def cmd_help(self, args, e):
    cmds = [i[4:] for i in dir(self) if i.startswith('cmd_')]
    self.reply(e, "Valid commands: '%s'" % "', '".join(cmds))

  def cmd_example_game(self, args, e):
    if len(args)==1:
       self.example_game = args[0].strip()=="1"
    else:
       self.reply(e, "<example_game [0|1]>. When enabled bot will publicly respond to all commands")

  def cmd_status(self, args, e):
    if self.gamestate == self.GAMESTATE_STARTING:
      self.reply(e, "A game is starting, current players are %s" % self.player_list_to_str(self.live_players))
    elif self.gamestate == self.GAMESTATE_RUNNING:
      self.reply(e, "A game is running, current players are %s" % self.player_list_to_str(self.live_players))
      self.reply(e, "The possible roles are: %s" % " ".join(r.name for r in self.roles_list))
    else:
      self.reply(e, "No game is in progress.")
    if (self.example_game):
      self.reply(e, ("example_game = 1"))

  def cmd_start(self, args, e):
    target = nm_to_n(e.source())
    self.start_game(target)

  def cmd_end(self, args, e):
    target = nm_to_n(e.source())
    self.end_game(target)

  #def cmd_votes(self, args, e):

  #def cmd_del(self, args, e):
  #  for nick in args:
  #    if nick not in self.live_players + self.dead_players:
  #      self.reply(e, "There's nobody playing by the name %s" % nick)
  #    self._removeUser(nick)

  #def cmd_renick(self, args, e):
  #  if len(args) != 1:
  #    self.reply(e, "Usage: renick <nick>")
  #  else:
  #    self.connection.nick(args[0])

  def cmd_see(self, args, e):
    if e.eventtype() != "privmsg":
      self.reply(e, "You must send that command privately")
    elif len(args) == 1 or len(args) == 2:
      viewees = []
      viewees.append(self.match_name(args[0].strip()))
      if len(args) == 2:
        viewees.append(self.match_name(args[1].strip()))
      self.see(e, viewees)
    else:
      self.reply(e, "See whom?")

  def cmd_rob(self, args, e):
    if e.eventtype() != "privmsg":
      self.reply(e, "You must send that command privately")
    elif len(args) == 1:
      target = self.match_name(args[0].strip())
      self.rob(e, target)
    else:
      self.reply(e, "Rob whom?")

  def cmd_swap(self, args, e):
    if e.eventtype() != "privmsg":
      self.reply(e, "You must send that command privately")
    elif len(args) == 1:
      self.swap(e, args[0])
    elif len(args) == 2:
      target = [self.match_name(args[0].strip()), self.match_name(args[1].strip())]
      self.swap(e, target)
    else:
      self.reply(e, "Swap whom?")

  def cmd_vote(self, args, e):
    if e.eventtype() != "privmsg":
      self.reply(e, "You must send that command privately")
    elif len(args) == 1:
      voted_for = self.match_name(args[0])
      if voted_for is not None:
        self.vote(e, voted_for.strip())
        return
    self.reply(e, "Vote for whom?")

  def cmd_join(self, args, e):
    if self.gamestate == self.GAMESTATE_NONE:
      self.reply(e, 'No game is running, perhaps you would like to start one?')
      return
    if self.gamestate == self.GAMESTATE_RUNNING:
      self.reply(e, 'Game is in progress; please wait for the next game.')
      return
    player = nm_to_n(e.source())
    if self.find_player(player):
      self.reply(e, 'You were already in the game!')
    else:
      self.live_players.append(Player(player))
      self.reply(e, 'You are now in the game.')
      self.fix_modes()
      if len(self.live_players) == maxUsers:
        self.start_game(None)

  def cmd_aboutbot(self, args, e):
    self.reply(e, "I am a bot written in Python using the python-irclib library")
    #self.reply(e, "My source code is available at %s" % svn_url)

  #def cmd_moderation(self, args, e):
  #  if self.game_starter and self.game_starter != nm_to_n(e.source()):
  #    self.reply(e, "%s started the game, and so has administrative control. "
  #        "Request denied." % self.game_starter)
  #    return
  #  if len(args) != 1:
  #    self.reply(e, "Usage: moderation on|off")
  #    return
  #  if args[0] == 'on':
  #    self.moderation = True
  #  elif args[0] == 'off':
  #    self.moderation = False
  #  else:
  #    self.reply(e, "Usage: moderation on|off")
  #    return
  #  self.say_public('Moderation turned %s by %s'
  #      % (args[0], nm_to_n(e.source())))
  #  self.fix_modes()

  def do_command(self, e, cmd):
    """This is the function called whenever someone sends a public or
    private message addressed to the bot. (e.g. "bot: blah").  Parse
    the CMD, execute it, then reply either to public channel or via
    /msg, based on how the command was received.  E is the original
    event, and FROM_PRIVATE is the nick that sent the message."""
    if cmd=='': return
    cmds = cmd.strip().split(" ")
    cmds[0]=cmds[0].lower()
    if self.debug and e.eventtype() == "pubmsg":
      if cmds[0][0] == '!':
        e._source = cmds[0][1:] + '!fakeuser@fakehost'
        cmds = cmds[1:]

    try:
      cmd_handler = getattr(self, "cmd_" + cmds[0])
    except AttributeError:
      cmd_handler = None

    if cmd_handler:
      cmd_handler(cmds[1:], e)
      return

    # unknown command:  respond appropriately.
    self.reply(e, "Invalid command")

def usage(exitcode=1):
  print "Usage: wolfmodbot.py [-d] [<config-file>]"
  sys.exit(exitcode)


def main_irc():
  import getopt

  try:
    opts, args = getopt.gnu_getopt(sys.argv, 'd', ('debug',))
  except getopt.GetoptError:
    usage()

  debug = False
  for opt, val in opts:
    if opt in ('-d', '--debug'):
      debug = True

  if len(args) not in (1, 2):
    usage()

  if len(args) > 1:
    configfile = args[1]
  else:
    configfile = 'wolfmodbot.conf'

  import ConfigParser
  c = ConfigParser.ConfigParser()
  c.read(configfile)
  cfgsect = 'wolfmodbot'
  host = c.get(cfgsect, 'host')
  channel = c.get(cfgsect, 'channel')
  nickname = c.get(cfgsect, 'nickname')
  nickpass = c.get(cfgsect, 'nickpass')

  s = string.split(host, ":", 1)
  server = s[0]
  if len(s) == 2:
    try:
      port = int(s[1])
    except ValueError:
      print "Error: Erroneous port."
      sys.exit(1)
  else:
    port = defaultPort

  print "Server = ", server
  bot = WolfModBot(channel, nickname, nickpass, server, port, debug)

def main_fakeirc():
  bot = WolfModBot('chname', 'bot_nickname', 'bot_nickpass', 'server', 'port', False)
  bot.cmd_test([], Event("privmsg", "KillerDucky", None, None))

def main():
  if REAL_IRC:
    main_irc()
  else:
    main_fakeirc()


if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    print "Caught Ctrl-C during initialization."
