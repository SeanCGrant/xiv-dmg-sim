import numpy as np
import math
from dataclasses import dataclass, field


# Create a base class for the character actors
class BaseActor:

    def __init__(self, job_mod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400):
        self.jobMod = job_mod
        self.trait = trait
        self.wd = wd
        self.ap = ap
        self.det = det
        self.spd = spd
        self.crit = crit
        self.dhit = dhit
        self.wpn_delay = wpn_delay
        self.ten = ten
        self.gcd_time = spd_from_stat(spd, 2500)  # override for jobs that aren't on 2.5 gcd (2500 ms)
        self.next_event = 0.0
        self.action_counter = 0  # action tracker for provided list
        self.next_auto = 0.0
        self.auto_potency = 1  # each job should update appropriately
        self.dots = {}
        self.ex_buffs = {}  # track all external buffs (maybe start and end time for each buff)
        self.buffs = {}     # will track all buffs, should combine ex_buffs with each personal_buffs
        self.resources = {}
        self.actions = {}
        self.last_time_check = 0.0  # the last time this player had their timers updated
        self.total_buff_mult = 1.0  # actively modified to reflect current active buffs
        self.base_crit = crit_from_stat(crit)
        self.base_dhit = dhit_from_stat(dhit)
        self.crit_rate = self.base_crit  # actively modified to reflect current buffs and/or auto-crits
        self.dhit_rate = self.base_dhit  # actively modified to reflect current buffs and/or auto-dhits

    def char_stats(self):
        # return a list of the character's stats
        return [self.jobMod, self.trait, self.wd, self.ap, self.det, self.spd, self.wpn_delay, self.ten]

    def buff_state(self):
        # return current multiplier, crit_rate, and dhit_rate
        return self.total_buff_mult, self.crit_rate, self.dhit_rate

    def inc_action(self):
        # move to the next action
        self.action_counter += 1

    def inc_auto(self):
        # move to the next auto
        self.next_auto += self.wpn_delay

        return self.auto_potency, self.buff_state()

    def perform_action(self, action):
        # put the action on cooldown
        self.actions[action].cooldown = self.actions[action].self_cooldown

        # values to be returned
        potency = self.actions[action].potency
        buff_state = self.buff_state()

        # apply any self buffs, return any team buffs
        team_buffs = self.actions[action].buff_effect.get('team', [])
        self_buffs = self.actions[action].buff_effect.get('self', [])
        for buff in self_buffs:
            self.apply_buff(buff)

        # remove any buffs
        for buff in self.actions[action].buff_removal:
            self.remove_buff(buff)

        # apply any dots
        dot = self.actions[action].dot_effect
        if dot != 'none':
            self.apply_dot(dot)

        # generate any resources
        for resource, val in self.actions[action].resource.items():
            self.add_resource(resource, val)

        # adjust the player's next_event time
        # TO-DO: handle more than just GCDs
        self.next_event += self.actions[action].gcd_lock

        return potency, buff_state, team_buffs

    def apply_buff(self, buff):
        if isinstance(buff, tuple):
            # buff has a probability to go off (some procs, for example)
            if np.random.rand() < buff[1]:
                self.apply_buff(buff[0])
        else:
            if self.buffs[buff].timer == 0:
                # only apply the effect of the buff if actually new (not refreshing)
                match self.buffs[buff].type:
                    case 'logistic':
                        pass
                    case 'dmg':
                        self.total_buff_mult *= self.buffs[buff].value
                    case 'crit':
                        self.crit_rate += self.buffs[buff].value
                    case 'dhit':
                        self.dhit_rate += self.buffs[buff].value
                    case 'spd':
                        self.gcd_time /= self.buffs[buff].value

            # apply the buff at full duration
            self.buffs[buff].timer = self.buffs[buff].duration

    def remove_buff(self, buff):
        # remove the effect of the buff
        match self.buffs[buff].type:
            case 'dmg':
                self.total_buff_mult /= self.buffs[buff].value
            case 'crit':
                self.crit_rate -= self.buffs[buff].value
            case 'dhit':
                self.dhit_rate -= self.buffs[buff].value
            case 'spd':
                self.gcd_time *= self.buffs[buff].value

        # insure the timer goes to zero upon removal
        self.buffs[buff].timer = 0

    def apply_dot(self, dot_name):
        # update the dot timer
        self.dots[dot_name].timer = self.dots[dot_name].duration
        # take a snapshot of current buffs
        self.dots[dot_name].buff_snap = self.buff_state()

    def add_resource(self, name, val):
        if isinstance(val, tuple):
            if np.random.rand() < val[1]:
                self.add_resource(name, val[0])
        else:
            self.resources[name] += val

    def update_time(self, current_time):
        # adjust player timers based on how long it has been since the last update
        time_change = current_time - self.last_time_check

        # update all buff timers
        for buff, tracker in self.buffs.items():
            # also check for buff removal
            if tracker.update_time(time_change):
                if tracker.type != 'logistic':
                    # remove buff effect
                    self.remove_buff(buff)

        # update all dot timers
        for dot, tracker in self.dots.items():
            tracker.update_time(time_change)

        # update all action cooldowns
        for action, tracker in self.actions.items():
            tracker.update_time(time_change)

        # update last time check to now
        self.last_time_check = current_time


@dataclass
class ActionDC:
    # a class to hold the information for each available action
    type: str  # 'gcd', 'ogcd'
    potency: int
    self_cooldown: float
    gcd_lock: float
    cooldown: float = 0
    buff_effect: dict = field(default_factory=dict)  # (['none', 'self', 'team'], ['none', '*buff name*'])
    buff_removal: list = field(default_factory=list)  # ['*buff names*']
    dot_effect: str = 'none'  # 'none', '*dot name*'
    resource: dict = field(default_factory=dict)  # (['none', '*resource name*], [value])
    condition: bool = True  # might hold a place for an actions conditions, e.g. (resources['esprit'] >= 50)

    def update_time(self, time_change):
        self.cooldown = max(self.cooldown - time_change, 0)


@dataclass
class BuffDC:
    # a class to hold the information for each buff
    type: str  # 'dmg', 'crit', 'dhit', 'spd'
    duration: float  # length of the buff
    timer: float  # the remaining time on the buff
    value: float  # e.g. 1.05 for a 5% dmg buff

    def update_time(self, time_change):
        remove = False

        if self.timer > 0:
            if max(self.timer - time_change, 0) == 0:
                # indicate to remove the buff effect
                remove = True
            self.timer = max(self.timer - time_change, 0)

        return remove


@dataclass
class DotDC:
    # a class to hold the information for each DoT
    potency: int
    duration: float
    buff_snap: tuple
    timer: float = 0.0

    def update_time(self, time_change):
        if self.timer > 0:
            self.timer = max(self.timer - time_change, 0)


# get crit rate from the crit stat
def crit_from_stat(crit):
    lvlMod_sub = 400
    lvlMod_div = 1900

    crit_rate = ((200 * (crit - lvlMod_sub) / lvlMod_div + 50) // 1) / 1000
    return crit_rate


# get crit rate from the crit stat
def dhit_from_stat(dhit):
    lvlMod_sub = 400
    lvlMod_div = 1900

    dhit_rate = ((550 * (dhit - lvlMod_sub) / lvlMod_div) // 1) / 1000
    return dhit_rate


def spd_from_stat(spd, base_gcd):

    gcd = (((base_gcd * (1000 + math.ceil(130 * (400 - spd) / 1900)) / 10000) // 1) / 100)
    return gcd











