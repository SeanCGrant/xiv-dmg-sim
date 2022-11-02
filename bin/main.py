# A damage simulator for Final Fantasy XIV teams

from simFunctions import sim_battle, damage_iteration, plot_hist
from charActors import ast, blm, drk, drg, dnc, pld, sam, whm
import time
import numpy as np

if __name__ == '__main__':
    # time the run
    start_time = time.perf_counter()

    # create character actors (by hand for now)
    player0 = dnc.Actor(126, 2949, 1721, 536, 2387, 1340, 3.12, player_id=0, partner=1)
    player1 = sam.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=1)
    player2 = drg.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=2)
    player3 = blm.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=2)
    player4 = ast.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=2)
    player5 = whm.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=2)
    player6 = drk.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=2)
    player7 = pld.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=2)
    actor_list = [player0, player1, player2, player3, player4, player5, player6, player7]

    # Replay the fight multiple times to build statistics
    dmg_list = []
    battle_iterations = 1  # iterations for stochastic fight rotation variance
    rng_interatons = 100  # iterations for stochastic damage variance (crit, dhit, etc.)
    fight_sim_duration = 360.0  # length of the fight in seconds

    for i in range(battle_iterations):
        # be sure to reset the actors between iterations
        [actor.reset() for actor in actor_list]
        # sim the fight
        dmg, sim_log = sim_battle(fight_sim_duration, actor_list, False)

        # Calculate stochastic damage multiple times to build statistics
        for j in range(rng_interatons):
            # roll one damage iteration
            damage_iteration(actor_list, sim_log)

            # add to damage list
            dmg_list.append(sim_log['Full Damage'].sum())

        print('############### Battle Iteration {} Done ###############'.format(i+1))

    print('First 20 rows of last battle sim:')
    print(sim_log.loc[sim_log['Player']==0][['Time', 'Player', 'Type', 'Multiplier', 'Crit Rate', "Full Damage"]][:60])

    print(f"mean damage: {np.mean(dmg_list) / (fight_sim_duration - 3.5)}")

    # End timer
    print("~~ Time: {} seconds".format(time.perf_counter() - start_time))

    # plot the damage histogram
    plot_hist(dmg_list)

