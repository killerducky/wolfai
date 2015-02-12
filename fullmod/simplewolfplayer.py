from pybrain.utilities import drawGibbs
import random

class SimpleWolfPlayer():
  def __init__(self, name, modbot):
    self.name = name
    self.modbot = modbot
  def getAction(self):
    print "name=%s yoyo" % self.name
