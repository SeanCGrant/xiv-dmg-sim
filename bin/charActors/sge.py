from .baseActor import BaseActor, ActionDC, ResourceDC, TimedResourceDC, BuffDC, BuffSelector, DotDC, Chance, Consume
import pandas as pd
import numpy as np


# Sage-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, *, player_id, **kwargs):

        self.kwargs = kwargs

        # Sage-specific values
        jobMod = 115
        trait = 130

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, player_id=player_id, **kwargs)

        # override auto potency
        self.auto_potency = 1 * (self.wpn_delay / 3.0)  # TO-DO: check this value

        # sge specific resources
        self.resources = {'addersgal': TimedResourceDC(3, charge_time=20.0), 'addersting': ResourceDC(3)}

        # sge personal buffs
        buffs = {}
        self.buffs.update(buffs)

        # dnc actions
        actions = {'DosisIII': ActionDC('gcd', 330, self.gcd_time, self.gcd_time,
                                        cast_time=1.5),
                   'EukrasianDosisIII': ActionDC('gcd', 0, 2.5, 2.5,
                                                 cast_time=1.0,
                                                 dot_effect='EukrasianDosisIII'),
                   'PhlegmaIII': ActionDC('gcd', 600, self.gcd_time, self.gcd_time,
                                          max_charges=2,
                                          charge_time=40.0),
                   'Pneuma': ActionDC('gcd', 330, self.gcd_time, self.gcd_time,
                                      cast_time=1.5),
                   'ToxiconII': ActionDC('gcd', 330, self.gcd_time, self.gcd_time,
                                         buff_removal=['FlourishingRC'],
                                         resource={'addersting': -1})}
        self.actions.update(actions)

        # dnc dots
        dots = {'EukrasianDosisIII': DotDC(70, 30.0)}
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

            # Reapply DoT if about to fall off
            if self.dots['EukrasianDosisIII'].timer <= 1.5:
                action = 'EukrasianDosisIII'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            # Use Phlegma at will for now
            action = 'PhlegmaIII'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Use Dosis otherwise
            action = 'DosisIII'
            if self.allowed_action(action):
                return self.initiate_action(action)
        else:
            # consider using oGCDs
            return self.go_to_gcd()



    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay,
                      player_id=self.player_id, **self.kwargs)






