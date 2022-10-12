# Module for functions used in the simulations

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

    # create battle log
    battle_log = pd.DataFrame(columns=["Time", "Player", "Ability", "Potency", "Crit Rate", "Dhit Rate",
                                       "Buff Multiplier", "Flat Damage", "Full Damage"])

    # initialize time
    time = 0.0
    fight_length = fight_length  # fight duration (provided by user)
    # randomize boss enemy tick
    dot_tick = round(np.random.rand() * 3, 2)

    # initialize time tracking (abilities, autos, dots)
    event_tracker = np.zeros((3, len(actor_list)))
    # update with dot timers
    event_tracker[2] = [dot_tick] * len(actor_list)

    ### Play through time ###
    while time <= fight_length:

        # either execute action or auto-attack as appropriate
        # find next event
        event_loc = np.unravel_index(np.argmin(event_tracker), event_tracker.shape)
        # player associated with this event
        player = event_loc[1]
        # update that player's time
        actor_list[player].update_time(time)

        # assume no buff unless told otherwise
        event_buff = 'none'

        if verbose:
            print(event_tracker)
            print(event_loc)

        if event_loc[0] == 0:
            # execute action
            event_pot, (event_M, event_crit, event_dhit), event_buff = actor_list[player].choose_action()
            event_name = "gcd"
            # update tracker for next event_pot
            event_tracker[0, player] = actor_list[player].next_event
        elif event_loc[0] == 1:
            # execute auto
            event_pot, (event_M, event_crit, event_dhit) = actor_list[player].inc_auto()
            event_name = "auto"
            # update tracker for next event_pot
            event_tracker[1, player] = actor_list[player].next_auto
        else:
            # execute dot tick
            if verbose:
                print('A dot tick')
            event_pot = 0.0
            event_name = "dot tick"
            # increment dot tracker
            event_tracker[2, player] = event_tracker[2, player] + 3


        # log event_pot
        event_log = pd.Series({"Time": time, "Player": player, "Ability": event_name, "Potency": event_pot,
                               "Crit Rate": event_crit, "Dhit Rate": event_dhit, "Multiplier": event_M,
                               "Flat Damage": np.nan, "Full Damage": np.nan})
        battle_log = pd.concat([battle_log, event_log.to_frame().T], ignore_index=True)
        if verbose:
            print('Time: {:.2f}\t\tPotency: {}'.format(time, event_pot))

        # apply team buffs
        # TO-DO: team buffs should be applied after a short delay
        if event_buff != 'none':
            for actor in actor_list:
                actor.apply_buff(event_buff)

        # update time to next event_pot
        time = np.min(event_tracker)

    # calculate damage from the DataFrame, individualized to each player
    for i in range(len(actor_list)):
        job_mod, trait, wd, ap, det, spd, wpn_delay, ten = actor_list[i].char_stats()
        # to-do: include buff multipliers and trait eventually #

        # ability damage
        battle_log.loc[(battle_log['Player'] == i) & (battle_log['Ability'] == 'gcd'), 'Flat Damage'] = \
            pot_to_dmg(battle_log['Potency'], job_mod, trait, wd, ap, det) * battle_log['Multiplier']

        # auto damage
        battle_log.loc[(battle_log['Player'] == i) & (battle_log['Ability'] == 'auto'), 'Flat Damage'] = \
            auto_dmg(battle_log['Potency'], job_mod, trait, wd, ap, det, spd, wpn_delay)

        # dot damage
        battle_log.loc[(battle_log['Player'] == i) & (battle_log['Ability'] == 'dot tick'), 'Flat Damage'] = \
            dot_dmg(battle_log['Potency'], job_mod, trait, wd, ap, det, spd)

    tot_dmg = battle_log['Flat Damage'].sum()

    return tot_dmg, battle_log


def damage_iteration(actor_list, sim_log):
    # "roll the dice"
    crit_dice = np.random.rand(len(sim_log['Potency']))
    dhit_dice = np.random.rand(len(sim_log['Potency']))

    # evaluate for each player (b/c different crit multipliers)
    for k in range(len(actor_list)):
        crit_mult = 0.35 + (0.25)  # to-do: pull from actor
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

