# A damage simulator for Final Fantasy XIV teams

from simFunctions import sim_battle, damage_iteration
from charActors import ast, blm, drk, drg, dnc, pld, sam, sge, whm
from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np
import time
import json
import os


class XIVSimThread(QThread):
    battle_prog = pyqtSignal(int)
    damage_prog = pyqtSignal(int)
    result = pyqtSignal(list)

    def __init__(self, stats):
        super(XIVSimThread, self).__init__()
        self.stats = stats
        self.sim_result = 0

    def __del__(self):
        self.wait()

    def run(self):
        self.battle_prog.emit(0)
        self.damage_prog.emit(0)

        # time the run
        start_time = time.perf_counter()

        # Function to convert sent Str and/or None vals to int
        def int_val(val):
            if val is None:
                return 0
            else:
                return int(val)

        # Prep for role-bonuses to damage
        role_bonus = 1.0
        tank_list = ['DRK', 'GNB', 'PLD', 'WAR']
        tank_bonus = 0.01
        healer_list = ['AST', 'SCH', 'SGE', 'WHM']
        healer_bonus = 0.01
        melee_list = ['DRG', 'MNK', 'NIN', 'RPR', 'SAM']
        melee_bonus = 0.01
        caster_list = ['BLM', 'RDM', 'SMN']
        caster_bonus = 0.01
        ranged_list = ['BRD', 'DNC', 'MCH']
        ranged_bonus = 0.01

        # create character actors
        # Keep the actors in a list
        actor_list = []
        for i, player in enumerate(self.stats['players']):
            job = player['job']

            # update role bonus
            if job in tank_list:
                # Add the bonus for this role
                role_bonus += tank_bonus
                # Only get the bonus once
                tank_bonus = 0.0
            elif job in healer_list:
                role_bonus += healer_bonus
                healer_bonus = 0.0
            elif job in melee_list:
                role_bonus += melee_bonus
                melee_bonus = 0.0
            elif job in caster_list:
                role_bonus += caster_bonus
                caster_bonus = 0.0
            elif job in ranged_list:
                role_bonus += ranged_bonus
                ranged_bonus = 0.0

            # Gather Actor stats
            wd, main, spd, crit, dhit, det = int_val(player['stats']['WD']), int_val(player['stats']['Main Stat']),\
                                             int_val(player['stats']['Speed Stat']), int_val(player['stats']['Crit']),\
                                             int_val(player['stats']['Dhit']), int_val(player['stats']['Det'])

            # Create Actor
            if job == 'AST':
                actor = ast.Actor(wd, main, det, spd, crit, dhit, 3.12, player_id=i)
            elif job == 'BLM':
                actor = blm.Actor(wd, main, det, spd, crit, dhit, 3.12, player_id=i)
            elif job == 'DRK':
                actor = drk.Actor(wd, main, det, spd, crit, dhit, 3.12, player_id=i)
            elif job == 'DRG':
                actor = drg.Actor(wd, main, det, spd, crit, dhit, 3.12, player_id=i)
            elif job == 'DNC':
                actor = dnc.Actor(wd, main, det, spd, crit, dhit, 3.12, player_id=i, **player['specifics'])
            elif job == 'PLD':
                actor = pld.Actor(wd, main, det, spd, crit, dhit, 3.12, player_id=i)
            elif job == 'SAM':
                actor = sam.Actor(wd, main, det, spd, crit, dhit, 3.12, player_id=i, **player['specifics'])
            elif job == 'SGE':
                actor = sge.Actor(wd, main, det, spd, crit, dhit, 3.12, player_id=i, **player['specifics'])
            elif job == 'WHM':
                actor = whm.Actor(wd, main, det, spd, crit, dhit, 3.12, player_id=i)
            else:
                print("Failed actor")
                continue

            # Add Actor to the list
            actor_list.append(actor)

        '''player0 = dnc.Actor(126, 2949, 1721, 536, 2387, 1340, 3.12, player_id=0, partner=1)
        player1 = sam.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=1)
        player2 = drg.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=2)
        player3 = blm.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=2)
        player4 = ast.Actor(50, 2560, 1987, 650, 2000, 2000, 3.14, player_id=2)
        player5 = whm.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=2)
        player6 = drk.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=2)
        player7 = pld.Actor(50, 2560, 1987, 510, 2000, 2000, 3.14, player_id=2)
        actor_list = [player0, player1, player2, player3, player4, player5, player6, player7]'''

        # Replay the fight multiple times to build statistics
        # A list for holding all the generated fight damage values
        dmg_list = []
        # Collect the simulation properties
        battle_iterations = self.stats['sims']  # iterations for stochastic fight rotation variance
        rng_iterations = self.stats['iterations']  # iterations for stochastic damage variance (crit, dhit, etc.)
        fight_sim_duration = self.stats['fight duration']  # length of the fight in seconds

        self.battle_prog.emit(0)
        # Run the simulations
        for i in range(battle_iterations):
            # be sure to reset the actors between iterations
            [actor.reset() for actor in actor_list]
            # sim the fight
            dmg, sim_log = sim_battle(fight_sim_duration, actor_list, False)

            # Calculate stochastic damage multiple times to build statistics
            self.damage_prog.emit(0)
            for j in range(rng_iterations):
                # roll one damage iteration
                damage_iteration(actor_list, sim_log)

                # add to damage list
                dmg_list.append(sim_log['Full Damage'].sum())

                # Inform the GUI of the current progress
                self.damage_prog.emit(j + 1)
            # Inform the GUI of the current progress
            self.battle_prog.emit(i + 1)

            print('############### Battle Iteration {} Done ###############'.format(i + 1))

        # Apply party role composition bonus
        sim_log['Full Damage'] = sim_log['Full Damage'] * role_bonus
        sim_log['Flat Damage'] = sim_log['Flat Damage'] * role_bonus
        dmg_list = np.array(dmg_list) * role_bonus
        # Convert damage to dps
        dps_list = dmg_list / (fight_sim_duration - 3.5)

        print('First 20 rows of last battle sim:')
        print(sim_log.loc[sim_log['Player'] == 0][['Time', 'Player', 'Type', 'Multiplier', 'Crit Rate', "Full Damage"]][
              :60])

        # Save the sim configuration
        os.makedirs('data', exist_ok=True)
        json.dump(self.stats, open('data/sim_config.json', 'w'))
        # Save the last battle sim to csv
        sim_log.to_csv('data/last_battle_log.csv')
        # Save player-specific logs
        for actor in actor_list:
            player_id = actor.player_id
            sim_log.loc[sim_log['Player'] == player_id].to_csv(f'data/battle_log_player_{player_id}.csv')
        # Save the damage list
        np.savetxt('data/damage_values.csv', dps_list, delimiter=',')

        # Print the mean damage
        print(
            f"mean damage: {np.mean(dmg_list) / (fight_sim_duration - 3.5)}")  # subtracting 3.5 for the "prepull dance prep"

        # End timer
        print("~~ Time: {} seconds".format(time.perf_counter() - start_time))

        # Return the list of damages in a Signal
        self.sim_result = list(dps_list)
        self.result.emit(self.sim_result)


