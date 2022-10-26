# A damage simulator for Final Fantasy XIV teams

from simFunctions import sim_battle, damage_iteration, plot_hist
from charActors import dnc
import time

if __name__ == '__main__':
    # time the run
    start_time = time.perf_counter()

    # create character actors (by hand for now)
    y = dnc.Actor(120, 2560, 1987, 510, 2000, 2000, 3.14, partner=1)
    z = dnc.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, partner=0)
    actor_list = [y, z]

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
    print(sim_log[['Time', 'Player', 'Type', 'Potency', 'Multiplier', "Flat Damage", 'Crit Rate', "Full Damage"]][:60])

    # End timer
    print("~~ Time: {} seconds".format(time.perf_counter() - start_time))

    # plot the damage histogram
    plot_hist(dmg_list)

