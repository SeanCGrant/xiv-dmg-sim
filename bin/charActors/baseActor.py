import numpy as np
import math
from dataclasses import dataclass, field


# Create a base class for the character actors
class BaseActor:

    def __init__(self, job_mod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, anim_lock=0.65, *, player_id):
        self.player_id = player_id
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
        self.gcd_time = spd_from_stat(spd, 2500) + 0.005  # [fps estimate included] override for jobs that aren't on 2.5 gcd (2500 ms)
        self.anim_lock = anim_lock
        self.spd_mod = 1.0
        self.next_gcd = 0.0
        self.next_ogcd = 0.0
        self.next_event = 0.0
        self.action_counter = 0  # action tracker for provided list
        self.next_auto = 0.0
        self.auto_potency = 1  # each job should update appropriately
        self.dots = {}
        # will track all buffs, universal external buffs listed here, personal buffs added within each job
        # TO-DO: add all targeted buffs here too
        self.buffs = {'Technical': BuffDC('dmg', 20.5, 1.05),
                      'TechEsprit': TargetedBuff('given', 20.0,
                                                 gift={'name': 'esprit', 'value': 10, 'rng': 0.2}),
                      'Standard': BuffDC('dmg', 60.0, 1.05),
                      'StandardEsprit': TargetedBuff('given', 20.0,
                                                     gift={'name': 'esprit', 'value': 10, 'rng': 0.2}),
                      'Devilment_crit': BuffDC('crit', 20.0, 0.2),
                      'Devilment_dhit': BuffDC('dhit', 20.0, 0.2),
                      'Divination': BuffDC('dmg', 15.0, 1.06),
                      'BattleLitany': BuffDC('crit', 15.0, 0.1)}
        self.tracked_buffs = ['TechEsprit', 'StandardEsprit']
        self.buff_tracked = False
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

    def go_to_gcd(self):
        # jump to the next gcd
        self.next_event = self.next_gcd

        return None, 0.0

    def pass_ogcd(self):
        # find next ogcd window and then jump to it
        # TO-DO: put in options for late-weave ogcds
        self.next_ogcd += self.anim_lock
        self.next_event = min(self.next_gcd, self.next_ogcd)

        return None, 0.0

    def allowed_action(self, action_name):
        action = self.actions[action_name]

        # Check the charges
        if action.charge_count < 1:
            return False
        # check the cooldown (REMOVE?)
        if action.cooldown > 0.00005:  # wiggle room for float precision (TO-DO: floor values appropriately)
            return False
        # check for proc (logistical buffs, usually)
        for proc in action.buff_removal:
            if self.buffs[proc].timer <= 0.0:
                return False
        # check for necessary resources
        for resource, val in action.resource.items():
            if isinstance(val, tuple):
                # No rng consumed resources exist, so if it has rng, it is a gained resource
                continue
            if (val < 0) & (self.resources[resource].amount < val * -1):
                return False
        return True

    def initiate_action(self, action_name):
        # adjust the player's next_event time
        action = self.actions[action_name]

        # apply any haste buffs, if the action is affected
        spd_mod = 1
        if action.spd_adjusted:
            spd_mod = self.spd_mod

        # If action was at max charges, start the charge cooldown
        if action.charge_count == action.max_charges:
            action.charge_cd = action.charge_time * spd_mod
        # Use a charge
        action.charge_count -= 1

        # put the action on cooldown
        action.cooldown = action.recast * spd_mod

        if action.type == 'gcd':
            # roll GCD
            self.next_gcd += round(action.gcd_lock * spd_mod, 3)
            # and animation-lock to next oGCD slot
            self.next_ogcd = round(self.next_event + (action.cast_time * spd_mod) + action.anim_lock, 3)

        if action.type == 'ogcd':
            # just move up one animation-lock slot for now
            # TO-DO: logic for late-weave slots
            self.next_ogcd = round(self.next_ogcd + action.anim_lock, 3)
            # Force animation lock on next GCD if applicable
            self.next_gcd = max(self.next_gcd, self.next_ogcd)

        # find next open event slot
        self.next_event = min(self.next_gcd, self.next_ogcd)

        return action_name, action.cast_time * spd_mod

    def perform_action(self, action):
        action = self.actions[action]

        # values to be returned
        potency = action.potency
        m, crit, dhit = self.buff_state()
        if action.autocrit:
            crit = 1.0
            # Patch 6.2: Apply dmg bonus for crit rate buffs
            m *= 1 + ((self.crit_rate - self.base_crit) * (self.base_crit + 0.35))
        if action.autodhit:
            dhit = 1.0
            # Patch 6.2: Apply a dmg bonus for dhit rate buffs
            m *= 1 + ((self.dhit_rate - self.base_dhit) * 0.25)

        # Determine buff to send
        buff_effect = action.buff_effect
        # If this is a buff selector, then select a buff (or set of buffs)
        if isinstance(action.buff_effect, BuffSelector):
            buff_effect = buff_effect.select()

        # remove any buffs
        for buff in action.buff_removal:
            self.remove_buff(buff)

        # apply any dots
        dot = action.dot_effect
        if dot != 'none':
            self.apply_dot(dot)

        # generate any resources
        for resource, val in action.resource.items():
            self.add_resource(resource, val)

        return potency, (m, crit, dhit), buff_effect, action.type

    def apply_buff(self, buff, *, giver_id=10):
        if isinstance(buff, tuple):
            # buff has a probability to go off (some procs, for example)
            if np.random.rand() < buff[1]:
                self.apply_buff(buff[0])
        else:
            if self.buffs[buff].timer == 0:
                # only apply the effect of the buff if actually new (not refreshing)
                match self.buffs[buff].type:
                    case 'dmg':
                        self.total_buff_mult *= self.buffs[buff].value
                    case 'crit':
                        self.crit_rate += self.buffs[buff].value
                    case 'dhit':
                        self.dhit_rate += self.buffs[buff].value
                    case 'spd':
                        self.spd_mod *= (1 - self.buffs[buff].value)
                    case 'given':
                        # make sure the player is flagged as having a tracked buff
                        self.buff_tracked = True

            # update the buffs giver, if it is a given-tracked buff
            if self.buffs[buff].type == 'given':
                self.buffs[buff].buff_giver = giver_id

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
                self.spd_mod /= (1 - self.buffs[buff].value)
            case 'given':
                # remove the tracked flag...
                self.buff_tracked = False
                # ...but only if there are no other tracked buffs
                for tracked_buff in self.tracked_buffs:
                    if self.buffs[tracked_buff].timer > 0:
                        self.buff_tracked = True
                        break

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
            resource = self.resources[name]

            # If the resource is supposed to be consumed in full, set value to negative of current quantity
            if val == 'consume':
                val = - resource.amount

            # If removing resource from a max-capped timed resource, start its cooldown
            if (isinstance(resource, TimedResourceDC)) & (resource.amount == resource.max) & (val < 0):
                resource.charge_cd = resource.charge_time

            # Add (or subtract) the resource, and don't let it go over the max allowed value
            self.resources[name].amount = min(self.resources[name].amount + val, self.resources[name].max)

    def update_time(self, current_time):
        # adjust player timers based on how long it has been since the last update
        time_change = round(current_time - self.last_time_check, 3)

        # don't need to do anything if time is already caught up
        if time_change == 0.0:
            return

        # update all buff timers
        for buff, tracker in self.buffs.items():
            # also check for buff removal
            if tracker.update_time(time_change):
                if tracker.type != 'logistic':
                    # remove buff effect
                    self.remove_buff(buff)
                else:
                    print(f"Lost a Proc!!??\t{buff}")

        # update all dot timers
        for dot, tracker in self.dots.items():
            tracker.update_time(time_change)

        # update all action cooldowns
        for action, tracker in self.actions.items():
            tracker.update_time(time_change)

        # Update resource timers
        for resource, tracker in self.resources.items():
            # only for timed resources
            if isinstance(tracker, TimedResourceDC):
                tracker.update_time(time_change)

        # update last time check to now
        self.last_time_check = current_time


@dataclass
class ResourceDC:
    max: int
    amount: int = 0


@ dataclass
class TimedResourceDC(ResourceDC):
    max_charges: int = 1
    charge_count: int = -1
    charge_time: float = 0.0
    charge_cd: float = 0.0  # The recharge cooldown

    def __post_init__(self):
        if self.charge_count == -1:
            # Set starting charges to max charges, unless specified otherwise
            self.charge_count = self.max_charges
        if self.charge_count == 0:
            # If the count starts at zero, then the cd starts automatically too
            self.charge_cd = self.charge_time

    def update_time(self, time_change):
        # Do nothing if the time hasn't actually changed
        if time_change == 0:
            return

        # Add a charge for each full pass over the charge time
        self.charge_count += time_change // self.charge_time
        # Now adjust for the extra time
        extra_time = time_change % self.charge_time
        # Check if this extra time also passed the current cooldown
        if (self.charge_cd - extra_time) <= 0:
            # Add a charge
            self.charge_count += 1
            # Set the new cooldown
            self.charge_cd = round(self.charge_time + (self.charge_cd - extra_time), 3)
        else:
            # Set the new cooldown
            self.charge_cd = round(self.charge_cd - extra_time, 3)
        # Check if the charges have hit their max
        if self.charge_count >= self.max_charges:
            # Reset to max
            self.charge_count = self.max_charges
            # And 'stop' the cooldown count
            self.charge_cd = 0


@dataclass
class BuffDC:
    # a class to hold the information for each buff
    type: str  # 'dmg', 'crit', 'dhit', 'spd'
    duration: float  # length of the buff
    value: float = 0.0  # e.g. 1.05 for a 5% dmg buff
    delay: float = 0.2  # TO-DO: this is a random guess at typical buff propagation delay
    timer: float = 0.0  # the remaining time on the buff

    def update_time(self, time_change):
        remove = False

        if self.timer > 0:
            if max(self.timer - time_change, 0) == 0:
                # indicate to remove the buff effect
                remove = True
            self.timer = max(round(self.timer - time_change, 3), 0)

        return remove


@dataclass
class TargetedBuff(BuffDC):
    # only for  buffs that need to track back to their giver, generally for resource generation
    buff_giver: int = field(kw_only=True, default=10)
    gift: dict = field(default_factory=dict)  # {'name': , 'value': , 'rng': }


@dataclass
class BuffSelector:
    # a class used when the buff that gets used depends on the state of the actor
    buff_selection: list  # Potential buffs to send
    sticker_selection: list  # The 'stickers' that affect which buff to choose
    actor: BaseActor

    def select(self):
        # count how many of the stickers are present
        count = 0
        for sticker in self.sticker_selection:
            if self.actor.resources[sticker].amount == 1:
                count += 1

        # Send no buffs back if no stickers
        if count == 0:
            return {}
        # Otherwise select the appropriate buff
        return self.buff_selection[count - 1]


@dataclass
class DotDC:
    # a class to hold the information for each DoT
    potency: int
    duration: float
    buff_snap: tuple
    timer: float = 0.0

    def update_time(self, time_change):
        if self.timer > 0:
            self.timer = max(round(self.timer - time_change, 3), 0)


@dataclass
class ActionDC:
    # a class to hold the information for each available action
    type: str  # 'gcd', 'ogcd'
    potency: int
    recast: float = 2.5
    gcd_lock: float = 0
    cooldown: float = 0  # The recast cooldown
    cast_time: float = 0  # This should be the in-game "cast time" minus 0.5s for the snapshot point
    max_charges: int = 1
    charge_count: int = -1
    charge_time: float = 0.0
    charge_cd: float = 0.0  # The recharge cooldown
    anim_lock: float = 0.65
    autocrit: bool = False
    autodhit: bool = False
    spd_adjusted: bool = True
    buff_effect: dict | BuffSelector = field(default_factory=dict)  # (['self', 'team', 'target']: ['*buff names*'])
    buff_removal: list = field(default_factory=list)  # ['*buff names*']
    dot_effect: str = 'none'  # 'none', '*dot name*'
    resource: dict = field(default_factory=dict)  # (['none', '*resource name*], [value])
    condition: bool = True  # might hold a place for an actions conditions, e.g. (resources['esprit'] >= 50)

    def __post_init__(self):
        if self.charge_count == -1:
            # Set starting charges to max charges, unless specified otherwise
            self.charge_count = self.max_charges
        if self.charge_time == 0:
            # If it wasn't set, set the charge time to the recast time
            self.charge_time = self.recast

        # Default oGCDs to be unaffected by haste
        if self.type == 'ogcd':
            self.spd_adjusted = False

    def update_time(self, time_change):
        # Do nothing if the time hasn't actually changed
        if time_change == 0:
            return

        self.cooldown = max(round(self.cooldown - time_change, 3), 0)

        # Add a charge for each full pass over the charge time
        self.charge_count += time_change // self.charge_time
        # Now adjust for the extra time
        extra_time = time_change % self.charge_time
        # Check if this extra time also passed the current cooldown
        if (self.charge_cd - extra_time) <= 0:
            # Add a charge
            self.charge_count += 1
            # Set the new cooldown
            self.charge_cd = round(self.charge_time + (self.charge_cd - extra_time), 3)
        else:
            # Set the new cooldown
            self.charge_cd = round(self.charge_cd - extra_time, 3)
        # Check if the charges have hit their max
        if self.charge_count >= self.max_charges:
            # Reset to max
            self.charge_count = self.max_charges
            # And 'stop' the cooldown count
            self.charge_cd = 0


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











