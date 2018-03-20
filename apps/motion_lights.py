import appdaemon.plugins.hass.hassapi as hass
import config

class MotionLights(hass.Hass):

  def initialize(self):
    self.utils = self.get_app('utils')
    self.handle = None
    if "delay" in self.args:
      self.listen_state(self.setDelay, self.args["delay"])
      self.delay = int(float(self.get_state(self.args["delay"])))
    else:
      self.delay = 60
    
    if "sensor" in self.args:
      self.sensors = self.args["sensor"].split(",")
      for sensor in self.sensors:
        self.listen_state(self.motion, sensor)
    else:
      self.log("No sensor specified, doing nothing")
      
    if "entity_on" in self.args:
      on_entities = self.args["entity_on"].split(",")
      for on_entity in on_entities:
        self.listen_state(self.off, on_entity)
    else:
      self.log("No entity to turn on specified")
  
  def setDelay(self, entity, attribute, old, new, kwargs):
    self.delay = int(float(new))
    self.log("New delay for {}: {}".format(self.args["entity_on"], new))
      
  def motion(self, entity, attribute, old, new, kwargs):
    if new == "on" and self.utils.dark_outside():
      if self.handle == None:
        if "entity_on" in self.args:
          on_entities = self.args["entity_on"].split(",")
          for on_entity in on_entities:
            self.turn_on(on_entity)
          self.log("First motion detected: i turned {} on, and set timer".format(self.args["entity_on"]))
        else:
          self.log("First motion detected: i turned nothing on, but did set timer")          
        self.handle = self.run_in(self.light_off, self.delay)
      else:
        self.cancel_timer(self.handle)
        self.handle = self.run_in(self.light_off, self.delay)
        self.log("Motion detected again, reset timer")
  
  def light_off(self, kwargs):
    motion_still_detected = False
    for sensor in self.sensors:
      if self.get_state(sensor) == "on":
        motion_still_detected = True
        self.handle = self.run_in(self.light_off, self.delay)
        self.log("Motion still detected, reset timer")
        
    if not motion_still_detected:
      self.handle = None
      if "entity_off" in self.args:
        off_entities = self.args["entity_off"].split(",")
      else:
        off_entities = self.args["entity_on"].split(",")
      for off_entity in off_entities:
        # If it's a scene we need to turn it on not off
        device, entity = self.split_entity(off_entity)
        if device == "scene":
          self.log("I activated {}".format(off_entity))
          self.turn_on(off_entity)
        else:
          self.log("I turned {} off".format(off_entity))
          self.turn_off(off_entity)
        
  def off(self, entity, attribute, old, new, kwargs):
    if self.get_state(entity) == "off":
      self.log("reset handle, because {} was turned off".format(entity))
      self.cancel_timer(self.handle)
      self.handle = None     
    
  
