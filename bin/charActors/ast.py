from .baseActor import BaseActor, ActionDC, BuffDC, DotDC
import pandas as pd
import numpy as np


# Astrologian-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, *, player_id):
        # Astrologian-specific values
        jobMod = 115  # TO-DO: check values
        trait = 120

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, player_id=player_id)

        # override auto potency
        self.auto_potency = 0  # TO-DO: check this value

        # ast specific resources
        self.resources = {}

        # ast personal buffs
        buffs = {}
        self.buffs.update(buffs)

        # ast actions
        actions = {'Divination': ActionDC('ogcd', 0, 120.0,
                                                buff_effect={'team': ['Divination']}),
                   'GCD-dummy': ActionDC('gcd', 0, self.gcd_time, self.gcd_time,
                                         cast_time=(1.5 - 0.5))}
        self.actions.update(actions)

        # ast dots
        dots = {'Combust3': DotDC(50, 30.0, self.buff_state())}
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
            # use Div first chance under Tech
            if self.buffs['Technical'].timer > 0:
                action = 'Divination'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            # no other oGCDs on the dummy actor
            return self.go_to_gcd()

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay, self.ten,
                      player_id=self.player_id)






