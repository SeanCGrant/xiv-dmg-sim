from .baseActor import (BaseActor, ActionDC, ResourceDC, TimedResourceDC, BuffDC, BuffSelector, DotDC, Chance, Consume,
                        piety_to_mp)
import pandas as pd
import numpy as np


# Sage-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, *, piety=390, player_id, **kwargs):

        self.kwargs = kwargs

        # Sage-specific values
        jobMod = 115
        trait = 130

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, player_id=player_id, **kwargs)

        # Adjust mp tick based on piety
        self.mp_tick = 200 + piety_to_mp(piety)

        # override auto potency
        self.auto_potency = 1  # TO-DO: check this value

        # job specific resources
        self.resources = {'addersgal': TimedResourceDC(3, charge_time=20.0), 'addersting': ResourceDC(3),
                          'mp': ResourceDC(max=10000, amount=10000)}

        # personal buffs
        buffs = {'Lucid Dreaming': BuffDC('logistic', 21.0)}
        self.buffs.update(buffs)

        # actions
        actions = {'DosisIII': ActionDC('gcd', 330, self.gcd_time, self.gcd_time,
                                        cast_time=1.5,
                                        resource={'mp': -400}),
                   'EukrasianDosisIII': ActionDC('gcd', 0, 2.5, 2.5,
                                                 cast_time=1.0,
                                                 dot_effect='EukrasianDosisIII',
                                                 resource={'mp': -400}),
                   'PhlegmaIII': ActionDC('gcd', 600, self.gcd_time, self.gcd_time,
                                          max_charges=2,
                                          charge_time=40.0,
                                          resource={'mp': -400}),
                   'Pneuma': ActionDC('gcd', 330, self.gcd_time, self.gcd_time,
                                      cast_time=1.5,
                                      resource={'mp': -700}),
                   'ToxiconII': ActionDC('gcd', 330, self.gcd_time, self.gcd_time,
                                         buff_removal=['FlourishingRC'],
                                         resource={'addersting': -1}),
                   'Druochole': ActionDC('ogcd', 0, 1.0,
                                         resource={'addersgal': -1, 'mp': 700}),
                   'Lucid Dreaming': ActionDC('ogcd', 0, 60.0,
                                              buff_effect={'self': ['Lucid Dreaming']})}
        self.actions.update(actions)

        # dots
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
            # Cover no allowed actions (no mp, for instance)
            return self.go_to_tick()
        else:
            # consider using oGCDs

            if round(self.next_event + self.anim_lock, 3) > self.next_gcd:
                # don't clip gcd
                return self.go_to_gcd()

            # Use Lucid when available
            action = 'Lucid Dreaming'
            if self.allowed_action(action):
                return self.initiate_action(action)

            # Use an addersgal stack if capped
            if self.resources['addersgal'].amount == 3:
                action = 'Druochole'
                if self.allowed_action(action):
                    return self.initiate_action(action)

            # Jump to the next gcd if nothing else
            return self.go_to_gcd()

    def execute_actor_tick(self):
        # Execute the base function
        BaseActor.execute_actor_tick(self)

        # Add mp
        # Base actor mp tick
        mp_tick = self.mp_tick
        # Check for Lucid
        if self.buffs['Lucid Dreaming'].active():
            # Add the Lucid value
            mp_tick += 550

        self.add_resource('mp', mp_tick)

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay,
                      player_id=self.player_id, **self.kwargs)






