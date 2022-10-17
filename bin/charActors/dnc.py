from .baseActor import BaseActor, ActionDC, BuffDC, DotDC
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

        self.resources = {'esprit': 0, 'feathers': 0}  # track personal resources
        buffs = {'F': BuffDC('logistic', 30.0, 0.0, 0.0), 'RC': BuffDC('logistic', 30.0, 0.0, 0.0),
                 'FF': BuffDC('logistic', 30.0, 0.0, 0.0), 'testBuff': BuffDC('dmg', 10, 0.0, 3.0),
                 'testTeam': BuffDC('crit', 2.5, 0.0, 0.2)}
        self.buffs.update(buffs)
        actions = {'Cascade': ActionDC('gcd', 220, self.gcd_time, 0.0, ('self', 'F'), dot_effect='TestDot'),
                   'Fountain': ActionDC('gcd', 280, self.gcd_time),
                   'ReverseCascade': ActionDC('gcd', 280, self.gcd_time, buff_effect=('team', 'testTeam')),
                   'Fountainfall': ActionDC('gcd', 340, self.gcd_time, 0.0, ('self', 'testBuff'))}
        self.actions.update(actions)
        dots = {'TestDot': DotDC(50, 15, self.buff_state())}
        self.dots.update(dots)

    def choose_action(self):
        # determine current action, based on current buffs/procs
        if self.buffs['FF'].timer > 0:
            # use FF proc if available first
            # remove the proc
            self.buffs['FF'].timer = 0
            # use the ability
            return self.perform_action('Fountainfall')
        elif self.buffs['RC'].timer > 0:
            # use RC proc if available
            # remove the proc
            self.buffs['RC'].timer = 0
            # use the ability
            return self.perform_action('ReverseCascade')
        elif self.buffs['F'].timer > 0:
            # use combo if available
            # chance to gain proc
            if np.random.rand() > 0.5:
                self.apply_buff('FF')
            # remove the combo
            self.buffs['F'].timer = 0
            # use the action
            return self.perform_action('Fountain')
        else:
            # Basic Cascade GCD
            # chance to gain proc
            if np.random.rand() > 0.5:
                self.apply_buff('RC')
            return self.perform_action('Cascade')

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.wpn_delay, self.ten)






