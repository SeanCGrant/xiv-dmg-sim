import numpy as np
import math
from dataclasses import dataclass, field
from typing import Callable


# Create a base class for the character actors
class BaseActor:

    def __init__(self, job_mod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, ten=400, anim_lock=0.65, *, player_id,
                 actions_defined=False, rotation_file=''):
        print(actions_defined)
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
        self.auto_spd_mod = 1.0
        self.next_gcd = -60.0
        self.next_ogcd = -60.0
        self.next_event = -60.0
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
                      'BattleLitany': BuffDC('crit', 15.0, 0.1),
                      'Brotherhood': BuffDC('dmg', 15.0, 1.05),
                      'Meditative Brotherhood': TargetedBuff('given', 15.0,
                                                             gift={'name': 'chakra', 'value': 1, 'rng': 0.2})}
        self.tracked_buffs = ['TechEsprit', 'StandardEsprit', 'Meditative Brotherhood']
        self.buff_tracked = False
        self.resources = {}
        self.actions = {}
        self.last_time_check = 0.0  # the last time this player had their timers updated
        self.total_buff_mult = 1.0  # actively modified to reflect current active buffs
        self.base_crit = crit_from_stat(crit)
        self.base_dhit = dhit_from_stat(dhit)
        self.crit_rate = self.base_crit  # actively modified to reflect current buffs and/or auto-crits
        self.dhit_rate = self.base_dhit  # actively modified to reflect current buffs and/or auto-dhits
        self.actions_list = False  # True if a list of actions is provided by the user
        self.actions_defined = actions_defined  # True if a time-specified list of actions is provided by the user
        self.rotation_file = rotation_file  # The file location for a defined rotation

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
        self.next_auto += self.wpn_delay * self.auto_spd_mod

        return self.auto_potency, self.buff_state()

    def go_to_gcd(self):
        # jump to the next gcd
        self.next_event = self.next_gcd

        return None, 0.0

    def pass_ogcd(self):
        # find next ogcd window and then jump to it
        # TO-DO: put in options for late-weave ogcds
        # Ignore the late weave, if it is before the current ogcd slot, and advance to the next GCD
        if self.next_ogcd >= round(self.next_gcd - self.anim_lock, 3):
            self.next_event = self.next_gcd
            return None, 0.0
        # Otherwise consider the latest late weave
        self.next_ogcd = round(min(self.next_ogcd + self.anim_lock, self.next_gcd - self.anim_lock), 3)
        self.next_event = round(min(self.next_gcd, self.next_ogcd), 3)

        return None, 0.0

    def go_to_cd(self, action_name):
        action = self.actions[action_name]
        # Go to when the action is off cd
        # Determine when action will be usable -- both cooldown and charges are available
        charge_wait = 0
        if action.charge_count < 1:
            charge_wait = action.charge_cd
        wait_time = round(max(action.cooldown, charge_wait), 3)

        # Adjust event timers based on this wait, and whether the action is a GCD or oGCD
        if action.type == 'ogcd':
            # Move ogcd to the desired action time
            self.next_ogcd = round(self.next_event + wait_time, 3)
            # Only change GCD if this ogcd is available after the next gcd
            self.next_gcd = round(max(self.next_gcd, self.next_ogcd), 3)
            # Update next event
            self.next_event = round(min(self.next_gcd, self.next_ogcd), 3)
        else:
            # Move GCD to desired action time
            self.next_gcd = round(self.next_event + wait_time, 3)
            # Move up oGCD too, just in case
            self.next_ogcd = self.next_gcd
            # Update next event
            self.next_event = round(self.next_gcd, 3)

        # Put no action in the queue right now
        return None, 0.0

    def is_off_cd(self, action_name):
        action = self.actions[action_name]
        # Return True if action is usable from a cooldown and charge perspective
        # Check the charges
        if action.charge_count < 1:
            return False
        # Check the cooldown
        if action.cooldown > 0.0:
            return False
        # Return True if we have made it here
        return True

    def allowed_action(self, action_name):
        action = self.actions[action_name]

        # Check the charges
        if action.charge_count < 1:
            return False
        # check the cooldown (REMOVE?)
        if action.cooldown > 0.0:
            return False
        # Check for disallowed buffs
        for buff in action.disallowed_buff:
            if self.buffs[buff].timer > 0.0:
                return False
        # check for required buffs, procs, etc.
        for proc in action.buff_removal + action.required_buff:
            if isinstance(proc, list):
                # Check for any one of the buffs, if a conditional list is given
                valid = True
                for buff_opt in proc:
                    if self.buffs[buff_opt].timer > 0.0:
                        valid = True
                        break
                # If none of the buffs are present
                if not valid:
                    return False
            else:
                if self.buffs[proc].timer <= 0.0:
                    return False
        # check for necessary resources
        for resource, val in action.resource.items():
            if isinstance(val, Chance):
                # No rng consumed resources exist, so if it has rng, it is a gained resource
                continue
            # If it is a full-resource consuming Action, check based on the minimum need
            if isinstance(val, Consume):
                val = - val.min
            # If resources are being used, make sure there is enough
            if (val < 0) & (self.resources[resource].amount < val * -1):
                return False
        return True

    def initiate_action(self, action_name):
        # initiate the requested action
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
        # Don't let charge count go below zero
        if action.charge_count < 0:
            # But send a warning if it does
            print(f"Warning: Negative charge achieved. ({action_name})")
            # and reset to zero
            action.charge_count = 0
            # This allows predefined rotations to break some rules

        # put the action on cooldown
        action.cooldown = action.recast * spd_mod

        if action.type == 'gcd':
            # roll GCD (and check for a predefined later "next_gcd")
            self.next_gcd = round(max(self.last_time_check + action.gcd_lock * spd_mod, self.next_gcd), 3)
            # and animation-lock to next oGCD slot (and check for predefined later "next_ogcd")
            self.next_ogcd = round(max(self.last_time_check + (action.cast_time * spd_mod) + action.anim_lock,
                                       self.next_ogcd), 3)

        if action.type == 'ogcd':
            # just move up one animation-lock slot for now
            # TO-DO: logic for late-weave slots
            self.next_ogcd = round(max(self.last_time_check + action.anim_lock, self.next_ogcd), 3)
            # Force animation lock on next GCD if applicable
            self.next_gcd = round(max(self.next_gcd, self.next_ogcd), 3)

        # find next open event slot (and check for a predefined later "next_event")
        self.next_event = round(max(min(self.next_gcd, self.next_ogcd), self.next_event), 3)

        return action_name, action.cast_time * spd_mod

    def perform_action(self, action):
        action = self.actions[action]

        # values to be returned
        potency = action.potency
        # Calculate potency if needed
        if callable(potency):
            potency = potency()
        m, crit, dhit = self.buff_state()
        # Check for auto-crit
        if isinstance(action.autocrit, BuffConditional):
            autocrit = action.autocrit.check()
        else:
            autocrit = action.autocrit
        # Apply auto-crit changes if applicable
        if autocrit:
            crit = 1.0
            # Patch 6.2: Apply dmg bonus for crit rate buffs
            m *= 1 + ((self.crit_rate - self.base_crit) * (self.base_crit + 0.35))
        # Check for auto-dhit
        if isinstance(action.autodhit, BuffConditional):
            autodhit = action.autodhit.check()
        else:
            autodhit = action.autodhit
        # Apply auto-dhit changes if applicable
        if autodhit:
            dhit = 1.0
            # Patch 6.2: Apply a dmg bonus for dhit rate buffs
            m *= 1 + ((self.dhit_rate - self.base_dhit) * 0.25)

        # Determine buff to send
        buff_effect = action.buff_effect
        # If this is a buff selector, then select a buff (or set of buffs)
        if isinstance(action.buff_effect, BuffSelector):
            buff_effect = buff_effect.select()

        # Remove buffs as necessary
        for buff in action.buff_removal + action.buff_removal_opt:
            if isinstance(buff, list):
                # Remove only the first active buff in the list if a conditional list is given
                for buff_opt in buff:
                    if self.buffs[buff_opt].timer > 0:
                        self.remove_buff(buff_opt)
                        break
            else:
                # Remove Buff
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
        if isinstance(buff, Chance):
            # buff has a probability to go off (some procs, for example)
            if np.random.rand() < buff.probability:
                self.apply_buff(buff.val)
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
                    case 'auto-spd':
                        self.auto_spd_mod *= (1 - self.buffs[buff].value)
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
            case 'auto-spd':
                self.auto_spd_mod /= (1 - self.buffs[buff].value)
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
        # Check if this is an rng resource
        if isinstance(val, Chance):
            # Roll the dice
            if np.random.rand() < val.probability:
                # Give the resource on success
                self.add_resource(name, val.val)
        else:
            resource = self.resources[name]

            # If the resource is supposed to be consumed in full, set value to negative of current quantity
            if isinstance(val, Consume):
                val = - resource.amount

            # If removing resource from a max-capped timed resource, start its cooldown
            if (isinstance(resource, TimedResourceDC)) & (resource.amount == resource.max) & (val < 0):
                resource.charge_cd = resource.charge_time

            # Add (or subtract) the resource, and don't let it go over the max allowed value or under 0
            self.resources[name].amount = max(0, min(self.resources[name].amount + val, self.resources[name].max))

    def combo_potency(self, potency_list, combo_name):
        # potency_list is a list with [uncombo'd potency, combo'd potency]

        # Generate a function that checks if the combo is active
        def pot_function():
            if self.buffs[combo_name].timer > 0:
                # Remove the combo buff when used
                self.remove_buff(combo_name)
                # And return the combo'd potency
                return potency_list[1]
            else:
                # Return the uncombo'd potency
                return potency_list[0]

        # Return this function
        return pot_function

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
class Chance:
    val: int | str
    probability: float


@dataclass
class ResourceDC:
    max: int
    amount: int = 0


@ dataclass
class TimedResourceDC(ResourceDC):
    charge_time: float = 1.0
    charge_cd: float = 0.0  # The recharge cooldown
    amount: int = -1

    def __post_init__(self):
        if self.amount == -1:
            # Set starting charges to max charges, unless specified otherwise
            self.amount = self.max
        if self.amount == 0:
            # If the count starts at zero, then the cd starts automatically too
            self.charge_cd = self.charge_time

    def update_time(self, time_change):
        # Do nothing if the time hasn't actually changed
        if time_change == 0:
            return

        # Add a charge for each full pass over the charge time
        self.amount += time_change // self.charge_time
        # Now adjust for the extra time
        extra_time = time_change % self.charge_time
        # Check if this extra time also passed the current cooldown
        if (self.charge_cd - extra_time) <= 0:
            # Add a charge
            self.amount += 1
            # Set the new cooldown
            self.charge_cd = round(self.charge_time + (self.charge_cd - extra_time), 3)
        else:
            # Set the new cooldown
            self.charge_cd = round(self.charge_cd - extra_time, 3)
        # Check if the charges have hit their max
        if self.amount >= self.max:
            # Reset to max
            self.amount = self.max
            # And 'stop' the cooldown count
            self.charge_cd = 0


@dataclass
class Consume:
    # Used for Actions that consume all of a given resource
    min: int = 0  # The min value needed for the Action to be allowed


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

    actor: BaseActor
    buff_selection: list  # Potential buffs to send
    sticker_selection: list  # The 'stickers' that affect which buff to choose
    mode: str = 'count'  # 'count' or 'type'

    def select(self):
        if self.mode == 'count':
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

        if self.mode == 'type':
            # Choose the list item that corresponds with the first buff present in the list
            for i, buff in enumerate(self.sticker_selection):
                if self.actor.buffs[buff].timer > 0.0:
                    return self.buff_selection[i]
            # If none of the conditional buffs are present
            # Check if an extra item exists in the buff_selection list
            if len(self.buff_selection) == i+2:
                # return that item (the no-buff option)
                return self.buff_selection[i+1]
            # Otherwise send no buffs back
            else:
                return {}

        else:
            # no valid mode provided -- send back no buffs
            return {}


@dataclass
class BuffConditional:
    # A class for truthiness of buff presence
    actor: BaseActor
    buffs: list = field(default_factory=list)

    def check(self):
        # Check if any of the buffs are present, and return True if so
        for buff in self.buffs:
            if self.actor.buffs[buff].timer > 0:
                return True
        return False


@dataclass
class DotDC:
    # a class to hold the information for each DoT
    potency: int
    duration: float
    buff_snap: tuple = field(default_factory=tuple)
    timer: float = 0.0

    def update_time(self, time_change):
        if self.timer > 0:
            self.timer = max(round(self.timer - time_change, 3), 0)


@dataclass
class ActionDC:
    # a class to hold the information for each available action
    type: str  # 'gcd', 'ogcd'
    potency: int | Callable
    recast: float = 2.5
    gcd_lock: float = 0
    cooldown: float = 0  # The dynamic recast cooldown
    cast_time: float = 0  # This should be the in-game "cast time" minus 0.5s for the snapshot point
    max_charges: int = 1
    charge_count: int = -1
    charge_time: float = 0.0  # How long it takes to generate a charge
    charge_cd: float = 0.0  # The dynamic recharge cooldown
    anim_lock: float = 0.65
    autocrit: bool | BuffConditional = False
    autodhit: bool | BuffConditional = False
    spd_adjusted: bool = True
    buff_effect: dict | BuffSelector = field(default_factory=dict)  # (['self', 'team', 'target']: ['*buff names*'])
    # Used for most things -- buffs that are required and removed
    buff_removal: list = field(default_factory=list)  # ['*buff names*']
    # Used when the buffs are removed, but not required for the action
    buff_removal_opt: list = field(default_factory=list)
    # Used when buffs are required, but don't get removed by the action
    required_buff: list = field(default_factory=list)
    # Disallowed buffs -- buffs that prevent an action from being used
    disallowed_buff: list = field(default_factory=list)
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











