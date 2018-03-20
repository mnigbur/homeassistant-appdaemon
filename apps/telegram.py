import appdaemon.plugins.hass.hassapi as hass
import uuid
import enum
import json
import random
import datetime
import subprocess

#thumbs = [  U+1F44D U+1F3FF  ,U+1F44D U+1F3FE, U+1F44D U+1F3FD  ,   U+1F44D U+1F3FC, U+1F44D U+1F3FB, U+1F44D  ]
thumbs = ["{}{}".format(u'\U0001f44d',u'\U0001f3ff'),"{}{}".format(u'\U0001f44d',u'\U0001f3fe'), "{}{}".format(u'\U0001f44d',u'\U0001f3fd'), "{}{}".format(u'\U0001f44d',u'\U0001f3fc'), "{}{}".format(u'\U0001f44d',u'\U0001f3fc'), "{}".format(u'\U0001f44d')]
fingers = ["{}{}".format(u'\U0001f44c',u'\U0001f3ff'),"{}{}".format(u'\U0001f44c',u'\U0001f3fe'), "{}{}".format(u'\U0001f44c',u'\U0001f3fd'), "{}{}".format(u'\U0001f44c',u'\U0001f3fc'), "{}{}".format(u'\U0001f44c',u'\U0001f3fc'), "{}".format(u'\U0001f44c')]
#fingers = [u'\U0001f3ff', u'\U0001f3fe', u'\U0001f3fd', u'\U0001f3fc', u'\U0001f3fc', u'\U0001f44d']

fingers = []
ALARM_KEYBOARD = {
    "Arm Stay".format(u'\U0001f3E1',u'\U0001f512')  : 'armStay',
    "Force Arm Stay".format(u'\U0001f3E1',u'\U0001f512')  : 'armStayForce',
    "Arm Away".format(u'\U0001f510')                : 'armAway',
    "Arm Away Delay".format(u'\U000023f3')          : 'armAwayDelay',
    "Force Arm Away".format(u'\U0001f510')          : 'armAwayForce',
    "Force Arm Away Delay".format(u'\U0001f510')    : 'armAwayDelayForce',
    "Disarm".format(u'\U0001f513')                  : 'disarm',
    "Sensor Overview".format(u'\U0001f440')          : 'sensorOverview',
    "Zone Bypass".format(u'\U0001f515')              : 'sensorBypass',
    "{} Menu".format(u'\U0001f3e0')                  : 'backToMenu',
    "{} Panic".format(u'\U0001f4e2')                : 'panic',
    "{}".format(u'\U0001f4f9')                      : 'cameras',
    "Alarm Functions"                                : 'alarmFunctions',
    "Refresh Status"                                : 'status',
    "Rooms"                                          : 'rooms',
    "{} Rooms".format(u'\U0001f448')                : 'rooms',
    'Lights'                                         :"lights",
    'Switches'                                       :"switches",
    'Scenes'                                         :"scenes",
    'Cameras'                                         :"cameras",
    "{} Alarm Functions".format(u'\U0001f448')      :'alarmFunctions',
    "enable"                                         :'unbypass',
    "bypass"                                        :'bypass',
    "Cameras"                                        :"cameras",
    "Done "                                          :"done1",
    u'\U0001f448'                                    :"back"
    }
ALARM_KEYBOARD_REVERSED = {v: k for k, v in ALARM_KEYBOARD.items()}
KEYBOARD_STRUCTURE = {
  'disarmed' :               ['armStay',
                      ['armAway','armAwayDelay'],
                        'sensorBypass',
                        'sensorOverview',
                        'status',
                      ['backToMenu','panic','cameras']],
  'armed_home' :           ['disarm',
                        'sensorBypass',
                        'sensorOverview',
                        'status',
                      ['backToMenu','panic','cameras']],
  'armed_away' :           ['disarm',
                        'sensorBypass',
                        'sensorOverview',
                        'status',
                      ['backToMenu','panic','cameras']],
  'armed_away_fail' : ['armAwayForce',
                        'armAway',
                        'sensorBypass',
                        'sensorOverview',
                      ['backToMenu','panic','cameras']],
  'pending_fail' :       ['armAwayDelayForce',
                        'armAwayDelay',
                        'sensorBypass',
                        'sensorOverview',
                      ['backToMenu','panic','cameras']],
  'armed_home_fail' : ['armStayForce',
                        'armStay',
                        'sensorBypass',
                        'sensorOverview',
                      ['backToMenu','panic','cameras']],
  'pending' :             ['disarm',
                        'armAwayForce',
                        'status',
                      ['backToMenu','panic']],
  'warning' :             ['disarm',
                        'armAwayForce',
                        'armStayForce',
                        'sensorOverview',
                        'status',
                      ['backToMenu','panic','cameras']],
  'triggered' :           ['disarm',
                        'sensorOverview',
                        'status',
                      ['backToMenu','cameras']]}

KEY_TO_SERVICE = {
  'armStay'            :'alarm_arm_home',
  'armStayForce'      :'alarm_arm_home_force',
  'armAway'            :'alarm_arm_away',
  'armAwayForce'      :'alarm_arm_away_force',
  'armAwayDelay'      :'alarm_arm_away_delay',
  'armAwayDelayForce' :'alarm_arm_away_delay_force',
  'disarm'            :'alarm_disarm',
  'panic'              :'alarm_trigger'
}
KEY_TO_EXPECTED_OUTCOME = {
  'armStay'            :'armed_home',
  'armStayForce'      :'armed_home',
  'armAway'            :'armed_away',
  'armAwayForce'      :'armed_away',
  'armAwayDelay'      :'pending',
  'armAwayDelayForce'  :'pending',
  'disarm'            :'disarmed',
  'panic'              :'triggered'
}
KEY_ON_OFF = {
  'on'            :True,
  'off'            :False
}
BOOL_TO_SERVICE = {
  True            :"turn_on",
  False            :"turn_off"
}
BOOL_TO_STATE = {
  True            : "on",
  False            : "off"
}
class TelegramBotEventListener(hass.Hass):
  """Event Listener for Telegram bot events"""
  def initialize(self):
    self.log("Listening for telegram texts...")
    self.listen_event(self.receive_telegram_text, 'telegram_text')
    self.handle = None
    self.handleIncomingCode = None
    self.running_state_listeners = set()
    self.delay = 1
    self.broadcastStartup("Homeassistant Online")
    if self.args.get("telegram_modules"):
      self.telegram_modules = {x: self.get_app(x) for x in self.args["telegram_modules"]}
      self.log("Modules - >")
      for module in self.telegram_modules.items():
        self.log("{} - {}".format(module[0],'active' if module[1] else "offline"))

  def isFromModule(self, payload_event, accessgroup):
    self.log(str(self.telegram_modules.values()))
    for telegram_module in self.telegram_modules.items():
      if telegram_module[1]:
        self.log(self.config[telegram_module[0]]['keywords'])
        if payload_event['text'].split()[0] in self.config[telegram_module[0]]['keywords']:
          telegram_module[1].execute(payload_event)
          return True
    return False

  def broadcastStartup (self, message):
    adminUsers = self.args["groups"]['admin']['chatids']
    for user in adminUsers:
      self.call_service("telegram_bot/send_message",
        target = user,
        message = message)

  def getAccessGroup(self,userID, groupItems):
    accessgroup = None
    for group in groupItems:
      for chat_id in group[1]["chatids"]:
        if userID == chat_id:
          accessgroup = group[1]
          accessgroup['groupname'] = group[0]
          return accessgroup
    return accessgroup
    
  def receive_telegram_text(self, event_id, payload_event, *args):
    assert event_id == 'telegram_text'
    self.log("{---+")
    accessgroup = self.getAccessGroup(str(payload_event["user_id"]),self.args["groups"].items())
    #self.log("ACCESS GROUP - <{}>".format(accessgroup))
    self.log("{} ---> {}".format(payload_event["from_first"],payload_event["text"]))
    if(accessgroup==None):
      self.errorMessage(payload_event,"User ID was not found\nPlease contact administrator")
      self.log("ERROR - user_id <{}> not found".format(payload_event["user_id"]))
    else:
      simpleFunction = ALARM_KEYBOARD_TO_METHOD.get(ALARM_KEYBOARD.get(payload_event['text']))
      if simpleFunction is not None:
        simpleFunction(self, payload_event, accessgroup)
      else:
        text = payload_event['text'].lower()
        replace_text = ALARM_KEYBOARD_REVERSED['back']
        refined_text = text.replace(replace_text,"").strip()
        self.log("{} ({}) ---> *{}*".format(text,replace_text,refined_text))
        text = payload_event['text'] = refined_text
        if text.startswith("turn off") or text.startswith("turn on"):
          self.turn_on_off(payload_event, accessgroup)
        elif text.startswith("bypass") or text.startswith("enable"):
          self.bypassZone(payload_event, accessgroup)
        elif text.endswith("sensors"):
          self.sensorStatusSelective(payload_event, accessgroup)
        elif self.isFromModule(payload_event, accessgroup):
          return True
        elif self.isRoom(payload_event, accessgroup):
          self.roomControl(payload_event, accessgroup)
        elif self.endsWithEntity(payload_event, accessgroup):
          self.roomEntityControl(payload_event, accessgroup)
        elif self.isFromModule(payload_event, accessgroup):
          return
        else:
          self.printMenu(payload_event,accessgroup)



  def alarmFunction(self, payload_event, accessgroup):
    alarm_command = ALARM_KEYBOARD.get(payload_event['text'])
    alarm_service = KEY_TO_SERVICE[alarm_command]
    chatid = str(payload_event['chat_id'])
    self.log("Calling Alarm Service {} from {}".format(alarm_service,chatid))
    service_result = self.call_service("alarm_control_panel/{}".format(alarm_service),entity_id = "alarm_control_panel.house", code = {'chat_id':chatid,'name':payload_event['from_first']})
    true_service_result = self.getTrueResultAlarm(service_result,"alarm_control_panel.house")
    if true_service_result is None:
      trippedSensors = self.get_state("alarm_control_panel.house","trippedsensors")
      state = self.get_state("alarm_control_panel.house")
      if state == KEY_TO_EXPECTED_OUTCOME[alarm_command]:
        message = "Already {}".format(str(state).upper())
      elif state == 'disarmed':
        message = "<code>{}</code> Fail due to {}".format(alarm_command.upper(), trippedSensors)
        state = '{}_fail'.format(KEY_TO_EXPECTED_OUTCOME[alarm_command])
      else:
        message = "<code>{}</code> Fail for unknow reason".format(alarm_command.upper())
    else:
      state = true_service_result['state']
      trippedSensors = true_service_result['attributes']['trippedsensors']
      if state == KEY_TO_EXPECTED_OUTCOME[alarm_command]:
        message = "Alarm successfully changed to <code>{}</code>".format(true_service_result['state'].upper())
        if state == "pending":
          self.handle = self.listen_state(self.armDelayCallback, entity_id = 'alarm_control_panel.house',old = 'pending',new = 'armed_away', chat_id = payload_event['chat_id'], accessgroup = accessgroup)  
      elif state == 'disarmed':
        message = "<code>{}</code> Fail due to {}".format(alarm_command.upper(), trippedSensors)
        state = '{}_fail'.format(KEY_TO_EXPECTED_OUTCOME[alarm_command])
        self.log("STATE - ".format(state))
      else:
        message = "<code>{}</code> Fail for unknow reason".format(alarm_command.upper())
    keyboard = self.getKeyboard(state, accessgroup)
    self.call_service("telegram_bot/send_message",
      target = payload_event['chat_id'],
      message = message,
      keyboard = keyboard)

  def armDelayCallback(self, entity, attribute, old, new, kwargs):
    self.log("CALLBACK DELAY - {} - {} - {}".format(old,new,kwargs))
    if new != 'disarmed':
      keyboard = self.getKeyboard(new, kwargs['accessgroup'])
      self.call_service("telegram_bot/send_message",
        target = kwargs['chat_id'],
        message = "Alarm successfully changed to <code>{}</code>".format(new.upper()),
        keyboard = keyboard)
    self.cancel_listen_event(self.handle)
      
  def getTrueResultAlarm(self, data, entity_id):
    #self.log("DATA - {}".format(data))
    for item in data:
      #self.log("ITEM - {}".format(item))
      if item.get('entity_id') == entity_id:
        if self.handle is not None:
          self.cancel_listen_event(self.handle)
        return item
    return None
  
  def getTrueResultGeneral(self, data, entity_id):
    #self.log("DATA - {}".format(data))
    for item in data:
      #self.log("ITEM - {}".format(item))
      if item.get('entity_id') == entity_id:
        return item
    return None
  

  def sensorStatus(self, payload_event, accessgroup):
    self.log("Sensor Status")
    alarm_sensor_states = self.get_state("alarm_control_panel.house","all")
    all_sensor_states = self.get_state('binary_sensor')
    #self.log(alarm_sensor_states['attributes']['allsensors'])
    message = ''
    for eid in alarm_sensor_states['attributes']['allsensors']:
      message+= "[{}] - {}\n".format(str(all_sensor_states[eid]['state']).upper(),all_sensor_states[eid]['attributes']['friendly_name'])
    self.log(message)
    self.call_service("telegram_bot/send_message",
      target = payload_event['chat_id'],
      message = message)

  def sensorStatusSelective(self, payload_event, accessgroup):
    self.log("Sensor Status Selective")
    all_group_states = self.get_state('group')
    friendly_name = payload_event['text']
    sensors = None
    for group in all_group_states.items():
      if type(group[1]) == dict:
        telegram_name = group[1]['attributes']['telegram_name'].lower()
        #self.log("<{}> - <{}>".format(friendly_name_text, friendly_name_test))
        if telegram_name == friendly_name:
          sensors = group[1]['attributes']['entity_id']
          break
        
    all_sensor_states = self.get_state('binary_sensor')
    message = ''
    for eid in sensors:
      message+= "[{}] - {}\n".format(str(all_sensor_states[eid]['state']).upper(),all_sensor_states[eid]['attributes']['friendly_name'])
    self.log(message)
    self.call_service("telegram_bot/send_message",
      target = payload_event['chat_id'],
      message = message)

  def bypassZone(self, payload_event, accessgroup):
    splitText = payload_event['text'].split()
    self.log("BYPASS ZONE")
    all_group_states = self.get_state('group')
    name_text = ' '.join(splitText[1:])
    bare_function = splitText[0]
    function = ALARM_KEYBOARD[bare_function]
    friendly_name_text = "{} sensors".format(name_text)
    entity_id = None
    for group in all_group_states.items():
      if type(group[1]) == dict:
        friendly_name_test = group[1]['attributes']['friendly_name'].lower()
        #self.log("<{}> - <{}>".format(friendly_name_text, friendly_name_test))
        if friendly_name_text == friendly_name_test:
          entity_id = group[0]
          break
    if entity_id:
      handle = self.call_service("alarm_control_panel/alarm_{}_zone".format(function),zone = entity_id)
      message = None
      if handle == list():
        state = self.get_state("alarm_control_panel.house")
        trippedSensors = self.get_state("alarm_control_panel.house","trippedsensors")
        if state in ['armed_home', 'armed_away']:
          message = "{} of {} Fail due to {}".format(bare_function.title(),name_text.title(), trippedSensors)
        else:
          message = "Sorry {} Already {}".format(name_text.title(),bare_function)
      else:
        self.log("HANDLE - <{}>".format(handle))
        trippedSensors = handle[0]['attributes']['trippedsensors']
        if trippedSensors != list():
          message = "{} of {} Fail due to {}".format(bare_function.title(),name_text.title(), trippedSensors)
      if message:
        self.call_service("telegram_bot/send_message",
          target = payload_event['chat_id'],
          message = message,
          disable_notification = True)
      self.run_in(self.bypass,1,payload_event = payload_event, accessgroup = accessgroup)
      #self.listenForService()

  def bypass(self,*args):
    self.log("Bypass")
    #self.log(args)
    payload_event = args[0]
    accessgroup = payload_event.get('accessgroup')
    if accessgroup is not None:
      payload_event = payload_event.get('payload_event')
    else:
      accessgroup = args[1]
    alarm_state = self.get_state("alarm_control_panel.house","all")
    alarm_zones = alarm_state['attributes']['zones']

    bypassedSensors = alarm_state['attributes']['bypassedsensors']
    all_group_states = self.get_state('group')

    keyboard = []
    message = ''
    for zone_id in alarm_zones:
      zone_friendly_name = all_group_states[zone_id]['attributes']['friendly_name'].replace(" Sensors","")
      if set(all_group_states[zone_id]['attributes']['entity_id']) <= set(bypassedSensors):
        keyboard.append("Enable {0}".format(zone_friendly_name))
        message+="{} {}\n".format(u'\U0000274C',zone_friendly_name)
      else:
        keyboard.append("Bypass {0}".format(zone_friendly_name))
        message+="{} {}\n".format(u'\U00002705',zone_friendly_name)

    keyboard.append(ALARM_KEYBOARD_REVERSED['sensorOverview'])
    keyboard.append("{},{}".format(ALARM_KEYBOARD_REVERSED['backToMenu'], ALARM_KEYBOARD_REVERSED['alarmFunctions']))
    self.call_service("telegram_bot/send_message",
      target = payload_event['chat_id'],
      message = message,
      disable_notification = True,
      keyboard = keyboard)
    
    
    #self.log(alarm_state)

  def panic(self, payload_event, accessgroup):
    self.log("Panic")
    result = self.call_service("alarm_control_panel/alarm_trigger",entity_id = "alarm_control_panel.house",code = {'chat_id':payload_event['chat_id'],'name':payload_event['from_first']})
    result = self.getTrueResultAlarm(result,"alarm_control_panel.house")
    self.log("True Result - {}".format(result))    
    keyboard = self.getKeyboard("triggered", accessgroup)
    self.call_service("telegram_bot/send_message",
      target = payload_event['chat_id'],
      message = "{} Alarm <code>{}</code>".format(u'\U000026d4',str(result['state']).upper()),
      keyboard = keyboard)

  def alarm_functions(self,payload_event, accessgroup):
    self.log("Serving Alarm Function Menu")
    alarm_state = self.get_state("alarm_control_panel.house","all")
    status = "Current Alarm Status - <code>{}</code>".format(str(alarm_state['state']).upper())
    self.call_service("telegram_bot/send_message",
      target = payload_event['chat_id'],
      message = status,
      disable_notification = True,
      keyboard = self.getKeyboard(alarm_state['state'],accessgroup,payload_event))
    self.log(status)
    self.log("+---}")
  def roomEntityControl(self,payload_event, accessgroup):
    entity = payload_event["text"].split()[-1]
    room_text = payload_event["text"][:-(len(entity)+1)]
    room_object = None
    for room in accessgroup["rooms"]:
      telegram_name_room = self.getTelegramName(room).lower()
      if telegram_name_room==room_text:
        room_object = room
    
    self.log("{} - {}".format(entity,room_text))
    keyboard = []
    group_entities = self.get_state(room_object,"attributes")["entity_id"]
    for group_entity in group_entities:
      if group_entity in accessgroup[entity]:
        telegram_name = self.getTelegramName(group_entity)
        keyboard.append("Turn on {0},Turn off {0}".format(telegram_name))
    keyboard.append("Turn on all {0} {1}".format(room_text.title(),entity.title()))
    keyboard.append("Turn off all {0} {1}".format(room_text.title(),entity.title()))
    keyboard.append("{} {},{}".format(ALARM_KEYBOARD_REVERSED['back'],room_text.title(), ALARM_KEYBOARD_REVERSED['backToMenu']))
      
    self.call_service("telegram_bot/send_message",
          target = payload_event['chat_id'],
          message = "Which {} in the {} do you want to control?".format(entity,room_text),
          disable_notification = True,
          keyboard = keyboard)
    self.log("+---}")
  def endsWithEntity(self, payload_event, accessgroup):
    functions = ["lights","switches","scenes"]
    for function in functions:
      if payload_event["text"].endswith(function):
        room_text = payload_event["text"][:-(len(function)+1)]
        for room in accessgroup["rooms"]:
          friendly_name_temp = str(self.get_state(room,"friendly_name")).lower()
          if friendly_name_temp==room_text:
            return True
    return False
  def roomControl(self, payload_event, accessgroup):
    self.log("Serving Room Control Menu")
    self.call_service("telegram_bot/send_message",
          target = payload_event['chat_id'],
          message = "Which do you want to control?",
          disable_notification = True,
          keyboard = self.getKeyboard("room_control",accessgroup,payload_event))
    self.log("+---}")
  def isRoom(self, payload_event, accessgroup):
    for room in accessgroup["rooms"]:
      friendly_name_temp = str(self.get_state(room,"friendly_name")).lower()
      self.log("*{}* =? *{}*".format(payload_event["text"],friendly_name_temp))
      if payload_event["text"]==friendly_name_temp:
        return True
    return False

  def getTelegramName(self, entity_id):
    telegram_name = self.get_state(entity_id,"telegram_name")
    if telegram_name is None:
      telegram_name = self.friendly_name(entity_id)
      if telegram_name is None:
        telegram_name = "None"
    return telegram_name
        
  def turn_on_off(self, payload_event,accessgroup, *args):
    isOn = False
    isAll = False
    text = (payload_event['text']).replace(" the "," ").lower()
    friendly_name = text[8:].lstrip().lower()
    if text.startswith("turn on"): isOn = True
    self.log("Checking if entity is a light...")
    entity_labels = ["lights","switches","scenes"]
    self.log("Entity - {}".format(friendly_name))
    if friendly_name.startswith("all "):
      payload_event['text'] = friendly_name.replace("all ","")
      if(payload_event['text'] in accessgroup):
        self.log("IS A ENTITY!!!")
        entities = []
        for entity in accessgroup[payload_event['text']]:
          entities.append(entity)
        self.entity_turn_on_off(entities,entity,isOn,payload_event)
      elif(self.endsWithEntity(payload_event,accessgroup)):
        self.log("ENDS WITH ROOM ENTITY")
        entity = payload_event["text"].split()[-1]
        room_text = payload_event["text"][:-(len(entity)+1)]
        room_object = None
        for room in accessgroup["rooms"]:
          telegram_name = self.getTelegramName(room).lower()
          if telegram_name==room_text:
            room_object = room
        group_entities = self.get_state(room_object,"attributes")["entity_id"]
        entities = []
        for group_entity in group_entities:
          if group_entity in accessgroup[entity]:
            entities.append(group_entity)
        self.entity_turn_on_off(entities,entity,isOn,payload_event)
      return
    self.log("Entity - {}".format(friendly_name))
    for entity_label in entity_labels:
      for entity in accessgroup[entity_label]:
        telegram_name = self.getTelegramName(entity).lower()
        if friendly_name==telegram_name:
          self.log("Entity is a {}".format(entity_label))
          self.entity_turn_on_off(entity,friendly_name,isOn,payload_event)
          return
    self.log("Invalid Turn on/off request")
    self.errorMessage(payload_event, "Invalid Request")
        
  
  def entity_turn_on_off(self, entity_id,friendly_name, isOn, payload_event):
    self.log("EID - <{}>".format(entity_id))
    entity_id_set = set()
    delay = self.delay
    if type(entity_id) == str:
      state = self.get_state(entity_id)
      state_mode = self.get_state(entity_id, "statefull")
      entity_delay = self.get_state(entity_id, "delay_confirmation")
      if entity_delay:
        delay = entity_delay
      entity_id_set.add(entity_id)
    else:
      state = not isOn
      state_mode = False
      friendly_name = 'group'
      entity_id_set|= set(entity_id)

    self.log("RUNNING STATE LISTENERS - <{}>".format(self.running_state_listeners))
    if entity_id_set.intersection(self.running_state_listeners) != set():
      self.call_service("telegram_bot/send_message",
            target = payload_event['chat_id'],
            message = "{} is currently being controlled".format(friendly_name.title()),
            disable_notification = False)
      return
    else:
      if type(entity_id) == str:
        self.running_state_listeners.add(entity_id)
      else:
        self.running_state_listeners |= set(entity_id)
    self.log("RUNNING STATE LISTENERS 2- <{}>".format(self.running_state_listeners))
    self.log("State Mode - {}".format(state_mode))
    self.log("STATE - {}".format(state))
    if state_mode != False and KEY_ON_OFF[state] == isOn:
      self.running_state_listeners.remove(entity_id)
      self.call_service("telegram_bot/send_message",
            target = payload_event['chat_id'],
            message = "{} is already turned {}".format(friendly_name.title(),state),
            disable_notification = False)
    else:
      self.log("{} {}".format(BOOL_TO_SERVICE[isOn], entity_id))
      listen_handle = self.listen_state(self.entity_state_change, entity_id, isOn = isOn, payload_event = payload_event, friendly_name = friendly_name, state_mode = state_mode)
      service_handle = self.call_service("homeassistant/{}".format(BOOL_TO_SERVICE[isOn]), entity_id = entity_id)
      if type(entity_id) == list:
        self.call_service("telegram_bot/send_message",
          target = payload_event['chat_id'],
          message = "{}{}".format(ALARM_KEYBOARD_REVERSED['done1'],random.choice(thumbs)),
          disable_notification = False)
      timer_handle = self.run_in(self.cancel_handle,delay,listen_handle = listen_handle, service_handle = service_handle)
      self.log("+---}")

  def entity_state_change (self, entity, attribute, old, new, kwargs):
      self.log("<{}> - <{}> - <{}> - {} -> {}".format(entity, attribute, kwargs, old, new))
      friendly_name = kwargs['friendly_name']
      isOn = kwargs['isOn']
      payload_event = kwargs['payload_event']
      if KEY_ON_OFF[new] == isOn:
          message = "{}{}\n{} is {}".format(ALARM_KEYBOARD_REVERSED['done1'],random.choice(thumbs), friendly_name.title(),new)
      else:
          message = "(Weird) Unable to turn {} {}".format(friendly_name.title(), new)
      self.call_service("telegram_bot/send_message",
        target = payload_event['chat_id'],
        message = message,
        disable_notification = False)

  def cancel_handle(self, *args):
      listen_handle = args[0]['listen_handle']
      service_handle = args[0]['service_handle']
      entity,attribute, kwargs = self.info_listen_state(listen_handle)
      self.cancel_listen_state(listen_handle)
      self.log("CANCELLING - {}>{}>{}".format(entity, attribute, kwargs))
      friendly_name = kwargs['friendly_name']
      isOn = kwargs['isOn']
      payload_event = kwargs['payload_event']
      if type(entity) == str:
        self.running_state_listeners.remove(entity)
        state = self.get_state(entity)
        self.log("STATE - <{}>".format(state))
        state_mode = kwargs['state_mode']
        if state_mode ==False:
            message =  "{}{}\n{} is {}".format(ALARM_KEYBOARD_REVERSED['done1'],random.choice(thumbs),friendly_name.title(),BOOL_TO_STATE[isOn])
        else:
            message = "Unable to turn {} {}".format(BOOL_TO_STATE[isOn], friendly_name.title())
        if (state_mode == False and service_handle == list()) or KEY_ON_OFF[state] != isOn:
            self.log("WARNING - DELAYED FAILED CANCEL")
            self.call_service("telegram_bot/send_message",
              target = payload_event['chat_id'],
              message = message,
              disable_notification = False)
      else:
          self.log("EIDs - {}".format(entity))
          self.running_state_listeners-=set(entity)
          state = self.get_state()
          faultList = []
          for eid in entity:
              state = self.get_state(eid)
              if KEY_ON_OFF[state] != isOn:
                  faultList.append(eid)
          if faultList == list():
              return
          else:
              message = "Unable to turn {} {}".format(BOOL_TO_STATE[isOn], self.friendly_name(faultList.pop()))
              for eid in faultList:
                  message += ", {}".format(self.friendly_name(eid))
          self.call_service("telegram_bot/send_message",
            target = payload_event['chat_id'],
            message = message,
            disable_notification = False)

  def checkState(self, *args):
      entity_id = args[0]['entity_id']
      payload_event = args[0]['payload_event']
      isOn = args[0]['isOn']
      state = self.get_state(entity_id)
      if KEY_ON_OFF[state] == isOn:
          self.log("COMPLETED 2")
      else:
          self.log("ERROR 2")
  def getKeyboard(self,keyboard_type,accessgroup,payload_event = None):
    keyboard = []
    if keyboard_type=="menu":
      keyboard = accessgroup["menu"]
    elif keyboard_type=="switches" or keyboard_type=="lights" or keyboard_type=="other":
      for entity in accessgroup[keyboard_type]:
        self.log("ENTITY - {}".format(entity))
        telegram_name = self.getTelegramName(entity)
        keyboard.append("Turn on {0},Turn off {0}".format(telegram_name))
      keyboard.append("Turn on all {0}".format(keyboard_type))
      keyboard.append("Turn off all {0}".format(keyboard_type))
      keyboard.append(ALARM_KEYBOARD_REVERSED["backToMenu"])
    elif keyboard_type=="scenes":
      for entity in accessgroup["scenes"]:
        telegram_name = self.getTelegramName(entity)
        keyboard.append("Turn on {}".format(telegram_name))
      keyboard.append(ALARM_KEYBOARD_REVERSED["backToMenu"])
    elif keyboard_type=="rooms":
      for entity in accessgroup["rooms"]:
        telegram_name = self.getTelegramName(entity)
        keyboard.append(telegram_name)
      keyboard.append(ALARM_KEYBOARD_REVERSED["backToMenu"])
    elif keyboard_type =="room_control":
      functions = ["Lights","Switches","Scenes"]
      for entry in functions:
        keyboard.append("{} {}".format(payload_event["text"].title(),entry))
      keyboard.append("{} Rooms,{}".format(ALARM_KEYBOARD_REVERSED['back'],ALARM_KEYBOARD_REVERSED['backToMenu']))
    elif keyboard_type in KEYBOARD_STRUCTURE.keys():
      keyboard = self.getRefinedKeyboard(KEYBOARD_STRUCTURE[keyboard_type],accessgroup['alarm']['functions'])            
    return keyboard

  def getRefinedKeyboard(self, keyboard, alarmAccessGroup):
    refinedKeyboard = []
    for item in keyboard:
      if(type(item) == str):
        if item not in alarmAccessGroup:
          refinedKeyboard.append(ALARM_KEYBOARD_REVERSED[item])
      else:
        line = ALARM_KEYBOARD_REVERSED[item[0]]
        for string in item[1:]:
          if string not in alarmAccessGroup:
            line += ",{}".format(ALARM_KEYBOARD_REVERSED[string])
        refinedKeyboard.append(line)
    return refinedKeyboard
  
  def control_lights(self,payload_event, accessgroup):
    self.log("Serving Light Menu")
    self.call_service("telegram_bot/send_message",
          target = payload_event['chat_id'],
          message = "Which lights do you want to control? {}".format(u'\U0001f4a1'),
          disable_notification = True,
          keyboard = self.getKeyboard("lights",accessgroup,payload_event))
    self.log("+---}")
  def control_switches(self,payload_event, accessgroup):
    self.log("Serving Switch Menu")
    self.call_service("telegram_bot/send_message",
          target = payload_event['chat_id'],
          message = "Which switches do you want to control?",
          disable_notification = True,
          keyboard = self.getKeyboard("switches",accessgroup,payload_event))
    self.log("+---}")
  def cameras(self, payload_event, accessgroup):
    self.log("Serving Camera Menu")
    self.call_service("telegram_bot/send_message",
          target = payload_event['chat_id'],
          message = "Feature Coming Soon {}".format(u'\U0001f609'),
          disable_notification = True)
    self.log("+---}")
  def control_scenes(self, payload_event, accessgroup):
    self.log("Serving Scene Menu")
    self.call_service("telegram_bot/send_message",
          target = payload_event['chat_id'],
          message = "Which scenes do you want to control?",
          disable_notification = True,
          keyboard = self.getKeyboard("scenes",accessgroup,payload_event))
    self.log("+---}")
  def printMenu(self,payload_event, accessgroup):
    self.log("Serving Main Menu")
    self.call_service("telegram_bot/send_message",
          target = payload_event['chat_id'],
          title = "Hi {0} {1}".format(payload_event['from_first'],u'\U0001f44b'),
          message = "How can I help you?",
          disable_notification = True,
          keyboard = self.getKeyboard("menu",accessgroup,payload_event))
    self.log("+---}")
  def errorMessage(self,payload_event, error_text):
    self.log("Serving Error Message")
    self.call_service("telegram_bot/send_message",
          target = payload_event['chat_id'],
          title = "Error",
          message = error_text,
          disable_notification = True)
    self.log("+---}")
  def rooms(self, payload_event, accessgroup):
    self.log("Serving Room Menu")
    self.call_service("telegram_bot/send_message",
          target = payload_event['chat_id'],
          message = "Which room do you want to control?",
          disable_notification = True,
          keyboard = self.getKeyboard("rooms",accessgroup,payload_event))
    self.log("+---}")
    
ALARM_KEYBOARD_TO_METHOD = {
  'armStay'          :TelegramBotEventListener.alarmFunction,
  'armStayForce'     :TelegramBotEventListener.alarmFunction,
  'armAway'          :TelegramBotEventListener.alarmFunction,
  'armAwayForce'      :TelegramBotEventListener.alarmFunction,
  'armAwayDelay'      :TelegramBotEventListener.alarmFunction,
  'armAwayDelayForce':TelegramBotEventListener.alarmFunction,
  'sensorOverview'   :TelegramBotEventListener.sensorStatus,
  'sensorBypass'     :TelegramBotEventListener.bypass,
  'backToMenu'       :TelegramBotEventListener.printMenu,
  'panic'            :TelegramBotEventListener.alarmFunction,
  'cameras'         :TelegramBotEventListener.cameras,
  'disarm'           :TelegramBotEventListener.alarmFunction,
  'alarmFunctions'   :TelegramBotEventListener.alarm_functions,
  'status'       :TelegramBotEventListener.alarm_functions,
  'rooms'        :TelegramBotEventListener.rooms,
  'lights'       :TelegramBotEventListener.control_lights,
  'switches'       :TelegramBotEventListener.control_switches,
  'scenes'       :TelegramBotEventListener.control_scenes,
  }