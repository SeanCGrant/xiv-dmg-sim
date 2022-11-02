from .baseActor import BaseActor, ActionDC, BuffDC, DotDC
import pandas as pd
import numpy as np


# dancer-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, *, player_id, partner):
        # Dancer-specific values
        jobMod = 115
        trait = 120

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, player_id=player_id)

        # override auto potency
        self.auto_potency = 90 * (self.wpn_delay / 3.0)  # TO-DO: check this value

        # dnc specific resources
        self.resources = {'esprit': 0, 'feathers': 0}

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
                                       buff_effect={'self': ['F', ('RC', 0.5)]},
                                       resource={'esprit': 5}),
                   'Fountain': ActionDC('gcd', 280, self.gcd_time, self.gcd_time,
                                        buff_effect={'self': [('FF', 0.5)]},
                                        buff_removal=['F'],
                                        resource={'esprit': 5}),
                   'ReverseCascade': ActionDC('gcd', 280, self.gcd_time, self.gcd_time,
                                              buff_removal=['RC'],
                                              resource={'esprit': 10, 'feathers': (1, 0.5)}),
                   'FlourishingReverseCascade': ActionDC('gcd', 280, self.gcd_time, self.gcd_time,
                                                         buff_removal=['FlourishingRC'],
                                                         resource={'esprit': 10, 'feathers': (1, 0.5)}),
                   'Fountainfall': ActionDC('gcd', 340, self.gcd_time, self.gcd_time,
                                            buff_removal=['FF'],
                                            resource={'esprit': 10, 'feathers': (1, 0.5)}),
                   'FlourishingFountainfall': ActionDC('gcd', 340, self.gcd_time, self.gcd_time,
                                                       buff_removal=['FlourishingFF'],
                                                       resource={'esprit': 10, 'feathers': (1, 0.5)}),
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
                                         buff_effect={'self': [('Threefold', 0.5)]}),
                   'FanDance3': ActionDC('ogcd', 200, 1.0,
                                         buff_removal=['Threefold']),
                   'FanDance4': ActionDC('ogcd', 300, 1.0,
                                         buff_removal=['Fourfold']),
                   'Flourish': ActionDC('ogcd', 0, 60.0,
                                        buff_effect={'self': ['FlourishingRC', 'FlourishingFF',
                                                              'Threefold', 'Fourfold']}),
                   'Devilment': ActionDC('ogcd', 0, 120.0,
                                         buff_effect={'self': ['Devilment_crit', 'Devilment_dhit', 'Starfall'],
                                                      'target': ['Devilment_crit', 'Devilment_dhit']})}
        self.actions.update(actions)

        # dnc dots
        dots = {}
        self.dots.update(dots)

    def choose_action(self):
        # determine current action, based on current buffs/procs

        if self.next_event == self.next_gcd:
            # use a GCD
            if self.next_event == 0.0:
                # open fight with Standard
                return self.initiate_action('StandardStep')
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
                if self.resources['esprit'] >= 50:
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
                    action = 'Fountain'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                    action = 'Cascade'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
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
                if self.resources['esprit'] > 75:
                    # use SaberDance
                    action = 'SaberDance'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                # basic gcd priority
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

                action = 'Fountain'
                if self.allowed_action(action):
                    return self.initiate_action(action)

                action = 'Cascade'
                if self.allowed_action(action):
                    return self.initiate_action(action)
        else:
            # consider using oGCDs
            if self.next_event + self.anim_lock > self.next_gcd:
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
                if self.resources['feathers'] < 4:
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

                if self.resources['feathers'] >= 4:
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
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay, self.ten,
                      player_id=self.player_id, partner=self.buff_target)






