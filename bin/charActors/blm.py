from .baseActor import BaseActor, ActionDC, BuffDC, DotDC
import pandas as pd
import numpy as np


# Black Mage-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, *, player_id):
        # Black Mage-specific values
        jobMod = 115  # TO-DO: check values
        trait = 120

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, player_id=player_id)

        # override auto potency
        self.auto_potency = 0  # TO-DO: check this value

        # blm specific resources
        self.resources = {}

        # blm personal buffs
        buffs = {}
        self.buffs.update(buffs)

        # blm actions
        actions = {'GCD-dummy': ActionDC('gcd', 0, self.gcd_time, self.gcd_time,
                                         cast_time=(self.gcd_time - 0.5))}
        self.actions.update(actions)

        # blm dots
        dots = {'Thunder3': DotDC(35, 30.0, self.buff_state())}
        self.dots.update(dots)

    def choose_action(self):
        # determine current action, based on current buffs/procs

        if self.next_event == self.next_gcd:
            # use a GCD

            # Prepull
            if self.next_event < 0.0:
                # No prepull
                self.next_gcd = 0.0
                self.next_event = self.next_gcd
                return None, 0.0

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






