import appdaemon.plugins.hass.hassapi as hass
import config

class utils(hass.Hass):
  def initialize(self):
    pass
    
  def all_on_lights(self):
    """
    Return list of entity_ids for all lights that are currently on
    """
    all_lights = self.get_state("light")
    all_on_lights = []
    
    for light in all_lights:
      state = self.get_state(light)
      if state == "on":
        all_on_lights.append(light)

    return all_on_lights
    
  def dark_outside(self):
    """
    Return if it's dark outside, wither because of sun elevation, or weather conditions
    """
    # sun low
    if int(self.get_state("sun.sun", attribute="elevation")) < 7:
      return True
    # rainy/cloudy day
    if self.get_state("binary_sensor.mistwetter") == "on":
      return True
   
    return False
    
