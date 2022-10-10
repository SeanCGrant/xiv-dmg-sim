import numpy as np
from dataclasses import dataclass


# Create a base class for the character actors
class BaseActor:

    def __init__(self, job_mod, trait, wd, ap, det, spd, wpn_delay, ten=400):
        self.jobMod = job_mod
        self.trait = trait
        self.wd = wd
        self.ap = ap
        self.det = det
        self.spd = spd
        self.wpn_delay = wpn_delay
        self.ten = ten
        self.gcd_time = 2.5  # call to spd stat in the long run
        self.next_event = 0.0
        self.action_counter = 0  # action tracker for provided list
        self.next_auto = 0.0
        self.auto_potency = 1  # each job should update appropriately
        self.active_dots = np.array([[60, 0, 0], [90, 0, 0]])  # placeholder idea (60 and 90 pot dots, binary "on", end time)
        self.ex_buffs = {}  # track all external buffs (maybe start and end time for each buff)
        self.buffs = {}     # will track all buffs, should combine ex_buffs with each personal_buffs
        self.resources = {}
        self.actions = {}
        self.last_time_check = 0.0  # the last time this player had their timers updated
        self.total_buff_mult = 1.0  # actively modified to reflect current active buffs
        self.base_crit = 0.25  # TO-DO: make a call with crit stat
        self.base_dhit = 0.5  # TO-DO: make a call with dhit stat
        self.crit_rate = self.base_crit  # actively modified to reflect current buffs and/or auto-crits
        self.dhit_rate = self.base_dhit  # actively modified to reflect current buffs and/or auto-dhits

    def char_stats(self):
        # return a list of the character's stats
        return [self.jobMod, self.trait, self.wd, self.ap, self.det, self.spd, self.wpn_delay, self.ten]

    def inc_action(self):
        # move to the next action
        self.action_counter += 1

    def inc_auto(self):
        # move to the next auto
        self.next_auto += self.wpn_delay

        return self.auto_potency

    def report_dots(self, time):
        # check if dots are still active
        self.active_dots[:, 1] = np.where(self.active_dots[:, 2] >= time, self.active_dots[:, 1], 0)
        # report the total potency of all active dots
        return np.sum(np.where(self.active_dots[:, 1], self.active_dots[:, 0], 0))

    def perform_action(self, action):
        # put the action on cooldown
        self.actions[action].cooldown = self.actions[action].self_cooldown

        potency = self.actions[action].potency
        buff_type = self.actions[action].buff_effect[0]
        buff = self.actions[action].buff_effect[1]

        # apply any self(?) buffs
        if buff_type == 'self':
            self.apply_buff(buff)
            buff = 'none'

        return potency, buff

    def apply_buff(self, buff):
        # apply the buff at full duration
        self.buffs[buff].timer = self.buffs[buff].duration

        # apply the effect of the buff
        match self.buffs[buff].type:
            case 'dmg':
                self.total_buff_mult *= self.buffs[buff].value
            case 'crit':
                self.crit_rate += self.buffs[buff].value
            case 'dhit':
                self.dhit_rate += self.buffs[buff].value
            case 'spd':
                self.gcd_time /= self.buffs[buff].value

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




@dataclass
class ActionDC:
    # a class to hold the information for each available action
    type: str  # 'gcd', 'ogcd'
    potency: int
    self_cooldown: float
    cooldown: float = 0
    buff_effect: str = 'none'  # 'none', '*buff name*'
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












