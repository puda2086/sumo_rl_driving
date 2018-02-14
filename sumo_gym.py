#!python3
__author__ = "Changjian Li"

from copy import deepcopy
import random

from action import get_action_space, disable_collision_check, act, EnvState
from observation import get_observation_space, get_veh_dict, get_obs_dict
from reward import get_reward_list
from utils import class_vars

from include import *

class History:
  def __init__(self, length):
    self._history = []
    self.size = 0
    self.length = length
    
  def add(self, current):
    if self.size >= self.length:
      self._history = self._history[:-1]
    else:
      self.size += 1
    self._history += [current]

  def reset(self):
    self._history = []
    self.size = 0

  def get(self, index):
    return deepcopy(self._history[index])

class SumoCfg():
  def __init__(self, 
               # sumo
               SUMO_CMD, 
               SUMO_TIME_STEP, 
               NET_XML_FILE, 
               EGO_VEH_ID, 
               MAX_VEH_ACCEL, 
               MAX_VEH_DECEL, 
               MAX_VEH_SPEED, 
               # observation
               NUM_LANE_CONSIDERED, 
               NUM_VEH_CONSIDERED, 
               OBSERVATION_RADIUS, 
               # reward
               MAX_COMFORT_ACCEL, 
               MAX_COMFORT_DECEL):
    self.SUMO_CMD = SUMO_CMD
    self.SUMO_TIME_STEP = SUMO_TIME_STEP
    self.NET_XML_FILE = NET_XML_FILE
    self.EGO_VEH_ID = EGO_VEH_ID
    self.MAX_VEH_ACCEL = MAX_VEH_ACCEL
    self.MAX_VEH_DECEL = MAX_VEH_DECEL
    self.MAX_VEH_SPEED = MAX_VEH_SPEED
    
    self.NUM_LANE_CONSIDERED = NUM_LANE_CONSIDERED
    self.NUM_VEH_CONSIDERED = NUM_VEH_CONSIDERED
    self.OBSERVATION_RADIUS = OBSERVATION_RADIUS
    
    self.MAX_COMFORT_ACCEL = MAX_COMFORT_ACCEL
    self.MAX_COMFORT_DECEL = MAX_COMFORT_DECEL

class SumoGymEnv(gym.Env):
  """SUMO environment"""
  def __init__(self, config):
    _attrs = class_vars(config)
    for _attr in _attrs:
      setattr(self, _attr, getattr(config, _attr))
    
    self.action_space = get_action_space()
    self.obsevation_space = get_observation_space(self)
    
    self.env_state = EnvState.NOT_STARTED
    self.agent_control = False # if the ego car is controlled by RL agent
    self.veh_dict_hist = History(2)
    self.obs_dict_hist = History(2)
    self.action_hist = History(2)

    try:  
      sim_label = "sim" + str(random.randint(0, 65536))
      traci.start(self.SUMO_CMD, label = sim_label)
      self.tc = traci.getConnection(sim_label)
    except (traci.FatalTraCIError, traci.TraCIException):
      self.env_state = EnvState.ERROR
      raise

  def step(self, action):
    obs = 0
    done = 0
    reward = 0
    info = None
    return obs, reward, done, info

  def reset(self):
    self.action_hist.reset()
    self.veh_dict_hist.reset()
    self.obs_dict_hist.reset()
    try:
      self.tc.load(self.SUMO_CMD[1:])
      # 1st time step starts the simulation, 
      # 2nd makes sure that all initial vehicles (departure time < SUMO_TIME_STEP) are in scene
      self.tc.simulationStep()
      self.tc.simulationStep()
      disable_collision_check(self, self.EGO_VEH_ID)
      self.env_state = EnvState.NORMAL
      return get_obs_dict(self)
    except (traci.FatalTraCIError, traci.TraCIException):
      self.env_state = EnvState.ERROR
      raise

  def close(self):
    try:  
      self.tc.close()
    except (traci.FatalTraCIError, traci.TraCIException):
      self.env_state = EnvState.ERROR
      raise
    
class MultiObjSumoEnv(SumoGymEnv):
  def step(self, action):
    assert self.env_state == EnvState.NORMAL, "env.env_state is not EnvState.NORMAL"
    try:
      self.env_state = act(self, self.EGO_VEH_ID, action)
      obs_dict =  get_obs_dict(self)
      self.action_hist.add(action)
      self.veh_dict_hist.add(get_veh_dict(self))
      self.obs_dict_hist.add(obs_dict)
    except (traci.FatalTraCIError, traci.TraCIException):
      self.env_state = EnvState.ERROR
      raise    
    info = None
    return obs_dict, get_reward_list(self), self.env_state, info
