from .baseActor import BaseActor, ActionDC, BuffDC, DotDC
import pandas as pd
import numpy as np


# Dragoon-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, *, player_id):
        # Dragoon-specific values
        jobMod = 115  # TO-DO: check values
        trait = 120

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, player_id=player_id)

        # override auto potency
        self.auto_potency = 0  # TO-DO: check this value

        # drg specific resources
        self.resources = {}

        # drg personal buffs
        buffs = {'Shifu': BuffDC('spd', 1000.0, 0.13)}
        self.buffs.update(buffs)

        # drg actions
        actions = {'BattleLitany': ActionDC('ogcd', 0, 120.0,
                                            buff_effect={'team': ['BattleLitany']}),
                   'GCD-dummy': ActionDC('gcd', 0, self.gcd_time, self.gcd_time)}
        self.actions.update(actions)

        # drg dots
        dots = {'ChaosThrust': DotDC(40, 24.0, self.buff_state())}
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
            # use Battle Lit first chance under Tech
            if self.buffs['Technical'].timer > 0:
                action = 'BattleLitany'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            # no other oGCDs on the dummy actor
            return self.pass_ogcd()

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay, self.ten,
                      player_id=self.player_id)






