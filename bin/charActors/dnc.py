from .baseActor import BaseActor, ActionDC, ResourceDC, BuffDC, BuffSelector, DotDC, Chance, Consume
import pandas as pd
import numpy as np


# dancer-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, *, player_id, partner, **kwargs):
        print(kwargs)
        self.kwargs = kwargs

        # Dancer-specific values
        jobMod = 115
        trait = 120

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, player_id=player_id, **kwargs)

        # override auto potency
        self.auto_potency = 90 * (self.wpn_delay / 3.0)  # TO-DO: check this value

        # dnc specific resources
        self.resources = {'esprit': ResourceDC(100), 'feathers': ResourceDC(4)}

        # dnc personal buffs
        buffs = {'F': BuffDC('logistic', 30.0), 'RC': BuffDC('logistic', 30.0),
                 'FF': BuffDC('logistic', 30.0), 'Tillana': BuffDC('logistic', 30.0),
                 'Starfall': BuffDC('logistic', 20.0), 'Threefold': BuffDC('logistic', 30.0),
                 'Fourfold': BuffDC('logistic', 30.0), 'FlourishingRC': BuffDC('logistic', 30.0),
                 'FlourishingFF': BuffDC('logistic', 30.0)}
        self.buffs.update(buffs)

        # dnc needs a buff target (dance partner)
        self.buff_target = partner

        # dnc actions
        actions = {'Cascade': ActionDC('gcd', 220, self.gcd_time, self.gcd_time, 0.0,
                                       buff_effect={'self': ['F', Chance('RC', 0.5)]},
                                       resource={'esprit': 5}),
                   ##### Two Options for Combo Actions: #####
                   ## First: Two separate actions that are called separately.
                   # This has advantages in simplifying rotation logic, particularly when an uncombo'd action is almost
                   # never used.
                   # Combo'd version
                   'Fountain': ActionDC('gcd', 280, self.gcd_time, self.gcd_time,
                                        buff_effect={'self': [Chance('FF', 0.5)]},
                                        buff_removal=['F'],
                                        resource={'esprit': 5}),
                   # Uncombo'd version - must be asked for explicitly
                   'unFountain': ActionDC('gcd', 100, self.gcd_time, self.gcd_time,
                                          resource={'esprit': 5}),
                   ## Second: Create one Action that determines the potency based on whether the combo buff is present.
                   # This gets contained in a single action that can be called, and automatically handles the potency.
                   # But requires that all instances of rotation logic check for the combo buff as necessary.
                   # Example here (unused):
                   # 'Fountain': ActionDC('gcd', self.combo_potency([100, 280], 'F'), self.gcd_time, self.gcd_time,
                   #                      buff_effect={'self': [Chance('FF', 0.5)]},
                   #                      #buff_removal=['F'],
                   #                      resource={'esprit': 5}),
                   'ReverseCascade': ActionDC('gcd', 280, self.gcd_time, self.gcd_time,
                                              buff_removal=['RC'],
                                              resource={'esprit': 10, 'feathers': Chance(1, 0.5)}),
                   'FlourishingReverseCascade': ActionDC('gcd', 280, self.gcd_time, self.gcd_time,
                                                         buff_removal=['FlourishingRC'],
                                                         resource={'esprit': 10, 'feathers': Chance(1, 0.5)}),
                   'Fountainfall': ActionDC('gcd', 340, self.gcd_time, self.gcd_time,
                                            buff_removal=['FF'],
                                            resource={'esprit': 10, 'feathers': Chance(1, 0.5)}),
                   'FlourishingFountainfall': ActionDC('gcd', 340, self.gcd_time, self.gcd_time,
                                                       buff_removal=['FlourishingFF'],
                                                       resource={'esprit': 10, 'feathers': Chance(1, 0.5)}),
                   'SaberDance': ActionDC('gcd', 480, self.gcd_time, self.gcd_time,
                                          resource={'esprit': -50}),
                   'StandardStep': ActionDC('gcd', 720, 30.0, 5.0,
                                            spd_adjusted=False,
                                            cast_time=3.5,
                                            buff_effect={'self': ['Standard'],
                                                         'target': ['Standard', 'StandardEsprit']}),
                   'TechnicalStep': ActionDC('gcd', 1200, 120.0, 7.0,
                                             spd_adjusted=False,
                                             cast_time=5.5,
                                             buff_effect={'self': ['Tillana'], 'team': ['Technical', 'TechEsprit']}),
                   'Tillana': ActionDC('gcd', 360, 1.5, 1.5,
                                       spd_adjusted=False,
                                       buff_effect={'self': ['Standard'], 'target': ['Standard']},
                                       buff_removal=['Tillana']),
                   'Starfall': ActionDC('gcd', 600, self.gcd_time, self.gcd_time,
                                        autocrit=True,
                                        autodhit=True,
                                        buff_removal=['Starfall']),
                   'FanDance1': ActionDC('ogcd', 150, 1.0,
                                         resource={'feathers': -1},
                                         buff_effect={'self': [Chance('Threefold', 0.5)]}),
                   'FanDance3': ActionDC('ogcd', 200, 1.0,
                                         buff_removal=['Threefold']),
                   'FanDance4': ActionDC('ogcd', 300, 1.0,
                                         buff_removal=['Fourfold']),
                   'Flourish': ActionDC('ogcd', 0, 60.0,
                                        buff_effect={'self': ['FlourishingRC', 'FlourishingFF',
                                                              'Threefold', 'Fourfold']}),
                   'Devilment': ActionDC('ogcd', 0, 120.0,
                                         buff_effect={'self': ['Devilment_crit', 'Devilment_dhit', 'Starfall'],
                                                      'target': ['Devilment_crit', 'Devilment_dhit']}),
                   'Charger': ActionDC('ogcd', 10, 1.0,
                                       max_charges=3, charge_time=30.0)}
        self.actions.update(actions)

        # dnc dots
        dots = {}
        self.dots.update(dots)

    def choose_action(self):
        # determine current action, based on current buffs/procs

        if self.next_event == self.next_gcd:
            # Prepull
            if self.next_event < 0.0:
                # Jump to -15 sec if needed
                if self.next_event < -15.0:
                    # Wait for 15 sec before pull
                    self.next_gcd = -15.0
                    self.next_event = self.next_gcd
                    return None, 0.0
                if self.next_event <= -15.0:
                    # Start Standard Step at -15, but give it a 'cast' until on pull
                    current_time = self.next_event
                    self.initiate_action('StandardStep')
                    self.next_gcd = 1.5
                    self.next_event = self.next_gcd
                    return 'StandardStep', -current_time

            # use a GCD
            if self.next_event == 0.0:
                # open fight with Standard, if not used prepull
                action = 'StandardStep'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            if self.actions['TechnicalStep'].cooldown <= 0:
                # use Technical every time it's up
                return self.initiate_action('TechnicalStep')

            # inside Tech window
            if self.buffs['Technical'].timer > 0.0:
                if (self.buffs['Starfall'].timer < self.gcd_time) & (self.buffs['Starfall'].timer > 0):
                    # use Starfall if it is about to drop
                    action = 'Starfall'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                if (self.buffs['FF'].timer < self.gcd_time) & (self.buffs['FF'].timer > 0):
                    # don't let FF drop
                    return self.initiate_action('Fountainfall')
                if (self.buffs['RC'].timer < self.gcd_time) & (self.buffs['RC'].timer > 0):
                    # don't let RC drop
                    return self.initiate_action('ReverseCascade')
                if self.resources['esprit'].amount >= 50:
                    # use Saber Dance liberally
                    return self.initiate_action('SaberDance')
                else:
                    # priority list
                    action = 'Starfall'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                    action = 'Tillana'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                    action = 'Fountainfall'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                    action = 'ReverseCascade'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                    action = 'FlourishingFountainfall'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                    action = 'FlourishingReverseCascade'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                    # Use Standard if there is time to finish it in buffs
                    if self.buffs['Technical'].timer > 3.5:
                        action = 'StandardStep'
                        if self.allowed_action(action):
                            return self.initiate_action(action)
                    action = 'Fountain'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                    action = 'Cascade'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                    else:
                        print(f"No valid gcd. {self.last_time_check}")
            # outside Tech window
            else:
                # use Tillana if leftover
                action = 'Tillana'
                if self.allowed_action(action):
                    return self.initiate_action(action)
                # use SS on cooldown
                action = 'StandardStep'
                if self.allowed_action(action):
                    return self.initiate_action(action)
                # avoid overcapping esprit
                if self.resources['esprit'].amount > 75:
                    # use SaberDance
                    action = 'SaberDance'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                # basic gcd priority
                if self.buffs['F'].timer > 0:
                    action = 'Fountainfall'
                    if self.allowed_action(action):
                        return self.initiate_action(action)

                    action = 'FlourishingFountainfall'
                    if self.allowed_action(action):
                        return self.initiate_action(action)

                    action = 'Fountain'
                    if self.allowed_action(action):
                        return self.initiate_action(action)

                else:
                    action = 'ReverseCascade'
                    if self.allowed_action(action):
                        return self.initiate_action(action)

                    action = 'FlourishingReverseCascade'
                    if self.allowed_action(action):
                        return self.initiate_action(action)

                    action = 'Cascade'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
        else:
            # consider using oGCDs
            if round(self.next_event + self.anim_lock, 3) > self.next_gcd:
                # don't clip gcd
                return self.go_to_gcd()

            # inside Tech window
            if self.buffs['Technical'].timer > 0.0:
                # use Devilment first chance into Tech
                action = 'Devilment'
                if self.allowed_action(action):
                    return self.initiate_action(action)

                # use Fan3 if you can
                action = 'FanDance3'
                if self.allowed_action(action):
                    return self.initiate_action(action)

                # use Fan4 when not capped on Fans, to avoid potential capping
                if self.resources['feathers'].amount < 4:
                    action = 'FanDance4'
                    if self.allowed_action(action):
                        return self.initiate_action(action)

                # use Flourish first chance w/out capping Fan3
                action = 'Flourish'
                if self.allowed_action(action):
                    return self.initiate_action(action)

                # use fans liberally
                # burn Fan3 before using any fans
                action = 'FanDance1'
                if self.allowed_action(action):
                    return self.initiate_action(action)

                # doing nothing for this oGCD
                else:
                    return self.pass_ogcd()
            else:
                # outside Tech window
                # use Fan3 if you can
                action = 'FanDance3'
                if self.allowed_action(action):
                    return self.initiate_action(action)

                if self.resources['feathers'].amount >= 4:
                    # don't risk overwriting fan dance 3
                    action = 'FanDance3'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                    # use a fan to avoid capping
                    action = 'FanDance1'
                    if self.allowed_action(action):
                        return self.initiate_action(action)

                # catch any lingering Fan4
                action = 'FanDance4'
                if self.allowed_action(action):
                    return self.initiate_action(action)

                # use Flourish if not capping feathers or Fan3
                action = 'Flourish'
                if self.allowed_action(action):
                    return self.initiate_action(action)
                else:
                    # doing nothing for this oGCD
                    return self.pass_ogcd()

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay,
                      player_id=self.player_id, partner=self.buff_target, **self.kwargs)






