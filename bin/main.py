# A damage simulator for Final Fantasy XIV teams

from simFunctions import sim_battle, damage_iteration, plot_hist
from charActors import ast, blm, brd, drk, drg, dnc, mch, mnk, pld, rpr, sam, sge, whm
import time
import numpy as np

if __name__ == '__main__':
    # time the run
    start_time = time.perf_counter()

    # create character actors (by hand for now)
    # 126, 2949, 1721, 536, 2387, 1340, 3.12
    player0 = rpr.Actor(126, 3093, 1721, 536, 2387, 1376, 2.56, player_id=0)
    player1 = brd.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=1)
    player2 = drg.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=2)
    player3 = blm.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=3)
    player4 = sge.Actor(50, 2560, 1987, 650, 2000, 2000, 3.14, player_id=4)
    player5 = whm.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=5)
    player6 = drk.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=6)
    player7 = pld.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=7)
    actor_list = [player0, player1, player2, player3, player4, player5, player6, player7]

    # Replay the fight multiple times to build statistics
    dmg_list = []
    battle_iterations = 1  # iterations for stochastic fight rotation variance
    rng_iterations = 100  # iterations for stochastic damage variance (crit, dhit, etc.)
    fight_sim_duration = 480.0  # length of the fight in seconds

    for i in range(battle_iterations):
        # be sure to reset the actors between iterations
        [actor.reset() for actor in actor_list]
        # sim the fight
        dmg, sim_log = sim_battle(fight_sim_duration, actor_list, False)

        # Calculate stochastic damage multiple times to build statistics
        for j in range(rng_iterations):
            # roll one damage iteration
            damage_iteration(actor_list, sim_log)

            # add to damage list (first player only)
            dmg_list.append(sim_log.loc[sim_log['Player']==0]['Full Damage'].sum())

        print('############### Battle Iteration {} Done ###############'.format(i+1))

    print('First 20 rows of last battle sim:')
    print(sim_log.loc[(sim_log['Player']==0) & (sim_log['Type']=='gcd')][['Time', 'Player', 'Type', 'Potency', 'Multiplier', 'Dhit Rate', 'Crit Rate', "Full Damage"]][:60])

    print(f"mean damage: {1.05 * np.mean(dmg_list) / fight_sim_duration}")  # added party bonus

    # End timer
    print("~~ Time: {} seconds".format(time.perf_counter() - start_time))

    # plot the damage histogram
    plot_hist(dmg_list)

