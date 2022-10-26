from .baseActor import BaseActor, ActionDC, BuffDC, DotDC
import pandas as pd
import numpy as np


# dancer-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, *, partner):
        # Dancer-specific values
        jobMod = 115
        trait = 120

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400)

        # override auto potency
        self.auto_potency = 80  # check this value

        # dnc specific resources
        self.resources = {'esprit': 0, 'feathers': 0}

        # dnc personal buffs
        buffs = {'F': BuffDC('logistic', 30.0), 'RC': BuffDC('logistic', 30.0),
                 'FF': BuffDC('logistic', 30.0), 'Tillana': BuffDC('logistic', 30.0),
                 'Starfall': BuffDC('logistic', 20.0), 'Threefold': BuffDC('logistic', 30.0),
                 'Fourfold': BuffDC('logistic', 30.0), 'FlourishingRC': BuffDC('logistic', 30.0),
                 'FlourishingFF': BuffDC('logistic', 30.0),
                 'testSelf': BuffDC('dmg', 10.0, 3.0)}
        self.buffs.update(buffs)

        # dnc needs a buff target (dance partner)
        self.buff_target = partner

        # dnc actions
        actions = {'Cascade': ActionDC('gcd', 220, self.gcd_time, self.gcd_time, 0.0,
                                       buff_effect={'self': ['F', ('RC', 0.5)]},
                                       resource={'esprit': 5},
                                       dot_effect='TestDot'),
                   'Fountain': ActionDC('gcd', 280, self.gcd_time, self.gcd_time,
                                        buff_effect={'self': [('FF', 0.5)]},
                                        buff_removal=['F'],
                                        resource={'esprit': 5}),
                   'ReverseCascade': ActionDC('gcd', 280, self.gcd_time, self.gcd_time,
                                              buff_effect={'team': ['testTeam']},
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
                                            buff_effect={'self': ['Standard']}),
                   'TechnicalStep': ActionDC('gcd', 1200, 120.0, 7.0,
                                             spd_adjusted=False,
                                             cast_time=5.5,
                                             buff_effect={'self': ['Tillana'], 'team': ['Technical']}),
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
        dots = {'TestDot': DotDC(50, 15, self.buff_state())}
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
                    return self.initiate_action('Starfall')
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
                    if self.buffs['Starfall'].timer > 0:
                        # use Starfall in an open spot
                        return self.initiate_action('Starfall')
                    if self.buffs['Tillana'].timer > 0:
                        # use Tillana in an open spot
                        return self.initiate_action('Tillana')
                    if self.buffs['FF'].timer > 0:
                        # use FF proc if available
                        return self.initiate_action('Fountainfall')
                    elif self.buffs['RC'].timer > 0:
                        # use RC proc if available
                        return self.initiate_action('ReverseCascade')
                    elif self.buffs['F'].timer > 0:
                        # use combo if available
                        return self.initiate_action('Fountain')
                    else:
                        # Basic Cascade GCD
                        return self.initiate_action('Cascade')
            # outside Tech window
            else:
                if self.buffs['Tillana'].timer > 0:
                    # use leftover Tillana proc if present
                    return self.initiate_action('Tillana')
                if self.actions['StandardStep'].cooldown <= 0:
                    # use Standard every time it's up
                    return self.initiate_action('StandardStep')
                if self.resources['esprit'] > 75:
                    # use SaberDance
                    return self.initiate_action('SaberDance')
                if self.buffs['FF'].timer > 0:
                    # use FF proc if available first
                    return self.initiate_action('Fountainfall')
                elif self.buffs['RC'].timer > 0:
                    # use RC proc if available
                    return self.initiate_action('ReverseCascade')
                elif self.buffs['F'].timer > 0:
                    # use combo if available
                    return self.initiate_action('Fountain')
                else:
                    # Basic Cascade GCD
                    return self.initiate_action('Cascade')
        else:
            # consider using oGCDs
            if self.next_event + 0.6 > self.next_gcd:
                # don't clip gcd
                return self.go_to_gcd()

            if self.buffs['Technical'].timer > 0.0:
                # inside Tech window
                if self.actions['Devilment'].cooldown <= 0:
                    # use Devilment first chance into Tech
                    return self.initiate_action('Devilment')
                elif (self.buffs['Fourfold'].timer > 0) & (self.resources['feathers'] < 4):
                    # use Fan4 when not capped on Fans, to avoid potential capping
                    return self.initiate_action('FanDance4')
                elif self.buffs['Threefold'].timer > 0:
                    # use Fan3 if you can
                    return self.initiate_action('FanDance3')
                elif self.actions['Flourish'].cooldown <= 0:
                    # use Flourish first chance w/out capping Fan3
                    return self.initiate_action('Flourish')
                elif self.resources['feathers'] > 0:
                    # use fans liberally
                    if self.buffs['Threefold'].timer > 0:
                        # burn Fan3 before using any fans
                        return self.initiate_action('FanDance3')
                    else:
                        # use a fan whenever you hit cap
                        return self.initiate_action('FanDance1')
                else:
                    # doing nothing for this oGCD
                    return self.pass_ogcd()
            else:
                # outside Tech window
                if self.buffs['Threefold'].timer > 0:
                    # use Fan3 if you can
                    return self.initiate_action('FanDance3')
                if self.resources['feathers'] >= 4:
                    if self.buffs['Threefold'].timer > 0:
                        # burn Fan3 before using any fans
                        return self.initiate_action('FanDance3')
                    else:
                        # use a fan whenever you hit cap
                        return self.initiate_action('FanDance1')
                else:
                    # doing nothing for this oGCD
                    return self.pass_ogcd()

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay, self.ten,
                      partner=self.buff_target)






