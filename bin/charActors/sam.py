from .baseActor import BaseActor, ActionDC, BuffDC, DotDC
import pandas as pd
import numpy as np


# Samurai-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, *, player_id):
        # Samurai-specific values
        jobMod = 115  # TO-DO: check values
        trait = 120

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, player_id=player_id)

        # override auto potency
        self.auto_potency = 0  # TO-DO: check this value

        # sam specific resources
        self.resources = {}

        # sam personal buffs
        buffs = {'Shifu': BuffDC('spd', 1000.0, 0.13)}
        self.buffs.update(buffs)

        # sam actions
        actions = {'Shifu-dummy': ActionDC('gcd', 0, self.gcd_time, self.gcd_time, 0.0,
                                           buff_effect={'self': ['Shifu']}),
                   'GCD-dummy': ActionDC('gcd', 0, self.gcd_time, self.gcd_time)}
        self.actions.update(actions)

        # sam dots
        dots = {'Higanbana': DotDC(45, 60.0, self.buff_state())}
        self.dots.update(dots)

    def choose_action(self):
        # determine current action, based on current buffs/procs

        if self.next_event == self.next_gcd:
            # use a GCD
            if self.next_event == 0.0:
                # open fight with Shifu
                return self.initiate_action('Shifu-dummy')
            else:
                # use dummy GCD
                action = 'GCD-dummy'
                if self.allowed_action(action):
                    return self.initiate_action(action)

        else:
            # no oGCDs on the dummy actor
            return self.go_to_gcd()

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay, self.ten,
                      player_id=self.player_id)






