from .baseActor import BaseActor, ActionDC, ResourceDC, BuffDC, BuffSelector, BuffConditional, DotDC, Chance, Consume
import pandas as pd
import numpy as np


# Reaper-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, *, player_id, **kwargs):
        print(kwargs)
        self.kwargs = kwargs

        # RPR-specific values
        jobMod = 115
        trait = 100

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, player_id=player_id, **kwargs)

        # override auto potency
        self.auto_potency = 90  # TO-DO: check this value

        # Stickers
        self.stickers = {'Soulsow': False}
        # resources
        self.resources = {'Soul Gauge': ResourceDC(100), 'Shroud Gauge': ResourceDC(100),
                          'Lemure Shroud': ResourceDC(5), 'Void Shroud': ResourceDC(5),
                          'Immortal Sacrifice': ResourceDC(8)}

        # personal buffs
        buffs = {'Waxing Slice': BuffDC('logistic', 30.0), 'Infernal Slice': BuffDC('logistic', 30.0),
                 'Enhanced Gibbet': BuffDC('logistic', 60.0), 'Enhanced Void Reaping': BuffDC('logistic', 30.0),
                 'Soul Reaver 2': BuffDC('logistic', 30.0), 'Soul Reaver 1': BuffDC('logistic', 30.0),
                 'Shroud': BuffDC('logistic', 30.0),
                 'Deaths Design': BuffDC('dmg', 30.0, 1.10, extendable=True, max_time=60.0)}
        self.buffs.update(buffs)

        # actions
        actions = {'Slice': ActionDC('gcd', 320, self.gcd_time, self.gcd_time,
                                     buff_effect={'self': ['Waxing Slice']},
                                     resource={'Soul Gauge': 10}),
                   'Waxing Slice': ActionDC('gcd', 400, self.gcd_time, self.gcd_time,
                                            buff_effect={'self': ['Infernal Slice']},
                                            buff_removal=['Waxing Slice'],
                                            resource={'Soul Gauge': 10}),
                   'Infernal Slice': ActionDC('gcd', 500, self.gcd_time, self.gcd_time,
                                              buff_removal=['Infernal Slice'],
                                              resource={'Soul Gauge': 10}),
                   'Shadow of Death': ActionDC('gcd', 300, self.gcd_time, self.gcd_time,
                                               buff_effect={'self': ['Deaths Design']}),
                   'Harpe': ActionDC('gcd', 300, self.gcd_time, self.gcd_time,
                                     cast_time=1.3 - 0.5),
                   'Soulsow': ActionDC('gcd', 0, self.gcd_time, self.gcd_time,
                                        cast_time=(5.0 - 0.5),
                                        sticker_gain=['Soulsow']),
                   'Harvest Moon': ActionDC('gcd', 600, self.gcd_time, self.gcd_time,
                                            sticker_removal=['Soulsow']),
                   'Plentiful Harvest': ActionDC('gcd', self.scale_potency(720, 40, 'Immortal Sacrifice', 1),
                                                 self.gcd_time, self.gcd_time,
                                                 resource={'Immortal Sacrifice': Consume(1), 'Shroud Gauge': 50}),
                   # Gibbet and Unveiled Gibbet are encompassing the whole Gibbet/Gallows system here, in practice
                   'Gibbet': ActionDC('gcd', self.combo_potency([460, 520], 'Enhanced Gibbet'),
                                      self.gcd_time, self.gcd_time,
                                      buff_effect={'self': ['Enhanced Gibbet']},
                                      buff_removal=[['Soul Reaver 2', 'Soul Reaver 1']],
                                      resource={'Shroud Gauge': 10}),
                   'Unveiled Gibbet': ActionDC('ogcd', self.combo_potency([340, 400], 'Enhanced Gibbet'), 1.0,
                                               buff_effect={'self': ['Soul Reaver 1']},
                                               buff_removal_opt=['Soul Reaver 2'],
                                               resource={'Soul Gauge': -50}),
                   'Gluttony': ActionDC('ogcd', 500, 60.0,
                                        buff_effect={'self': ['Soul Reaver 2', 'Soul Reaver 1']}),
                   'Soul Slice': ActionDC('ogcd', 460, 1.0,
                                          max_charges=2,
                                          charge_time=30.0,
                                          resource={'Soul Gauge': 50}),
                   # TO-DO: Make it so that Circle of Sacrifice is consumed upon giving a stack
                   'Arcane Circle': ActionDC('ogcd', 0, 120.0,
                                             buff_effect={'team': ['Arcane Circle', 'Circle of Sacrifice']}),
                   # Shroud Cycle #
                   'Enshroud': ActionDC('ogcd', 0, 15.0,
                                        buff_effect={'self': ['Shroud']},
                                        resource={'Shroud Gauge': -50, 'Lemure Shroud': 5}),
                   'Void Reaping': ActionDC('gcd', self.combo_potency([460, 520], 'Enhanced Void Reaping'), 1.5, 1.5,
                                            buff_effect={'self': ['Enhanced Void Reaping']},
                                            required_buff=['Shroud'],
                                            resource={'Void Shroud': 1, 'Lemure Shroud': -1}),
                   'Lemures Slice': ActionDC('ogcd', 220, 1.0,
                                             required_buff=['Shroud'],
                                             resource={'Void Shroud': -2}),
                   'Communio': ActionDC('gcd', 1100, self.gcd_time, self.gcd_time,
                                        cast_time=(1.3 - 0.5),
                                        buff_removal=['Shroud'],
                                        resource={'Lemure Shroud': Consume(1), 'Void Shroud': Consume(0)})
                   }
        self.actions.update(actions)

        # dots
        dots = {}
        self.dots.update(dots)

    def choose_action(self):
        # determine current action, based on current buffs/procs

        if self.next_event == self.next_gcd:
            # Prepull
            if self.next_event < 0.0:
                # Use Soulsow before combat
                current_time = self.next_event
                self.initiate_action('Soulsow')
                self.next_gcd = 0.0
                self.next_event = self.next_gcd
                return 'Soulsow', -current_time

            # use a GCD
            # Keep up Death's Design
            if self.buffs['Deaths Design'].timer < 2.5:
                action = 'Shadow of Death'
                if self.allowed_action(action):
                    return self.initiate_action(action)

            # Use Gibbet when a Soul Reaver stack is available
            if self.buffs['Soul Reaver 1'].active():
                action = 'Gibbet'
                if self.allowed_action(action):
                    return self.initiate_action(action)

            # Use shroud abilities when in Shroud
            # Always finish with Communio
            if self.resources['Lemure Shroud'].amount == 1:
                action = 'Communio'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            action = 'Void Reaping'
            if self.allowed_action(action):
                return self.initiate_action(action)

            # Use Plentiful Harvest if available
            action = 'Plentiful Harvest'
            if self.allowed_action(action):
                return self.initiate_action(action)

            # Basic Combo
            action = 'Infernal Slice'
            if self.allowed_action(action):
                return self.initiate_action(action)
            action = 'Waxing Slice'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Mix in some bonus Death's Design when free
            if self.buffs['Deaths Design'].timer < 30.0:
                action = 'Shadow of Death'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            action = 'Slice'
            if self.allowed_action(action):
                return self.initiate_action(action)

        else:
            # consider using oGCDs
            if round(self.next_event + self.anim_lock, 3) > self.next_gcd:
                # don't clip gcd
                return self.go_to_gcd()

            # Use Shroud abilities in Shroud
            action = 'Lemures Slice'
            if self.allowed_action(action):
                return self.initiate_action(action)

            action = 'Arcane Circle'
            if self.allowed_action(action):
                return self.initiate_action(action)

            action = 'Enshroud'
            if self.allowed_action(action):
                return self.initiate_action(action)

            action = 'Gluttony'
            if self.allowed_action(action):
                return self.initiate_action(action)
            action = 'Unveiled Gibbet'
            if self.allowed_action(action):
                return self.initiate_action(action)

            # doing nothing for this oGCD
            return self.pass_ogcd()

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay,
                      player_id=self.player_id, **self.kwargs)






