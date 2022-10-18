from .baseActor import BaseActor, ActionDC, BuffDC, DotDC
import pandas as pd
import numpy as np


# dancer-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400):
        # Dancer-specific values
        jobMod = 115
        trait = 120

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400)

        # override auto potency
        self.auto_potency = 80  # check this value

        self.resources = {'esprit': 0, 'feathers': 0}  # track personal resources
        buffs = {'F': BuffDC('logistic', 30.0, 0.0, 0.0), 'RC': BuffDC('logistic', 30.0, 0.0, 0.0),
                 'FF': BuffDC('logistic', 30.0, 0.0, 0.0),
                 'Standard': BuffDC('dmg', 60.0, 0.0, 1.05),
                 'testSelf': BuffDC('dmg', 10, 0.0, 3.0), 'testTeam': BuffDC('crit', 2.5, 0.0, 0.2)}
        self.buffs.update(buffs)
        actions = {'Cascade': ActionDC('gcd', 220, self.gcd_time, self.gcd_time, 0.0,
                                       buff_effect={'self': ['F', ('RC', 0.5)]},
                                       resource={'esprit': 5},
                                       dot_effect='TestDot'),
                   'Fountain': ActionDC('gcd', 280, self.gcd_time, self.gcd_time,
                                        buff_effect={'self': [('FF', 0.5)]},
                                        buff_removal=['F'],
                                        resource={'esprit': 5}),
                   'ReverseCascade': ActionDC('gcd', 280, self.gcd_time, self.gcd_time,
                                              buff_effect={'team': ['testTeam']},
                                              buff_removal=['RC'],
                                              resource={'esprit': 10, 'feathers': (1, 0.5)}),
                   'Fountainfall': ActionDC('gcd', 340, self.gcd_time, self.gcd_time,
                                            buff_effect={'self': ['testSelf']},
                                            buff_removal=['FF'],
                                            resource={'esprit': 10, 'feathers': (1, 0.5)}),
                   'SaberDance': ActionDC('gcd', 480, self.gcd_time, self.gcd_time,
                                          resource={'esprit': -50}),
                   'StandardStep': ActionDC('gcd', 720, 30.0, 5.0,
                                            buff_effect={'self': ['Standard']}),
                   'FeatherUse': ActionDC('gcd', 10, self.gcd_time, self.gcd_time,
                                          resource={'feathers': -4})}
        self.actions.update(actions)
        dots = {'TestDot': DotDC(50, 15, self.buff_state())}
        self.dots.update(dots)

    def choose_action(self):
        # determine current action, based on current buffs/procs
        if self.actions['StandardStep'].cooldown <= 0:
            # use Standard every time it's up
            return self.perform_action('StandardStep')
        if self.resources['feathers'] >= 4:
            return self.perform_action('FeatherUse')
        if self.resources['esprit'] > 50:
            # use SaberDance
            return self.perform_action('SaberDance')
        if self.buffs['FF'].timer > 0:
            # use FF proc if available first
            return self.perform_action('Fountainfall')
        elif self.buffs['RC'].timer > 0:
            # use RC proc if available
            return self.perform_action('ReverseCascade')
        elif self.buffs['F'].timer > 0:
            # use combo if available
            return self.perform_action('Fountain')
        else:
            # Basic Cascade GCD
            return self.perform_action('Cascade')

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay, self.ten)






