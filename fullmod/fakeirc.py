class SingleServerIRCBot():
  def __init__(self, *args):
    self.connection = Connection()
    self.channels   = {"chname":Channel()}
  def start(self): pass

class Connection():
  def quit(self, s): pass
  def get_nickname(self): return "bot_nickname"

class Channel():
  def __init__(self):
    self.users = ["usera"]
  def is_moderated(self): return False

class OutputManager():
  def __init__(self, *args): pass
  def start(self): pass
  def send(self, s, ch="default"): print "OutputManger: ch=%s s=%s" % (ch, s)

class Event:
  def __init__(self, eventtype, source, target, arguments=None):
    self._eventtype = eventtype
    self._source = source
    self._target = target
    if arguments:
      self._arguments = arguments
    else:
      self._arguments = []
  def eventtype(self): return self._eventtype
  def source(self): return self._source
  def target(self): return self._target
  def arguments(self): return self._arguments

def nm_to_n(s): return s
