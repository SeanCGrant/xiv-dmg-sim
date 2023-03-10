# Module for functions used in the simulations
import copy
import csv
import heapq
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from charActors.baseActor import Chance


# convert potency to damage (standard hits)
def pot_to_dmg(pot, job_mod, trait, wd, ap, det, tnc=400):
    lvlMod_main = 390
    lvlMod_sub = 400
    lvlMod_div = 1900
    jobMod_dmg = job_mod  # 115 ish
    trait = trait  # 120 ish

    fAtk = ((195 * (ap - lvlMod_main) / lvlMod_main) // 1) + 100
    # ^^ probably 195 instead of 165, and '340' was actually lvl_main; should be something else for tanks? ^^ #
    fDet = (((140 * (det - lvlMod_main)) / lvlMod_div) + 1000) // 1
    # ^ 140 instead of 130 in EW #
    fTnc = (((100 * (tnc - lvlMod_sub)) / lvlMod_div) + 1000) // 1
    fWd = ((lvlMod_main * jobMod_dmg) // 1000) + wd

    dmg = ((((((((((((pot * fAtk * fDet) // 1) // 100) // 1000) * fTnc) // 1) // 1000) * fWd) // 1) // 100) * trait) // 100)
    return dmg


# convert potency to damage (auto attacks)
def auto_dmg(pot, job_mod, trait, wd, ap, det, spd, wpn_delay, tnc=400):
    lvlMod_main = 390
    lvlMod_sub = 400
    lvlMod_div = 1900
    jobMod_dmg = job_mod  # 115 ish
    trait = trait  # 120 ish

    fAtk = ((195 * (ap - lvlMod_main) / lvlMod_main) // 1) + 100
    # ^^ probably 195 instead of 165, and '340' was actually lvl_main; should be something else for tanks? ^^ #
    fDet = (((140 * (det - lvlMod_main)) / lvlMod_div) + 1000) // 1
    # ^ 140 instead of 130 in EW #
    fTnc = (((100 * (tnc - lvlMod_sub)) / lvlMod_div) + 1000) // 1
    fSpd = (((130 * (spd - lvlMod_sub)) / lvlMod_div) + 1000) // 1
    fAuto = (((((lvlMod_main * jobMod_dmg) / 1000) + wd) // 1) * (wpn_delay / 3)) // 1

    dmg = ((((((((((((((pot * fAtk * fDet) // 1) // 100) // 1000) * fTnc) // 1) // 1000) * fSpd) // 1) // 1000 * fAuto) // 1) // 100) * trait) // 100)
    return dmg


# convert potency to damage (dot ticks)
def dot_dmg(pot, job_mod, trait, wd, ap, det, spd, tnc=400):
    lvlMod_main = 390
    lvlMod_sub = 400
    lvlMod_div = 1900
    jobMod_dmg = job_mod  # 115 ish
    trait = trait  # 120 ish

    fAtk = ((195 * (ap - lvlMod_main) / lvlMod_main) // 1) + 100
    # ^^ probably 195 instead of 165, and '340' was actually lvl_main; should be something else for tanks? ^^ #
    fDet = (((140 * (det - lvlMod_main)) / lvlMod_div) + 1000) // 1
    # ^ 140 instead of 130 in EW #
    fTnc = (((100 * (tnc - lvlMod_sub)) / lvlMod_div) + 1000) // 1
    fWd = ((lvlMod_main * jobMod_dmg) // 1000) + wd
    fSpd = (((130 * (spd - lvlMod_sub)) / lvlMod_div) + 1000) // 1

    dmg = (((((((((((((((pot * fAtk * fDet) // 1) // 100) // 1000) * fTnc) // 1) // 1000) * fSpd) //1) // 1000) * fWd) // 1) // 100) * trait) // 100) + 1
    return dmg


def sim_battle(fight_length, actor_list, verbose=False):

    # Put an event into the battle log
    def log_event(time, player, event_type, event_name, event_pot, event_crit, event_dhit, event_M, resources, verbose):
        # We want a snapshot of the resources, not the object itself
        resources = copy.deepcopy(resources)
        # create a line for the event, then add to the battle log
        event_log = pd.Series({"Time": time, "Player": player, "Type": event_type, "Ability": event_name,
                               "Potency": event_pot, "Crit Rate": event_crit, "Dhit Rate": event_dhit,
                               "Multiplier": event_M, "Flat Damage": np.nan, "Full Damage": np.nan,
                               "Resources": resources})
        nonlocal battle_log
        battle_log = pd.concat([battle_log, event_log.to_frame().T], ignore_index=True)
        if verbose:
            print('Time: {:.2f}\t\tPotency: {}'.format(time, event_pot))

    # update time to next event
    def new_time():
        nonlocal time
        nonlocal buff_counter
        nonlocal action_queue
        nonlocal event_tracker

        time = round(np.min(event_tracker), 3)
        # check for action queue event
        if action_queue:
            time = round(min(time, action_queue[0][0]), 3)
        # check for buff queue event
        if buff_queue:
            time = round(min(time, buff_queue[0][0]), 3)
        # check for prepared queue event
        if prepared_queue:
            time = round(min(time, prepared_queue[0][0]), 3)

    # add a buff to the buff queue
    def heap_add(heap, time, actor, target, buff):
        nonlocal buff_counter

        if isinstance(buff, Chance):
            # buff/event has a probability to go off (some procs, for example)
            if np.random.rand() < buff.probability:
                heap_add(heap, time, actor, target, buff.val)
        else:
            heapq.heappush(heap, (round(time + actor.buffs[buff].delay, 3), buff_counter, actor.player_id, target, buff))

            buff_counter += 1

    # create battle log
    battle_log = pd.DataFrame(columns=["Time", "Player", "Type", "Ability", "Potency", "Crit Rate", "Dhit Rate",
                                       "Multiplier", "Flat Damage", "Full Damage", "Resources"])

    # initialize time
    prepull_time = -60.0
    time = prepull_time
    fight_length = fight_length  # fight duration (provided by user)
    # randomize boss enemy tick
    dot_tick = round(np.random.rand() * 3, 2)

    # initialize time tracking (abilities, autos, dots)
    event_tracker = np.zeros((3, len(actor_list)))
    # update with dot timers
    event_tracker[2] = [dot_tick] * len(actor_list)
    # look for prepull actions
    event_tracker[0] = [prepull_time] * len(actor_list)

    # create a delay queue for delayed buff effects
    buff_queue = []
    buff_counter = 0

    # create a delay queue for delayed actions
    action_queue = []

    # create a prepares queue for predefined actions to be used
    prepared_queue = []
    # Fill with predefined actions, if needed
    for actor in actor_list:
        if actor.actions_defined:
            print('here')
            # read actions
            with open(actor.rotation_file) as csvfile:
                reader = csv.DictReader(csvfile)
                for event in reader:
                    event_time = round(float(event['Time']), 3)

                    # First non-defined gcd time is provided in the file
                    if event['Action'] == 'next gcd':
                        continue

                    else:
                        # Get the action
                        action_name = event['Action']
                        player = actor.player_id
                        if action_name is not None:
                            if player in [0]:
                                print(f"Prepares: {action_name} \t\t\t time: {event_time}")
                            # put in action queue
                            heapq.heappush(prepared_queue, (round(event_time, 3), player, action_name))

                # update player and tracker for next event
                actor.next_gcd = event_time
                actor.next_ogcd = event_time
                actor.next_event = event_time
                print(actor.next_gcd)
                event_tracker[0, player] = actor_list[player].next_event

                print('done')

    ### Play through time ###
    while time <= fight_length:

        # if (time >= 0.0) and (time <= 20.0):
        #     print(f"gcd: {actor_list[0].next_gcd}")
        #     print(f"event: {actor_list[0].next_event} \t time:{time}")
        #     print(event_tracker)

        # Initiate any actions in the prepared queue
        if bool(prepared_queue):
            if prepared_queue[0][0] < time:
                print("Error: skipped a queue item (prepared)")
            elif prepared_queue[0][0] == time:
                # Get the first action
                _, player, action = heapq.heappop(prepared_queue)
                # Initiate the action
                action_name, delay = actor_list[player].initiate_action(action)
                if action_name is not None:
                    if player in [0]:
                        print(f"Input: {action_name} \t\t\t time: {time} \t\t\t resources: {actor_list[player].resources}")
                    # put in action queue
                    heapq.heappush(action_queue, (round(time + delay, 3), player, action_name))
                # update tracker for next event_pot
                event_tracker[0, player] = actor_list[player].next_event

        # Perform any effects that are ready from the buff queue
        if bool(buff_queue):
            if buff_queue[0][0] < time:
                print("Error: skipped a queue item (buffs)")
            elif buff_queue[0][0] == time:
                _, _, giver_id, target_player, buff = heapq.heappop(buff_queue)

                if target_player == 'team':
                    # apply team buffs
                    for actor in actor_list:
                        # update player's time
                        actor.update_time(time)
                        # apply buff
                        actor.apply_buff(buff, giver_id=giver_id)
                else:
                    actor = actor_list[target_player]
                    # update player's time
                    actor.update_time(time)
                    # apply given buff
                    actor.apply_buff(buff, giver_id=giver_id)

                # update time to next event and continue
                new_time()
                continue

        # perform any actions that are ready from the action queue
        if bool(action_queue):
            if action_queue[0][0] < time:
                print("Error: skipped a queue item (action)")
            elif action_queue[0][0] == time:
                _, player, action_name = heapq.heappop(action_queue)

                # update player's time
                actor_list[player].update_time(time)
                # execute action
                event_pot, (event_M, event_crit, event_dhit), event_buffs, event_type =\
                    actor_list[player].perform_action(action_name)
                log_event(time, player, event_type, action_name, event_pot, event_crit, event_dhit, event_M, actor_list[player].resources, verbose)
                if player in [0]:
                    print(f"Performs: {action_name} \t\t\t time: {time} \t\t\t resources: {actor_list[player].resources}")

                # distribute any given resources
                # Tech overrides Standard
                tech_override = False
                # check if player has any tracked buffs, and whether this action can give
                if (actor_list[player].buff_tracked) & (actor_list[player].actions[action_name].type == 'gcd'):
                    for buff in actor_list[player].tracked_buffs:
                        tracked_buff = actor_list[player].buffs[buff]

                        # Self-given buffs don't count (except Monk)
                        if buff != 'Self-Meditative':
                            if player == tracked_buff.buff_giver:
                                continue

                        if buff == 'TechEsprit':
                            # If Tech is up, then don't look at Standard, when it comes around
                            if tracked_buff.timer > 0:
                                tech_override = True
                        if (buff == 'StandardEsprit') & (tech_override):
                            continue

                        # check that the buff is still active, and roll the dice on rng
                        if (tracked_buff.timer > 0) & (tracked_buff.gift['rng'] > np.random.rand()):
                            # give the resource, without going over the max
                            actor_list[tracked_buff.buff_giver].resources[tracked_buff.gift['name']].amount =\
                                min(actor_list[tracked_buff.buff_giver].resources[tracked_buff.gift['name']].amount
                                    + tracked_buff.gift['value'],
                                    actor_list[tracked_buff.buff_giver].resources[tracked_buff.gift['name']].max)

                # put buffs in the queue
                team_buffs = event_buffs.get('team', [])
                self_buffs = event_buffs.get('self', [])
                target_buffs = event_buffs.get('target', [])
                for buff in team_buffs:
                    heap_add(buff_queue, time, actor_list[player], 'team', buff)
                for buff in self_buffs:
                    heap_add(buff_queue, time, actor_list[player], player, buff)
                for buff in target_buffs:
                    heap_add(buff_queue, time, actor_list[player], actor_list[player].buff_target, buff)

                # update time to next event and continue
                new_time()
                continue

        # either execute action or auto-attack as appropriate
        # find next event
        event_loc = np.unravel_index(np.argmin(event_tracker), event_tracker.shape)
        # player associated with this event
        player = event_loc[1]
        # update that player's time
        actor_list[player].update_time(time)

        # assume no buff unless told otherwise
        event_buff = []

        if verbose:
            print(event_tracker)
            print(event_loc)

        if event_loc[0] == 0:
            # select an action
            action_name, delay = actor_list[player].choose_action()
            if action_name is not None:
                if player in [0]:
                    print(f"{action_name} \t\t\t time: {time} \t\t\t resources: {actor_list[player].resources}")
                # put in action queue
                heapq.heappush(action_queue, (round(time+delay, 3), player, action_name))
            # update tracker for next event_pot
            event_tracker[0, player] = actor_list[player].next_event
        elif event_loc[0] == 1:
            # execute auto
            event_pot, (event_M, event_crit, event_dhit) = actor_list[player].inc_auto()
            event_type = "auto"
            log_event(time, player, event_type, "auto", event_pot, event_crit, event_dhit, event_M, actor_list[player].resources, verbose)
            # update tracker for next event_pot
            event_tracker[1, player] = actor_list[player].next_auto
        else:
            # execute dot tick
            for dot, tracker in actor_list[player].dots.items():
                # log each dot individually (could have different buff snapshots)
                if tracker.timer > 0:
                    event_pot, (event_M, event_crit, event_dhit) = tracker.potency, tracker.buff_snap
                    event_type = "dot tick"
                    log_event(time, player, event_type, "dot", event_pot, event_crit, event_dhit, event_M, actor_list[player].resources, verbose)

            # And execute actor ticks here
            actor_list[player].execute_actor_tick()

            # increment dot tracker
            event_tracker[2, player] = event_tracker[2, player] + 3

        # update time to next event
        new_time()

    # calculate damage from the DataFrame, individualized to each player
    for i in range(len(actor_list)):
        job_mod, trait, wd, ap, det, spd, wpn_delay, ten = actor_list[i].char_stats()

        # ability damage
        battle_log.loc[(battle_log['Player'] == i) & ((battle_log['Type'] == 'gcd') | (battle_log['Type'] == 'ogcd')), 'Flat Damage'] = \
            pot_to_dmg(battle_log['Potency'], job_mod, trait, wd, ap, det) * battle_log['Multiplier']

        # auto damage
        battle_log.loc[(battle_log['Player'] == i) & (battle_log['Type'] == 'auto'), 'Flat Damage'] = \
            auto_dmg(battle_log['Potency'], job_mod, trait, wd, ap, det, spd, wpn_delay)

        # dot damage
        battle_log.loc[(battle_log['Player'] == i) & (battle_log['Type'] == 'dot tick'), 'Flat Damage'] = \
            dot_dmg(battle_log['Potency'], job_mod, trait, wd, ap, det, spd)

    tot_dmg = battle_log['Flat Damage'].sum()

    return tot_dmg, battle_log


def damage_iteration(actor_list, sim_log):
    # "roll the dice"
    crit_dice = np.random.rand(len(sim_log['Potency']))
    dhit_dice = np.random.rand(len(sim_log['Potency']))
    # built in +/-5% damage variance
    dmg_dice = 0.95 + np.random.rand(len(sim_log['Potency'])) * 0.10

    # Add damage variance column
    sim_log['Dmg Variance'] = dmg_dice

    # evaluate for each player (b/c different crit multipliers)
    for k in range(len(actor_list)):
        crit_mult = 0.35 + actor_list[k].base_crit
        sim_log.loc[sim_log['Player'] == k, 'Crit Multiplier'] = \
            1 + (crit_mult) * (sim_log['Crit Rate'] > crit_dice)
        sim_log.loc[sim_log['Player'] == k, 'Dhit Multiplier'] = \
            1 + 0.25 * (sim_log['Dhit Rate'] > dhit_dice)

    # apply rng multipliers
    sim_log['Full Damage'] = np.floor(np.floor(np.floor(sim_log['Flat Damage'] * sim_log['Crit Multiplier']) *
                                      sim_log['Dhit Multiplier']) * sim_log['Dmg Variance'])


def plot_hist(dmg_list):
    # generate figure
    fig = plt.figure()

    # plot histogram
    plt.hist(dmg_list, bins=40)

    # adjust labels
    plt.title('Damage Histogram')
    plt.xlabel('Damage')
    plt.ylabel('Counts')

    # display plot
    plt.show()

