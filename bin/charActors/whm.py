from .baseActor import BaseActor, ActionDC, BuffDC, DotDC, ResourceDC, TimedResourceDC, piety_to_mp
import pandas as pd
import numpy as np


# White Mage-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, *, piety=390, player_id, **kwargs):

        self.kwargs = kwargs

        # White Mage-specific values
        jobMod = 115
        trait = 130

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, player_id=player_id, **kwargs)

        # Adjust mp tick based on piety
        self.mp_tick = 200 + piety_to_mp(piety)

        # override auto potency
        self.auto_potency = 1 * (self.wpn_delay / 3.0)  # TO-DO: check this value

        # whm specific resources
        self.resources = {'Lily': TimedResourceDC(3, amount=0, charge_time=20.0), 'Blood Lily': ResourceDC(3),
                          'mp': ResourceDC(max=10000, amount=10000)}

        # whm personal buffs
        buffs = {"Presence of Mind": BuffDC('spd', 15.0, 0.2), 'Lucid Dreaming': BuffDC('logistic', 21.0)}
        self.buffs.update(buffs)

        # whm actions
        actions = {'GCD-dummy': ActionDC('gcd', 0, self.gcd_time, self.gcd_time,
                                         cast_time=(1.5 - 0.5)),
                   'Glare III': ActionDC('gcd', 310, self.gcd_time, self.gcd_time,
                                         cast_time=(1.5 - 0.5),
                                         resource={'mp': -400}),
                   'Dia': ActionDC('gcd', 60, self.gcd_time, self.gcd_time,
                                   dot_effect='Dia',
                                   resource={'mp': -400}),
                   'Afflatus Rapture': ActionDC('gcd', 0, self.gcd_time, self.gcd_time,
                                                resource={'Lily': -1, 'Blood Lily': 1}),
                   'Afflatus Misery': ActionDC('gcd', 1240, self.gcd_time, self.gcd_time,
                                               resource={'Blood Lily': -3}),
                   'Assize': ActionDC('ogcd', 400, 40.0,
                                      resource={'mp': 500}),
                   'Presence of Mind': ActionDC('ogcd', 0, 120.0,
                                                buff_effect={'self': ['Presence of Mind']}),
                   'Lucid Dreaming': ActionDC('ogcd', 0, 60.0,
                                              buff_effect={'self': ['Lucid Dreaming']})}
        self.actions.update(actions)

        # whm dots
        dots = {'Dia': DotDC(60, 30.0, self.buff_state())}
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
            if self.dots['Dia'].timer <= 1.5:
                action = 'Dia'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            # Use Rapture and Misery at will for now
            action = 'Afflatus Misery'
            if self.allowed_action(action):
                return self.initiate_action(action)
            action = 'Afflatus Rapture'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Use Glare otherwise
            action = 'Glare III'
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

            # Use Assize at will
            action = 'Assize'
            if self.allowed_action(action):
                return self.initiate_action(action)

            # Use PoM
            action = 'Presence of Mind'
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






