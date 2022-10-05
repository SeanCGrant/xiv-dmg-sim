import numpy as np


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
        self.last_time_check = 0.0  # the last time this player had their timers updated

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












