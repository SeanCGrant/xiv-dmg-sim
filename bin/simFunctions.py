# Module for functions used in the simulations
import heapq

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


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
    def log_event(time, player, event_type, event_name, event_pot, event_crit, event_dhit, event_M, verbose):
        # create a line for the event, then add to the battle log
        event_log = pd.Series({"Time": time, "Player": player, "Type": event_type, "Ability": event_name,
                               "Potency": event_pot, "Crit Rate": event_crit, "Dhit Rate": event_dhit,
                               "Multiplier": event_M, "Flat Damage": np.nan, "Full Damage": np.nan})
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

        time = np.min(event_tracker)
        # check for action queue event
        if action_queue:
            time = min(time, action_queue[0][0])
        # check for buff queue event
        if buff_queue:
            time = min(time, buff_queue[0][0])

    # add a buff to the buff queue
    def heap_add(heap, time, actor, target, buff):
        nonlocal buff_counter

        if isinstance(buff, tuple):
            # buff/event has a probability to go off (some procs, for example)
            if np.random.rand() < buff[1]:
                heap_add(heap, time, actor, target, buff[0])
        else:
            heapq.heappush(heap, (time + actor.buffs[buff].delay, buff_counter, target, buff))

            buff_counter += 1

    # create battle log
    battle_log = pd.DataFrame(columns=["Time", "Player", "Type", "Ability", "Potency", "Crit Rate", "Dhit Rate",
                                       "Multiplier", "Flat Damage", "Full Damage"])

    # initialize time
    time = 0.0
    fight_length = fight_length  # fight duration (provided by user)
    # randomize boss enemy tick
    dot_tick = round(np.random.rand() * 3, 2)

    # initialize time tracking (abilities, autos, dots)
    event_tracker = np.zeros((3, len(actor_list)))
    # update with dot timers
    event_tracker[2] = [dot_tick] * len(actor_list)

    # create a delay queue for delayed buff effects
    buff_queue = []
    buff_counter = 0

    # create a delay queue for delayed actions
    action_queue = []

    ### Play through time ###
    while time <= fight_length:

        # Perform any effects that are ready from the buff queue
        if bool(buff_queue):
            if buff_queue[0][0] < time:
                print("Error: skipped a queue item (buffs)")
            elif buff_queue[0][0] == time:
                _, _, target_player, buff = heapq.heappop(buff_queue)

                if target_player == 'team':
                    # apply team buffs
                    for actor in actor_list:
                        # update player's time
                        actor.update_time(time)
                        # apply buff
                        actor.apply_buff(buff)
                else:
                    # update player's time
                    actor_list[target_player].update_time(time)
                    # apply self or targeted buff
                    actor_list[target_player].apply_buff(buff)

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
                event_pot, (event_M, event_crit, event_dhit), event_buffs =\
                    actor_list[player].perform_action(action_name)
                event_type = actor_list[player].actions[action_name].type
                log_event(time, player, event_type, action_name, event_pot, event_crit, event_dhit, event_M, verbose)

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
                if player == 0:
                    print(f"{action_name} \t\t\t time: {time} \t\t\t esprit: {actor_list[player].resources['esprit']}")
                # put in action queue
                heapq.heappush(action_queue, (time+delay, player, action_name))
            # update tracker for next event_pot
            event_tracker[0, player] = actor_list[player].next_event
        elif event_loc[0] == 1:
            # execute auto
            event_pot, (event_M, event_crit, event_dhit) = actor_list[player].inc_auto()
            event_type = "auto"
            log_event(time, player, event_type, "auto", event_pot, event_crit, event_dhit, event_M, verbose)
            # update tracker for next event_pot
            event_tracker[1, player] = actor_list[player].next_auto
        else:
            # execute dot tick
            for dot, tracker in actor_list[player].dots.items():
                # log each dot individually (could have different buff snapshots)
                if tracker.timer > 0:
                    event_pot, (event_M, event_crit, event_dhit) = tracker.potency, tracker.buff_snap
                    event_type = "dot tick"
                    log_event(time, player, event_type, "dot", event_pot, event_crit, event_dhit, event_M, verbose)

            # increment dot tracker
            event_tracker[2, player] = event_tracker[2, player] + 3

        # update time to next event
        new_time()

    # calculate damage from the DataFrame, individualized to each player
    for i in range(len(actor_list)):
        job_mod, trait, wd, ap, det, spd, wpn_delay, ten = actor_list[i].char_stats()
        # to-do: include buff multipliers and trait eventually #

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

    # evaluate for each player (b/c different crit multipliers)
    for k in range(len(actor_list)):
        crit_mult = 0.35 + actor_list[k].base_crit
        sim_log.loc[sim_log['Player'] == k, 'Crit Multiplier'] = \
            1 + (crit_mult) * (sim_log['Crit Rate'] > crit_dice)
        sim_log.loc[sim_log['Player'] == k, 'Dhit Multiplier'] = \
            1 + 0.25 * (sim_log['Dhit Rate'] > dhit_dice)

    # apply rng multipliers
    sim_log['Full Damage'] = sim_log['Flat Damage'] * sim_log['Crit Multiplier'] * sim_log['Dhit Multiplier']


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

