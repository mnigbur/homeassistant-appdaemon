import appdaemon.plugins.hass.hassapi as hass
import datetime
import appdaemon
import config


class HouseModes(hass.Hass):

  def initialize(self):
    
    # get current mode
    self.mode = self.get_state("input_select.house_mode")
    # Create some callbacks
    #self.listen_event(self.mode_event, "MODE_CHANGE")
    #self.listen_state(self.mode_event, "input_select.house_mode")
    self.listen_state(self.sun_event, entity = "sun.sun")
    
    # Morning
    morning_week = self.parse_time(self.args["morning_on_week"])
    self.run_daily(self.morning, morning_week, constrain_days="mon,tue,wed,thu,fri")
    morning_weekend = self.parse_time(self.args["morning_on_weekend"])
    self.run_daily(self.morning, morning_weekend, constrain_days="sat,sun")

    # Night
    night_week = self.parse_time(self.args["night_on_week"])
    self.run_daily(self.night, night_week, constrain_days="sun,mon,tue,wed,thu")
    night_weekend = self.parse_time(self.args["night_on_weekend"])
    self.run_daily(self.night, night_weekend, constrain_days="fri,sat")


  def mode_event(self, entity, attribute, old, new, kwargs):
    if new == "Morgen":
      self.morning()
    elif new == "Tag":
      self.day()
    elif new == "Abend":
      self.evening()
    elif new == "Nacht":
      self.night()
      
  def sun_event(self, entity, attribute, old, new, kwargs):
    if new == "above_horizon" and old == "below_horizon":
      self.day();
    if new == "below_horizon" and old == "above_horizon":
      self.evening();
      
  def morning(self, *kwargs):
    #Set the house up for morning
    self.log("Switching mode to Morning")
    self.notify("Switching mode to Morning", name=config.notify)
    self.select_option("input_select.house_mode", "Morgen")
    
    self.turn_on("switch.wohnzimmer_stehlampe")
    self.turn_off("switch.wohnzimmer_couch")
    #self.turn_on("scene.morgen")
    
  def day(self, *kwargs):
    # Set the house up for daytime
    self.log("Switching mode to Day")
    self.notify("Switching mode to Day", name=config.notify)
    self.select_option("input_select.house_mode", "Tag")
    
    self.turn_off("switch.wohnzimmer_stehlampe")

  def evening(self, *kwargs):
    #Set the house up for evening
    self.log("Switching mode to Evening")
    self.notify("Switching mode to Evening", name=config.notify)
    self.select_option("input_select.house_mode", "Abend")
    
    # if self.anyone_home() or self.get_state("input_boolean.vacation") == "on":
    #   self.turn_on("scene.abend")
    self.turn_on("switch.wohnzimmer_stehlampe")
  
  def night(self, *kwargs):
    #Set the house up for night
    self.log("Switching mode to Night")
    self.notify("Switching mode to Night", name=config.notify)
    self.select_option("input_select.house_mode", "Nacht")
    
    self.turn_off("switch.wohnzimmer_stehlampe")
    self.turn_on("switch.wohnzimmer_couch")
