# xiv-dmg-sim
 An in-progress damage simulator for FFXIV

# Current State
The simulator is currently only usable as a Dancer-specific damage simulator.
All other jobs are only present in a "dummy" state -- they will use their team-wide buffs and spam zero-potency GCDs --
this allows them to contribute to the Dancer's damage, through gauge generation and buffs.

# Running the Simulator
The simulator GUI can be accessed by running the xivSim.py script.

## Simulation Specifications
The following specifications must be provided:
+ "Number of Rotational Simulations" -- This is the number of times that you want the simulator to "play" through the course of a fight, choosing which skills and abilities to use.
+ "Number of Damage Sims per Rotation Sim" -- This is the number fo times that you want the simulator to generate the rng-dependent damage from each of the above playthroughs. This is where the rng from Critical and Direct hits is considered. Currently the +/- 5% damage variance that is inherent to the game is not included.
+ "Fight Duration" -- The length of the fight, in seconds, that you want to simulate.
+ Player info
  + "Job" -- The in-game job the player is using
  + In-game player stats:
    + "WD" -- Weapon Damage
    + "Main Stat" -- Mind, Strength, Dexterity, etc. This should be the non-party value; party bonuses will be added by the simulator based on the party composition provided.
    + "Speed Stat" -- Skill Speed or Spell Speed
    + "Crit" -- Critical Hit
    + "Dhit" -- Direct Hit
    + "Det" -- Determination

**The Dancer will always be partnered to "Player 1"! This means that a job must be selected for "Player 1".** All other players may be left empty if desired.

## Getting Results
Once all the specs are provided, the simulation can be started using the "Start Sim" button.
The two progress bars at the bottom will show the progress of the total Rotational Simulations and the
Damage Simulations within each of the Rotational Simulations.

Upon completion, a histogram of all the final damage values will be plotted on the right-hand side,
along with the mean and standard deviation being marked. The mean and standard deviation values will also be printed
beneath the plot.

### Data Output
The simulator will also save the specifications that were used for a simulation. Each time the simulation is run
it will output the following files into a "data" folder:
+ config.json -- a json file of the provided specifications
+ last_battle_log.csv -- a csv file of the Pandas Dataframe containing all the actions/skills used by all players during the last Rotational Simulation.
+ battle_log_player_n.csv -- a csv file of the same data, but limited to only the actions/skills of each single player.
+ damage_values.csv -- a csv file of all the resulting total fight damage values (those used to plot the histogram)
