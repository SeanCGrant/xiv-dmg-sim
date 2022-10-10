from .baseActor import BaseActor
import pandas as pd
import numpy as np


# dancer-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, wpn_delay, ten=400):
        # Dancer-specific values
        jobMod = 115
        trait = 120

        super().__init__(jobMod, trait, wd, ap, det, spd, wpn_delay, ten=400)

        # override auto potency
        self.auto_potency = 80  # check this value

        self.pers_buffs = {}  # personal buffs
        self.resources = {'esprit': 0, 'feathers': 0}  # track personal resources
        buffs = {'F': 0, 'RC': 0, 'FF': 0}
        self.buffs = pd.Series(buffs)

    def choose_action(self):
        # determine current action, based on current buffs/procs
        if self.buffs['FF'] > 0:
            # use FF proc if available first
            self.buffs['FF'] = 0
            potency = 340
        elif self.buffs['RC'] > 0:
            # use RC proc if available
            self.buffs['RC'] = 0
            potency = 280
        elif self.buffs['F'] > 0:
            # use combo if available
            self.buffs['F'] = 0
            # chance to gain proc
            if np.random.rand() > 0.5:
                self.buffs['FF'] = 30
            potency = 280
        else:
            # Basic Cascade GCD
            # chance to gain proc
            if np.random.rand() > 0.5:
                self.buffs['RC'] = 30
            # gain Fountain combo
            self.buffs['F'] = 30
            potency = 220

        # update next_event time by gcd length
        self.next_event += self.gcd_time

        return potency

    def update_time(self, current_time):
        # to-do #: move this to the BaseActor when buff handling between different actor types is sorted out #
        # adjust player timers based on how long it has been since the last update
        self.buffs = self.buffs - (current_time - self.last_time_check)
        # bring all negative timers back up to zero
        self.buffs = self.buffs.where(self.buffs >= 0, 0)

        # update last time check to now
        self.last_time_check = current_time

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.wpn_delay, self.ten)






