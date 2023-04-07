from .baseActor import BaseActor, ActionDC, BuffDC, BuffSelector, DotDC, ResourceDC, Chance, Consume, piety_to_mp
import pandas as pd
import numpy as np


# Astrologian-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, *, piety=390, player_id, **kwargs):

        self.kwargs = kwargs

        # Astrologian-specific values
        jobMod = 115
        trait = 130

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, player_id=player_id, **kwargs)

        # Adjust mp tick based on piety
        self.mp_tick = 200 + piety_to_mp(piety)

        # override auto potency
        self.auto_potency = 1  # TO-DO: check this value

        # Create a priority list for giving out AST cards
        self.card_priority = {'Melee': [1, 2, 6], 'Ranged': [3, 4, 5]}
        # Control who will get the next card
        self.buff_target = 0
        # Track who has a card buff, and how long it has left
        self.active_card_buffs = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0}

        # Stickers
        self.stickers = {'Solar Sign': False, 'Lunar Sign': False, 'Celestial Sign': False, 'Lord of Crowns': False,
                         'Solar Card': False, 'Lunar Card': False, 'Celestial Card': False,
                         'Melee Card': False, 'Ranged Card': False,
                         'card in hand': False}

        # ast specific resources
        self.resources = {'Astrosign': ResourceDC(3), 'mp': ResourceDC(max=10000, amount=10000)}

        # ast personal buffs
        buffs = {'Harmony of Spirit': BuffDC('logistic', 15.0), 'Harmony of Body': BuffDC('spd', 15.0, 0.1),
                 'Harmony of Mind': BuffDC('dmg', 15.0, 1.05), 'Lightspeed': BuffDC('spd', 15.0, 1.0),
                 'Lucid Dreaming': BuffDC('logistic', 21.0)}
        self.buffs.update(buffs)

        # ast actions
        actions = {'Divination': ActionDC('ogcd', 0, 120.0,
                                          buff_effect={'team': ['Divination']}),
                   'GCD-dummy': ActionDC('gcd', 0, self.gcd_time, self.gcd_time,
                                         cast_time=(1.5 - 0.5)),
                   'Fall Malefic': ActionDC('gcd', 250, self.gcd_time, self.gcd_time,
                                            cast_time=(1.5 - 0.5),
                                            resource={'mp': -400}),
                   'Combust III': ActionDC('gcd', 0, self.gcd_time, self.gcd_time,
                                           dot_effect='Combust III',
                                           resource={'mp': -400}),
                   'Macrocosmos': ActionDC('gcd', 250, self.gcd_time, self.gcd_time,
                                           resource={'mp': -600}),
                   'Earthly Star': ActionDC('ogcd', 310, 60.0,
                                            delay_on_perform=20.0),
                   'Lord of Crowns': ActionDC('ogcd', 250, 1.0,
                                              sticker_removal=['Lord of Crowns']),
                   'Draw': ActionDC('ogcd', 0, 1.0,
                                    max_charges=2,
                                    charge_time=30.0,
                                    resource={'mp': 500},
                                    sticker_gain=['card in hand'],
                                    additional_effect=[self._draw_card_func]),
                   'Play': ActionDC('ogcd', 0, 1.0,
                                    buff_effect={'target': ['AST Card']},
                                    sticker_removal=['card in hand'],
                                    sticker_removal_opt=['Solar Card', 'Lunar Card', 'Celestial Card',
                                                         'Melee Card', 'Ranged Card'],
                                    additional_effect=[self._play_card_func]),
                   'Minor Arcana': ActionDC('ogcd', 0, 60.0,
                                            sticker_gain=[Chance('Lord of Crowns', 0.5)]),
                   'Lightspeed': ActionDC('ogcd', 0, 90.0,
                                          buff_effect={'self': ['Lightspeed']}),
                   'Astrodyne': ActionDC('ogcd', 0, 1.0,
                                         buff_effect=BuffSelector(self, [{'self': ['Harmony of Spirit']},
                                                                         {'self': ['Harmony of Spirit', 'Harmony of Body']},
                                                                         {'self': ['Harmony of Spirit', 'Harmony of Body', 'Harmony of Mind']}],
                                                                  ['Solar Sign', 'Lunar Sign', 'Celestial Sign'],
                                                                  mode='type'),
                                         sticker_removal_opt=['Solar Sign', 'Lunar Sign', 'Celestial Sign'],
                                         resource={'Astrosign': -3}),
                   'Lucid Dreaming': ActionDC('ogcd', 0, 60.0,
                                              buff_effect={'self': ['Lucid Dreaming']})}
        self.actions.update(actions)

        # ast dots
        dots = {'Combust III': DotDC(50, 30.0, self.buff_state())}
        self.dots.update(dots)

    def choose_action(self):
        # determine current action, based on current buffs/procs

        if self.next_event == self.next_gcd:
            # use a GCD

            # Prepull
            if self.next_event < 0.0:
                # Jump to -30 sec if needed
                if self.next_event < -30.0:
                    # Wait for 30 sec before pull
                    self.next_gcd = -30.0
                    self.next_event = self.next_gcd
                    return None, 0.0
                if self.next_event >= -30.0:
                    # Draw a card
                    current_time = self.next_event
                    self.initiate_action('Draw')
                    self.next_gcd = 0.0
                    self.next_event = self.next_gcd
                    return 'Draw', 0.0

            # Reapply DoT if about to fall off
            if self.dots['Combust III'].timer <= 1.5:
                action = 'Combust III'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            # Use Rapture and Misery at will for now
            action = 'Fall Malefic'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Cover no allowed actions (no mp, for instance)
            return self.go_to_tick()

        else:
            #oGCDs

            if round(self.next_event + self.anim_lock, 3) > self.next_gcd:
                # don't clip the gcd
                return self.go_to_gcd()

            # use Div first chance under Tech
            if self.buffs['Technical'].timer > 0:
                action = 'Divination'
                if self.allowed_action(action):
                    return self.initiate_action(action)

            # Warning: not much thought put into this order
            # # Start with Lightspeed
            # action = 'Lightspeed'
            # if self.allowed_action(action):
            #     return self.initiate_action(action)
            # Use Astrodyne when available
            action = 'Astrodyne'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Draw when not holding a card
            if not self.stickers['card in hand']:
                action = 'Draw'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            # Minor Arcana
            action = 'Minor Arcana'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Earthly Star
            action = 'Earthly Star'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Use Divination around here
            action = 'Divination'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Play cards
            action = 'Play'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Play any Lords
            action = 'Lord of Crowns'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Use Lucid when available and not near full mp
            if self.resources['mp'].amount < 9000:
                action = 'Lucid Dreaming'
                if self.allowed_action(action):
                    return self.initiate_action(action)
            # no other oGCDs on the dummy actor
            return self.pass_ogcd()

    def execute_actor_tick(self):
        # Execute the base function
        BaseActor.execute_actor_tick(self)

        # Add mp
        # Base actor mp tick
        mp_tick = self.mp_tick
        # Check for Lucid
        if self.buffs['Lucid Dreaming'].active():
            # Add the Lucid value
            mp_tick += 550
        # And check for Harmony of Spirit
        if self.buffs['Harmony of Spirit'].active():
            # Add mp value  TO-DO: check the value
            mp_tick += 50

        self.add_resource('mp', mp_tick)

    def _draw_card_func(self):
        # Remove any old cards
        for sticker in ['Melee Card', 'Ranged Card', 'Solar Card', 'Lunar Card', 'Celestial Card']:
            self.remove_sticker(sticker)

        # Give a new card combination
        card_type = np.random.choice(['Melee Card', 'Ranged Card'])
        card_affinity = np.random.choice(['Solar Card', 'Lunar Card', 'Celestial Card'])
        self.add_sticker(card_type)
        self.add_sticker(card_affinity)

    def _play_card_func(self):
        # Change target based on the current card in hand.
        if self.stickers['Melee Card']:
            # Look at melee players
            for player in self.card_priority['Melee']:
                # Skip a player if they already have a card up
                if self.active_card_buffs[player] > 1.0:
                    continue
                # Give this player the card otherwise
                self.buff_target = self.card_priority['Melee'][0]
        else:
            # Look at ranged players
            for player in self.card_priority['Ranged']:
                # Skip this player if they have a card up
                if self.active_card_buffs[player] > 1.0:
                    continue
                # Give this player the card otherwise
                self.buff_target = self.card_priority['Ranged'][0]

        # Remember that this player got a 15 sec card
        self.active_card_buffs[self.buff_target] = 15.0

        # Give appropriate astrosign affinity
        if self.stickers['Solar Card']:
            self.add_sticker('Solar Sign')
        elif self.stickers['Lunar Card']:
            self.add_sticker('Lunar Sign')
        else:
            self.add_sticker('Celestial Sign')

        # And tick up the astrosign count by 1
        self.add_resource('Astrosign', 1)

    def update_time(self, current_time):
        # adjust player timers based on how long it has been since the last update
        time_change = round(current_time - self.last_time_check, 3)

        # don't need to do anything if time is already caught up
        if time_change == 0.0:
            return

        # Call the base function
        BaseActor.update_time(self, current_time)

        # update all card timers
        for player, time in self.active_card_buffs.items():
            self.active_card_buffs[player] = round(max(0.0, time - time_change), 3)

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay,
                      player_id=self.player_id, **self.kwargs)






