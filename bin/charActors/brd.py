from .baseActor import BaseActor, ActionDC, ResourceDC, BuffDC, BuffSelector, DotDC, Chance, Consume
import pandas as pd
import numpy as np


# Bard-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, *, player_id, **kwargs):
        print(kwargs)
        self.kwargs = kwargs

        # Bard-specific values
        jobMod = 115
        trait = 120

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, player_id=player_id, **kwargs)

        # Buff selectors for the various buffs associated with Armys Paeon repertoire stacks
        self._armys_selector = BuffSelector(self, [None, 'Armys Haste 1', 'Armys Haste 2', 'Armys Haste 3',
                                                   'Armys Haste 4'],
                                            ['Repertoire-Armys'], mode='count')
        self._armys_ethos_selector = BuffSelector(self, [None, 'Armys Ethos 1', 'Armys Ethos 2', 'armys Ethos 3',
                                                         'Armys Ethos 4'],
                                                  ['Repertoire-Armys'], mode='count')

        # override auto potency
        self.auto_potency = 90 * (self.wpn_delay / 3.0)  # TO-DO: check this value

        # Stickers
        self.stickers = {'Mages Coda': False, 'Wanderers Coda': False, 'Armys Coda': False}

        # BRD specific resources
        self.resources = {'Pitch Perfect': ResourceDC(3), 'Repertoire-Armys': ResourceDC(4),
                          'Soul Voice': ResourceDC(100)}

        # BRD personal buffs
        buffs = {'Straight Shot Ready': BuffDC('logistic', 30.0), 'Barrage': BuffDC('logistic', 10.0),
                 'Blast Arrow Ready': BuffDC('logistic', 10.0),
                 'Armys Song': BuffDC('logistic', 45.0, removal_additions=[self._armys_end]),
                 'Armys Ethos 1': BuffDC('logistic', 30.0), 'Armys Ethos 2': BuffDC('logistic', 30.0),
                 'Armys Ethos 3': BuffDC('logistic', 30.0), 'Armys Ethos 4': BuffDC('logistic', 30.0),
                 'Armys Haste 1': BuffDC('spd', 100.0, 0.04), 'Armys Haste 2': BuffDC('spd', 100.0, 0.08),
                 'Armys Haste 3': BuffDC('spd', 100.0, 0.12), 'Armys Haste 4': BuffDC('spd', 100.0, 0.16),
                 'Armys Muse 1': BuffDC('spd', 100.0, 0.01), 'Armys Muse 2': BuffDC('spd', 100.0, 0.02),
                 'Armys Muse 3': BuffDC('spd', 100.0, 0.04), 'Armys Muse 4': BuffDC('spd', 100.0, 0.12),
                 'Raging Strikes': BuffDC('dmg', 20.0, 1.15)}
        self.buffs.update(buffs)

        # BRD actions
        actions = {'Burst Shot': ActionDC('gcd', 220, self.gcd_time, self.gcd_time,
                                          buff_effect={'self': [Chance('Straight Shot Ready', 0.35)]},
                                          buff_removal_opt=['Barrage']),
                   'Refulgent Arrow': ActionDC('gcd', 280, self.gcd_time, self.gcd_time,
                                               buff_removal=['Straight Shot Ready'],
                                               buff_removal_opt=['Barrage']),
                   'Caustic Bite': ActionDC('gcd', 150, self.gcd_time, self.gcd_time,
                                            buff_effect={'self': [Chance('Straight Shot Ready', 0.35)]},
                                            buff_removal_opt=['Barrage'],
                                            dot_effect='Caustic Bite'),
                   'Stormbite': ActionDC('gcd', 100, self.gcd_time, self.gcd_time,
                                         buff_effect={'self': [Chance('Straight Shot Ready', 0.35)]},
                                         buff_removal_opt=['Barrage'],
                                         dot_effect='Stormbite'),
                   'Iron Jaws': ActionDC('gcd', 100, self.gcd_time, self.gcd_time,
                                         buff_effect={'self': [Chance('Straight Shot Ready', 0.35)]},
                                         buff_removal_opt=['Barrage'],
                                         additional_effect=[self._iron_func]),
                   'Apex Arrow': ActionDC('gcd', self.scale_potency(100, 5, 'Soul Voice', resource_base=20), self.gcd_time, self.gcd_time,
                                          resource={'Soul Voice': Consume(20)},
                                          additional_effect=[self._apex_func]),
                   'Blast Arrow': ActionDC('gcd', 600, self.gcd_time, self.gcd_time,
                                           buff_removal=['Blast Arrow Ready']),
                   'Bloodletter': ActionDC('ogcd', 110, 0.0,
                                           max_charges=3,
                                           charge_time=15.0),
                   'Empyreal Arrow': ActionDC('ogcd', 230, 15.0,
                                              additional_effect=[self._empyreal_func]),
                   'Sidewinder': ActionDC('ogcd', 300, 60.0),
                   'Mages Ballad': ActionDC('ogcd', 100, 120.0,
                                            sticker_gain=['Mages Coda'],
                                            buff_effect=BuffSelector(self, [{'team': ['Mages Ballad'], 'self':['Armys Muse 4']}, {'team': ['Mages Ballad'], 'self':['Armys Muse 4']},
                                                                            {'team': ['Mages Ballad'], 'self':['Armys Muse 3']}, {'team': ['Mages Ballad'], 'self':['Armys Muse 3']},
                                                                            {'team': ['Mages Ballad'], 'self':['Armys Muse 2']}, {'team': ['Mages Ballad'], 'self':['Armys Muse 3']},
                                                                            {'team': ['Mages Ballad'], 'self':['Armys Muse 1']}, {'team': ['Mages Ballad'], 'self':['Armys Muse 1']},
                                                                            {'team': ['Mages Ballad']}],
                                                                     ['Armys Ethos 4', 'Armys Haste 4', 'Armys Ethos 3', 'Armys Haste 3', 'Armys Ethos 2', 'Armys Haste 2', 'Armys Ethos 1', 'Armys Haste 1'],
                                                                     mode='type')),
                   'Wanderers Minuet': ActionDC('ogcd', 100, 120.0,
                                                sticker_gain=['Wanderers Coda'],
                                                buff_effect=BuffSelector(self,
                                                                         [{'team': ['Wanderers Minuet'], 'self':['Armys Muse 4']}, {'team': ['Mages Ballad'], 'self':['Armys Muse 4']},
                                                                          {'team': ['Wanderers Minuet'], 'self':['Armys Muse 3']}, {'team': ['Mages Ballad'], 'self':['Armys Muse 3']},
                                                                          {'team': ['Wanderers Minuet'], 'self':['Armys Muse 2']}, {'team': ['Mages Ballad'], 'self':['Armys Muse 3']},
                                                                          {'team': ['Wanderers Minuet'], 'self':['Armys Muse 1']}, {'team': ['Mages Ballad'], 'self':['Armys Muse 1']},
                                                                          {'team': ['Wanderers Minuet']}],
                                                                         ['Armys Ethos 4', 'Armys Haste 4', 'Armys Ethos 3',
                                                                          'Armys Haste 3', 'Armys Ethos 2', 'Armys Haste 2',
                                                                          'Armys Ethos 1', 'Armys Haste 1'],
                                                                         mode='type')),
                   'Armys Paeon': ActionDC('ogcd', 100, 120.0,
                                           sticker_gain=['Armys Coda'],
                                           buff_effect={'team': ['Armys Paeon'], 'self': ['Armys Song']}),
                   'Pitch Perfect': ActionDC('ogcd', self.step_potency([0, 100, 220, 360], resource='Pitch Perfect'), 1.0,
                                             resource={'Pitch Perfect': Consume(1)}),
                   'Barrage': ActionDC('ogcd', 0, 120.0,
                                       buff_effect={'self': ['Barrage', 'Straight Shot Ready']}),
                   'Raging Strikes': ActionDC('ogcd', 0, 120.0,
                                              buff_effect={'self': ['Raging Strikes']}),
                   'Battle Voice': ActionDC('ogcd', 0, 120.0,
                                            buff_effect={'team': ['Battle Voice']}),
                   'Radiant Finale': ActionDC('ogcd', 0, 110.0,
                                              buff_effect=BuffSelector(self, [{'team': ['Radiant Finale 1']}, {'team': ['Radiant Finale 2']}, {'team': ['Radiant Finale 3']}],
                                                                       ['Mages Coda', 'Wanderers Coda', 'Armys Coda'],
                                                                       mode='sticker count'),
                                              sticker_removal_opt=['Mages Coda', 'Wanderers Coda', 'Armys Coda'])
                   }
        self.actions.update(actions)

        # dnc dots
        dots = {'Caustic Bite': DotDC(20, 45.0), 'Stormbite': DotDC(25, 45.0)}
        self.dots.update(dots)

    def choose_action(self):
        # determine current action, based on current buffs/procs

        if self.next_event == self.next_gcd:
            # Prepull
            if self.next_event < 0.0:
                # Jump to -15 sec if needed
                if self.next_event < -15.0:
                    # Wait for 15 sec before pull
                    self.next_gcd = 0.0
                    self.next_event = self.next_gcd
                    return None, 0.0

            # use a GCD
            # Use dots if they aren't up already
            if not self.dots['Stormbite'].active():
                action = 'Stormbite'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            if not self.dots['Caustic Bite'].active():
                action = 'Caustic Bite'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            # Use Iron Jaws if dots will fall off soon
            if (self.dots['Stormbite'].timer < self.gcd_time) | (self.dots['Caustic Bite'].timer < self.gcd_time):
                action = 'Iron Jaws'
                if self.allowed_action(action):
                    return self.initiate_action(action)

            # Use Blast Arrow quickly when available
            action = 'Blast Arrow'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Use Apex Arrow at 90 gauge?
            if self.resources['Soul Voice'].amount >= 90:
                action = 'Apex Arrow'
                if self.allowed_action(action):
                    return self.initiate_action(action)

            # Basic GCD actions
            # Refulgent if available
            action = 'Refulgent Arrow'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Burst Shot otherwise
            action = 'Burst Shot'
            if self.allowed_action(action):
                return self.initiate_action(action)

        else:
            # consider using oGCDs
            if round(self.next_event + self.anim_lock, 3) > self.next_gcd:
                # don't clip gcd
                return self.go_to_gcd()

            # Sing us a song
            # If not singing already
            if not (self.buffs['Wanderers Minuet'].active() | self.buffs['Armys Paeon'].active() |
                    self.buffs['Mages Ballad'].active()):
                if not self.stickers['Wanderers Coda']:
                    action = 'Wanderers Minuet'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                if not self.stickers['Armys Coda']:
                    action = 'Armys Paeon'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                if not self.stickers['Mages Coda']:
                    action = 'Mages Ballad'
                    if self.allowed_action(action):
                        return self.initiate_action(action)

            # Use the buffing oGCDs
            action = 'Raging Strikes'
            if self.allowed_action(action):
                return self.initiate_action(action)
            action = 'Battle Voice'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Radiant Finale at 3 stacks
            if (self.stickers['Mages Coda']) & (self.stickers['Armys Coda']) & (self.stickers['Wanderers Coda']):
                action = 'Radiant Finale'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            action = 'Barrage'
            if self.allowed_action(action):
                return self.initiate_action(action)

            # Use damage oGCDs
            action = 'Empyreal Arrow'
            if self.allowed_action(action):
                return self.initiate_action(action)
            action = 'Sidewinder'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Use Pitch Perfect if at 3 stacks
            if self.resources['Pitch Perfect'].amount == self.resources['Pitch Perfect'].max:
                action = 'Pitch Perfect'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            # Use Bloodletter if close to capping or under buffs
            if (self.actions['Bloodletter'].charge_count == 2) | (self.buffs['Raging Strikes'].active()):
                action = 'Bloodletter'
                if self.allowed_action(action):
                    return self.initiate_action(action)

            return self.go_to_gcd()

    def perform_action(self, action):
        # Determine whether to send this hit multiple times (Barrage's effect)
        barrage = ('Barrage' in self.actions[action].buff_removal_opt) & (self.buffs['Barrage'].active())

        # Call the basic perform_action function
        potency, (m, crit, dhit), buff_effect, action_type, multihit = BaseActor.perform_action(self, action)

        # Barrage makes an ability hit three times
        if barrage:
            multihit = 3

        # Return the values with the updated multihit
        return potency, (m, crit, dhit), buff_effect, action_type, multihit

    def execute_actor_tick(self, rng=0.8):
        # Execute the base function
        BaseActor.execute_actor_tick(self)

        # Check if a song is up
        if (self.buffs['Wanderers Minuet'].active() | self.buffs['Armys Paeon'].active() |
                self.buffs['Mages Ballad'].active()):

            # Chance of giving a tick
            if np.random.rand() >= rng:
                # do not trigger effects
                return

            # Give Soul Voice gauge
            self.add_resource('Soul Voice', 5)

            # Give appropriate song effect
            if self.buffs['Mages Ballad'].active():
                # Reduce timer on bloodletter
                self.actions['Bloodletter'].update_time(7.5)

            if self.buffs['Wanderers Minuet'].active():
                # Give a Pitch Perfect stack
                self.add_resource('Pitch Perfect', 1)

            if self.buffs['Armys Paeon'].active():
                # Do nothing if already capped on stacks
                if self.resources['Repertoire-Armys'] == 4:
                    return
                # Remove old haste buff, if present
                if self.resources['Repertoire-Armys'].amount > 0:
                    self.remove_buff(self._armys_selector.select())
                # Give a stack of haste
                self.add_resource('Repertoire-Armys', 1)
                # Add new haste buff
                #print(f"give haste: {self._armys_selector.select()}")
                self.apply_buff(self._armys_selector.select())

    def _iron_func(self):
        if self.dots['Caustic Bite'].active():
            self.apply_dot('Caustic Bite')
        if self.dots['Stormbite'].active():
            self.apply_dot('Stormbite')

    def _apex_func(self):
        # Check if the actor has 80 or more gauge
        if self.resources['Soul Voice'].amount >= 80:
            # Give Blast Arrow buff
            self.apply_buff('Blast Arrow Ready')

    def _empyreal_func(self):
        # Trigger the song effects with no rng
        self.execute_actor_tick(rng=1.0)

    def _armys_end(self):
        # remove haste when Armys Paeon ends
        self.remove_buff(self._armys_selector.select())
        # Grant the appropriate Armys Ethos if there are Repertoire stacks
        if self.resources['Repertoire-Armys'].amount > 0:
            self.apply_buff(self._armys_ethos_selector.select())
        # Remove the repertoire stacks
        self.resources['Repertoire-Armys'].amount = 0

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay,
                      player_id=self.player_id, **self.kwargs)






