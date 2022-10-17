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
        self.dots = {}
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
        buff_type = self.actions[action].buff_effect[0]
        buff = self.actions[action].buff_effect[1]
        match buff_type:
            case 'self':
                self.apply_buff(buff)
                buff = 'none'
            case 'logistic':
                # don't return logistic buffs
                buff = 'none'
            case _:
                pass

        # apply any dots
        dot = self.actions[action].dot_effect
        if dot != 'none':
            self.apply_dot(dot)

        # adjust the player's next_event time
        # TO-DO: handle more than just GCDs
        self.next_event += self.gcd_time

        return potency, buff_state, buff

    def apply_buff(self, buff):
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

    def apply_dot(self, dot_name):
        # update the dot timer
        self.dots[dot_name].timer = self.dots[dot_name].duration
        # take a snapshot of current buffs
        self.dots[dot_name].buff_snap = self.buff_state()

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
    cooldown: float = 0
    buff_effect: (str, str) = ('none', 'none')  # (['none', 'self', 'team'], ['none', '*buff name*'])
    dot_effect: str = 'none'  # 'none', '*dot name*'
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













