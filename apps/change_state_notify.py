import appdaemon.plugins.hass.hassapi as hass
import config

class ChangeStateNotify(hass.Hass):

  def initialize(self):
    self.utils = self.get_app('utils')
    
    if "entities" in self.args:
      self.entities = self.args["entities"].split(",")
      for entity in self.entities:
        self.listen_state(self.stateChange, entity)
    else:
      self.log("No entities specified, doing nothing")
      
          
  def stateChange(self, entity, attribute, old, new, kwargs):
    if new != old:
      self.log("State changed '{}' from '{}' to '{}'".format(entity, old, new))
      self.notify("State changed '{}' from '{}' to '{}'".format(entity, old, new), name=config.notify)
  