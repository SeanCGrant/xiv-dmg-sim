from .baseActor import BaseActor, ActionDC, BuffDC, DotDC
import pandas as pd
import numpy as np


# Paladin-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, *, player_id):
        # Paladin-specific values
        jobMod = 115  # TO-DO: check values
        trait = 120

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, player_id=player_id)

        # override auto potency
        self.auto_potency = 0  # TO-DO: check this value

        # pld specific resources
        self.resources = {}

        # pld personal buffs
        buffs = {}
        self.buffs.update(buffs)

        # pld actions
        actions = {'GCD-dummy': ActionDC('gcd', 0, self.gcd_time, self.gcd_time)}
        self.actions.update(actions)

        # pld dots
        dots = {}
        self.dots.update(dots)

    def choose_action(self):
        # determine current action, based on current buffs/procs

        if self.next_event == self.next_gcd:
            # use a GCD
            # use dummy GCD
            action = 'GCD-dummy'
            if self.allowed_action(action):
                return self.initiate_action(action)

        else:
            #oGCDs
            # no oGCDs on the dummy actor
            return self.go_to_gcd()

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay, self.ten,
                      player_id=self.player_id)






