from .baseActor import BaseActor, ActionDC, ResourceDC, BuffDC, BuffSelector, BuffConditional, DotDC, Chance, Consume
import pandas as pd
import numpy as np


# Machinist-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, *, player_id, **kwargs):
        print(kwargs)
        self.kwargs = kwargs

        # MCH-specific values
        jobMod = 115
        trait = 120

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, player_id=player_id, **kwargs)

        # override auto potency
        self.auto_potency = 80 * (self.wpn_delay / 3.0)  # TO-DO: check this value

        # resources
        self.resources = {'Heat Gauge': ResourceDC(100), 'Battery Gauge': ResourceDC(100)}

        # personal buffs
        buffs = {'Heated Slug': BuffDC('logistic', 30.0), 'Heated Clean': BuffDC('logistic', 30.0),
                 'Hypercharge': BuffDC('logistic', 10.0), 'Overheat 5': BuffDC('logistic', 10.0),
                 'Overheat 4': BuffDC('logistic', 10.0), 'Overheat 3': BuffDC('logistic', 10.0),
                 'Overheat 2': BuffDC('logistic', 10.0), 'Overheat 1': BuffDC('logistic', 10.0),
                 'Reassemble': BuffDC('logistic', 5.0)}
        self.buffs.update(buffs)

        # actions
        actions = {'Heated Split Shot': ActionDC('gcd', self.combo_potency([200, 200+20], 'Overheat 1'),
                                                 self.gcd_time, self.gcd_time,
                                                 buff_effect={'self': ['Heated Slug']},
                                                 resource={'Heat Gauge': 5},
                                                 buff_removal_opt=[['Overheat 5', 'Overheat 4', 'Overheat 3',
                                                                    'Overheat 2', 'Overheat 1']]),
                   'Heated Slug Shot': ActionDC('gcd', self.combo_potency([300, 300+20], 'Overheat 1'),
                                                self.gcd_time, self.gcd_time,
                                                buff_effect={'self': ['Heated Clean']},
                                                buff_removal=['Heated Slug'],
                                                resource={'Heat Gauge': 5},
                                                buff_removal_opt=[['Overheat 5', 'Overheat 4', 'Overheat 3',
                                                                   'Overheat 2', 'Overheat 1']]
                                                ),
                   'Heated Clean Shot': ActionDC('gcd', self.combo_potency([380, 380+20], 'Overheat 1'),
                                                 self.gcd_time, self.gcd_time,
                                                 resource={'Heat Gauge': 5, 'Battery Gauge': 10},
                                                 buff_removal=['Heated Clean'],
                                                 buff_removal_opt=[['Overheat 5', 'Overheat 4', 'Overheat 3',
                                                                    'Overheat 2', 'Overheat 1']]
                                                 ),
                   'Drill': ActionDC('gcd', self.combo_potency([600, 600+20], 'Overheat 1'),
                                     8*self.gcd_time, self.gcd_time,
                                     buff_removal_opt=['Reassemble', ['Overheat 5', 'Overheat 4', 'Overheat 3',
                                                       'Overheat 2', 'Overheat 1']],
                                     autocrit=BuffConditional(self, ['Reassemble']),
                                     autodhit=BuffConditional(self, ['Reassemble'])),
                   'Air Anchor': ActionDC('gcd', self.combo_potency([600, 600+20], 'Overheat 1'),
                                          16*self.gcd_time, self.gcd_time,
                                          resource={'Battery Gauge': 20},
                                          buff_removal_opt=['Reassemble', ['Overheat 5', 'Overheat 4', 'Overheat 3',
                                                            'Overheat 2', 'Overheat 1']],
                                          autocrit=BuffConditional(self, ['Reassemble']),
                                          autodhit=BuffConditional(self, ['Reassemble'])),
                   'Chainsaw': ActionDC('gcd', 600, 24*self.gcd_time, self.gcd_time,
                                        resource={'Battery Gauge': 20},
                                        buff_removal_opt=['Reassemble'],
                                        autocrit=BuffConditional(self, ['Reassemble']),
                                        autodhit=BuffConditional(self, ['Reassemble'])),
                   'Heat Blast': ActionDC('gcd', 200+20, 1.5, 1.5,
                                          buff_removal=[['Overheat 5', 'Overheat 4', 'Overheat 3',
                                                         'Overheat 2', 'Overheat 1']],
                                          additional_effect=[self._heat_blast_func]),
                   'Gauss Round': ActionDC('ogcd', 130, 1.0,
                                           max_charges=3,
                                           charge_time=30.0),
                   'Ricochet': ActionDC('ogcd', 130, 1.0,
                                        max_charges=3,
                                        charge_time=30.0),
                   'Reassemble': ActionDC('ogcd', 0, 55.0,
                                          buff_effect={'self': ['Reassemble']}),
                   'Barrel Stabilizer': ActionDC('ogcd', 0, 120.0,
                                                 resource={'Heat Gauge': 50}),
                   'Hypercharge': ActionDC('ogcd', 0, 10.0,
                                           buff_effect={'self': ['Overheat 5', 'Overheat 4', 'Overheat 3',
                                                                 'Overheat 2', 'Overheat 1']},
                                           resource={'Heat Gauge': -50}),
                   # TO-DO: Wildfire currently assumes six gcds get used (full damage), and it does the damage upfront
                   'Wildfire': ActionDC('ogcd', 240*6, 120.0,
                                        delay_on_perform=0.0,
                                        anticrit=True,
                                        antidhit=True),
                   # TO-DO: Queen currently assumes all damage drops six seconds later, and all buffs apply (dragon sight does not)
                   'Automaton Queen': ActionDC('ogcd', self.scale_potency(0.89 * (5*120 + 340 + 390),
                                                                          0.89 * (5*120 + 340 + 390) / 50,
                                                                          'Battery Gauge', 50), 6.0,
                                               resource={'Battery Gauge': Consume(50)},
                                               delay_on_perform=6.0)
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
                # No prepull
                self.next_gcd = 0.0
                self.next_event = self.next_gcd
                return None, 0.0

            # use a GCD
            # In Hypercharge Window
            if self.buffs['Overheat 1'].active():
                # Can sneak in a Chainsaw if up
                action = 'Chainsaw'
                if self.allowed_action(action):
                    return self.initiate_action(action)
                # Typical Use
                action = 'Heat Blast'
                if self.allowed_action(action):
                    return self.initiate_action(action)

            # Use tools first
            action = 'Air Anchor'
            if self.allowed_action(action):
                return self.initiate_action(action)
            action = 'Drill'
            if self.allowed_action(action):
                return self.initiate_action(action)
            action = 'Chainsaw'
            if self.allowed_action(action):
                return self.initiate_action(action)

            # Basic GCD combo
            action = 'Heated Clean Shot'
            if self.allowed_action(action):
                return self.initiate_action(action)
            action = 'Heated Slug Shot'
            if self.allowed_action(action):
                return self.initiate_action(action)
            action = 'Heated Split Shot'
            if self.allowed_action(action):
                return self.initiate_action(action)

        else:
            # consider using oGCDs
            if round(self.next_event + self.anim_lock, 3) > self.next_gcd:
                # don't clip gcd
                return self.go_to_gcd()

            # Don't overcap charges
            if self.actions['Gauss Round'].charge_count == 3:
                action = 'Gauss Round'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            if self.actions['Ricochet'].charge_count == 3:
                action = 'Ricochet'
                if self.allowed_action(action):
                    return self.initiate_action(action)

            # Use charges quickly in Hypercharge window
            if self.buffs['Overheat 1'].active():
                if self.actions['Gauss Round'].charge_count > self.actions['Ricochet'].charge_count:
                    action = 'Gauss Round'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                else:
                    action = 'Ricochet'
                    if self.allowed_action(action):
                        return self.initiate_action(action)

            # Use Reassemble if a tool is coming up
            if (self.actions['Drill'].cooldown < (self.next_gcd - self.last_time_check)) | \
                    (self.actions['Air Anchor'].cooldown < (self.next_gcd - self.last_time_check)) | \
                    (self.actions['Chainsaw'].cooldown < (self.next_gcd - self.last_time_check)):
                action = 'Reassemble'
                if self.allowed_action(action):
                    return self.initiate_action(action)

            # Use Barrel Stabilizer if below 50 heat
            if self.resources['Heat Gauge'].amount < 50:
                action = 'Barrel Stabilizer'
                if self.allowed_action(action):
                    return self.initiate_action(action)

            # Use Wildfire on cooldown
            # I understand I haven't forced usage with Hypercharge here, which is flawed
            action = 'Wildfire'
            if self.allowed_action(action):
                return self.initiate_action(action)

            # Use Hypercharge freely
            action = 'Hypercharge'
            if self.allowed_action(action):
                return self.initiate_action(action)

            # Use Queen at 80 battery
            if self.resources['Battery Gauge'].amount >= 80:
                action = 'Automaton Queen'
                if self.allowed_action(action):
                    return self.initiate_action(action)

            # doing nothing for this oGCD
            return self.pass_ogcd()

    def _heat_blast_func(self):
        # Lower cooldown of Gauss Round and Ricochet
        self.actions['Gauss Round'].update_time(15.0)
        self.actions['Ricochet'].update_time(15.0)

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay,
                      player_id=self.player_id, **self.kwargs)






