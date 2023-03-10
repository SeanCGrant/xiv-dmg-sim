from .baseActor import BaseActor, ActionDC, ResourceDC, BuffDC, BuffSelector, BuffConditional, TargetedBuff, DotDC,\
    Chance, Consume, spd_from_stat
import pandas as pd
import numpy as np


# monk-specific Actor
class Actor(BaseActor):
    def __init__(self, wd, ap, det, spd, crit, dhit, wpn_delay, *, player_id, **kwargs):
        print(kwargs)
        self.kwargs = kwargs

        # Monk-specific values
        jobMod = 110
        trait = 100

        super().__init__(jobMod, trait, wd, ap, det, spd, crit, dhit, wpn_delay, player_id=player_id, **kwargs)

        # override auto potency
        self.auto_potency = 90 * (self.wpn_delay / 3.0)  # TO-DO: check this value
        # and adjust for 2.0s GCD
        self.gcd_time = spd_from_stat(spd, 2000) + 0.005  # [fps estimate included]

        # mnk specific resources
        self.resources = {'chakra': ResourceDC(5, 5), 'Lunar Nadi': ResourceDC(1), 'Solar Nadi': ResourceDC(1)}

        # mnk personal buffs
        buffs = {'Riddle of Fire': BuffDC('dmg', 20.0, 1.15), 'Disciplined Fist': BuffDC('dmg', 15.0, 1.15),
                 'Riddle of Wind': BuffDC('auto-spd', 15.0, 0.5),
                 'Oppo-oppo': BuffDC('logistic', 30.0), 'Raptor': BuffDC('logistic', 30.0),
                 'Coeurl': BuffDC('logistic', 30.0), 'Formless Fist': BuffDC('logistic', 30.0),
                 'Perfect Balance 1': BuffDC('logistic', 20.0), 'Perfect Balance 2': BuffDC('logistic', 20.0),
                 'Perfect Balance 3': BuffDC('logistic', 20.0),
                 'Beast-Oppo-oppo': BuffDC('logistic', 40.0), 'Beast-Raptor': BuffDC('logistic', 40.0),
                 'Beast-Coeurl': BuffDC('logistic', 40.0), 'Blitz': BuffDC('logistic', 20.0),
                 'Leaden Fist': BuffDC('logistic', 30.0),
                 'Self-Meditative': TargetedBuff('given', 15.0, gift={'name': 'chakra', 'value': 1, 'rng': 1.0})}
        self.buffs.update(buffs)

        self.tracked_buffs += ['Self-Meditative']

        # mnk actions
        actions = {'Bootshine': ActionDC('gcd', self.combo_potency([210, 310], 'Leaden Fist'),
                                         self.gcd_time, self.gcd_time,
                                         buff_effect=BuffSelector(self, [{'self': ['Beast-Oppo-oppo']}, {'self': ['Beast-Oppo-oppo']}, {'self': ['Beast-Oppo-oppo', 'Blitz']}, {'self': ['Raptor']}, {'self': ['Raptor']}, {'self': ['Raptor']}],
                                                                  ['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1', 'Oppo-oppo', 'Formless Fist'], mode='type'),
                                         buff_removal_opt=[['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1'], 'Oppo-oppo', 'Formless Fist', 'Leaden Fist'],
                                         autocrit=BuffConditional(self, ['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1', 'Oppo-oppo', 'Formless Fist'])),
                   'Dragon Kick': ActionDC('gcd', 320, self.gcd_time, self.gcd_time,
                                           buff_effect=BuffSelector(self, [{'self': ['Beast-Oppo-oppo', 'Leaden Fist']}, {'self': ['Beast-Oppo-oppo', 'Leaden Fist']}, {'self': ['Beast-Oppo-oppo', 'Blitz', 'Leaden Fist']}, {'self': ['Raptor', 'Leaden Fist']}, {'self': ['Raptor', 'Leaden Fist']}, {'self': ['Raptor']}],
                                                                  ['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1', 'Oppo-oppo', 'Formless Fist'], mode='type'),
                                           buff_removal_opt=[['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1'], 'Oppo-oppo', 'Formless Fist']),
                   'True Strike': ActionDC('gcd', 300, self.gcd_time, self.gcd_time,
                                           buff_effect=BuffSelector(self, [{'self': ['Beast-Raptor']}, {'self': ['Beast-Raptor']}, {'self': ['Beast-Raptor', 'Blitz']}, {'self': ['Coeurl']}, {'self': ['Coeurl']}],
                                                                  ['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1', 'Raptor', 'Formless Fist'], mode='type'),
                                           required_buff=[['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1', 'Raptor', 'Formless Fist']],
                                           buff_removal_opt=[['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1'], 'Raptor', 'Formless Fist']),
                   'Twin Snakes': ActionDC('gcd', 280, self.gcd_time, self.gcd_time,
                                           buff_effect=BuffSelector(self, [{'self': ['Beast-Raptor', 'Disciplined Fist']}, {'self': ['Beast-Raptor', 'Disciplined Fist']}, {'self': ['Beast-Raptor', 'Blitz', 'Disciplined Fist']}, {'self': ['Coeurl', 'Disciplined Fist']}, {'self': ['Coeurl', 'Disciplined Fist']}],
                                                                  ['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1', 'Raptor', 'Formless Fist'], mode='type'),
                                           required_buff=[['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1', 'Raptor', 'Formless Fist']],
                                           buff_removal_opt=[['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1'], 'Raptor', 'Formless Fist']),
                   'Snap Punch': ActionDC('gcd', 310, self.gcd_time, self.gcd_time,
                                          buff_effect=BuffSelector(self, [{'self': ['Beast-Coeurl']}, {'self': ['Beast-Coeurl']}, {'self': ['Beast-Coeurl', 'Blitz']}, {'self': ['Oppo-oppo']}, {'self': ['Oppo-oppo']}],
                                                                  ['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1', 'Coeurl', 'Formless Fist'], mode='type'),
                                          required_buff=[['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1', 'Coeurl', 'Formless Fist']],
                                          buff_removal_opt=[['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1'], 'Coeurl', 'Formless Fist']),
                   'Demolish': ActionDC('gcd', 130, self.gcd_time, self.gcd_time,
                                        buff_effect=BuffSelector(self, [{'self': ['Beast-Coeurl']}, {'self': ['Beast-Coeurl']}, {'self': ['Beast-Coeurl', 'Blitz']}, {'self': ['Oppo-oppo']}, {'self': ['Oppo-oppo']}],
                                                                  ['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1', 'Coeurl', 'Formless Fist'], mode='type'),
                                        required_buff=[['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1', 'Raptor', 'Formless Fist']],
                                        buff_removal_opt=[['Perfect Balance 3', 'Perfect Balance 2', 'Perfect Balance 1'], 'Coeurl', 'Formless Fist'],
                                        dot_effect='Demolish'),
                   'Six-sided Star': ActionDC('gcd', 550, 2*self.gcd_time, 2*self.gcd_time),
                   'Elixir Field': ActionDC('gcd', 600, self.gcd_time, self.gcd_time,
                                            buff_effect={'self': ['Formless Fist']},
                                            buff_removal=['Blitz'],
                                            buff_removal_opt=['Oppo-oppo', 'Raptor', 'Coeurl', 'Beast-Oppo-oppo',
                                                              'Beast-Raptor', 'Beast-Coeurl'],
                                            resource={'Lunar Nadi': 1}),
                   'Rising Phoenix': ActionDC('gcd', 700, self.gcd_time, self.gcd_time,
                                              buff_effect={'self': ['Formless Fist']},
                                              buff_removal=['Blitz'],
                                              buff_removal_opt=['Oppo-oppo', 'Raptor', 'Coeurl', 'Beast-Oppo-oppo',
                                                                'Beast-Raptor', 'Beast-Coeurl'],
                                              resource={'Solar Nadi': 1}),
                   'Phantom Rush': ActionDC('gcd', 1150, self.gcd_time, self.gcd_time,
                                            buff_effect={'self': ['Formless Fist']},
                                            buff_removal=['Blitz'],
                                            buff_removal_opt=['Oppo-oppo', 'Raptor', 'Coeurl', 'Beast-Oppo-oppo',
                                                              'Beast-Raptor', 'Beast-Coeurl'],
                                            resource={'Lunar Nadi': -1, 'Solar Nadi': -1}),
                   'The Forbidden Chakra': ActionDC('ogcd', 340, 1.0,
                                                    resource={'chakra': -5}),
                   'Meditation': ActionDC('ogcd', 0, 1.0,
                                          resource={'chakra': 1}),
                   'Perfect Balance': ActionDC('ogcd', 0, 1.0,
                                               buff_effect={'self': ['Perfect Balance 3', 'Perfect Balance 2',
                                                                     'Perfect Balance 1']},
                                               buff_removal_opt=['Oppo-oppo', 'Raptor', 'Coeurl', 'Formless Fist'],
                                               disallowed_buff=['Perfect Balance 1', 'Blitz'],
                                               max_charges=2,
                                               charge_time=40.0),
                   'Form Shift': ActionDC('gcd', 0, self.gcd_time, self.gcd_time,
                                          buff_effect={'self': ['Formless Fist']}),
                   'Riddle of Fire': ActionDC('ogcd', 0, 60.0,
                                              buff_effect={'self': ['Riddle of Fire']}),
                   'Riddle of Wind': ActionDC('ogcd', 0, 90.0,
                                              buff_effect={'self': ['Riddle of Wind']}),
                   'Brotherhood': ActionDC('ogcd', 0, 120.0,
                                           buff_effect={'self': ['Self-Meditative'],
                                                        'team': ['Brotherhood', 'Meditative Brotherhood']})
                   }
        self.actions.update(actions)

        # dots
        dots = {'Demolish': DotDC(70, 18.0)}
        self.dots.update(dots)

    def choose_action(self):
        # determine current action, based on current buffs/procs

        if self.next_event == self.next_gcd:
            # Use a GCD
            # Prepull
            if self.next_event < 0.0:
                # Jump to -15 sec if needed
                if self.next_event < -15.0:
                    # Wait until 15 sec before pull
                    self.next_gcd = -15.0
                    self.next_event = self.next_gcd
                    return None, 0.0
                if self.next_event <= -15.0:
                    # Use Form Shift and jump to start of fight
                    self.next_gcd = 0.0
                    self.next_event = self.next_gcd
                    return self.initiate_action('Form Shift')

            # Blitz available
            if self.buffs['Blitz'].timer > 0.0:
                # Try Phantom first
                action = 'Phantom Rush'
                if self.allowed_action(action):
                    return self.initiate_action(action)

                # Check beast chakra count
                beast_count = 0
                for beast in ['Beast-Oppo-oppo', 'Beast-Raptor', 'Beast-Coeurl']:
                    if self.buffs[beast].timer > 0:
                        beast_count += 1

                # Use the allowed blitz by beast count
                if beast_count == 3:
                    action = 'Rising Phoenix'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                if beast_count == 1:
                    action = 'Elixir Field'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                else:
                    print('failed beast')
                    return self.initiate_action('Elixir Field')

            # Basic GCD Rotation
            if self.buffs['Oppo-oppo'].timer > 0.0:
                if self.buffs['Leaden Fist'].timer > 0.0:
                    action = 'Bootshine'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                else:
                    action = 'Dragon Kick'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
            if self.buffs['Raptor'].timer > 0.0:
                if self.buffs['Disciplined Fist'].timer > 4.0:
                    action = 'True Strike'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                else:
                    action = 'Twin Snakes'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
            if self.buffs['Coeurl'].timer > 0.0:
                if self.dots['Demolish'].timer <= 2.0:
                    action = 'Demolish'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                else:
                    action = 'Snap Punch'
                    if self.allowed_action(action):
                        return self.initiate_action(action)

            # Formless Fist
            if self.buffs['Formless Fist'].timer > 0.0:
                if self.buffs['Leaden Fist'].timer <= 0.0:
                    action = 'Dragon Kick'
                    if self.allowed_action(action):
                        return self.initiate_action(action)
                else:
                    action = 'Bootshine'
                    if self.allowed_action(action):
                        return self.initiate_action(action)

            # Perfect Balance Stacks
            if self.buffs['Perfect Balance 1'].timer > 0.0:
                if self.resources['Solar Nadi'].amount < 1:
                    # Just do normal rotation (not optimal, just a placeholder)
                    if self.buffs['Perfect Balance 3'].timer > 0.0:
                        if self.buffs['Leaden Fist'].timer > 0.0:
                            action = 'Bootshine'
                            if self.allowed_action(action):
                                return self.initiate_action(action)
                        else:
                            action = 'Dragon Kick'
                            if self.allowed_action(action):
                                return self.initiate_action(action)
                    if self.buffs['Perfect Balance 2'].timer > 0.0:
                        if self.buffs['Disciplined Fist'].timer > 4.0:
                            action = 'True Strike'
                            if self.allowed_action(action):
                                return self.initiate_action(action)
                        else:
                            action = 'Twin Snakes'
                            if self.allowed_action(action):
                                return self.initiate_action(action)
                    else:
                        if self.dots['Demolish'].timer <= 2.0:
                            action = 'Demolish'
                            if self.allowed_action(action):
                                return self.initiate_action(action)
                        else:
                            action = 'Snap Punch'
                            if self.allowed_action(action):
                                return self.initiate_action(action)
                else:
                    if self.buffs['Leaden Fist'].timer > 0.0:
                        action = 'Bootshine'
                        if self.allowed_action(action):
                            return self.initiate_action(action)
                    else:
                        action = 'Dragon Kick'
                        if self.allowed_action(action):
                            return self.initiate_action(action)
        else:
            # consider using oGCDs
            if round(self.next_event + self.anim_lock, 3) > self.next_gcd:
                # don't clip gcd
                return self.go_to_gcd()

            # Use Riddle of Fire when up
            action = 'Riddle of Fire'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Use Brotherhood when up
            action = 'Brotherhood'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Use TFC when available (at 5 chakra)
            action = 'The Forbidden Chakra'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Use Perfect Balance on cooldown for now
            action = 'Perfect Balance'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # Use Riddle of Wind when up
            action = 'Riddle of Wind'
            if self.allowed_action(action):
                return self.initiate_action(action)
            # doing nothing for this oGCD
            return self.pass_ogcd()

    def reset(self):
        # reset the actor (clears buff and proc timers, etc.)
        self.__init__(self.wd, self.ap, self.det, self.spd, self.crit, self.dhit, self.wpn_delay,
                      player_id=self.player_id, **self.kwargs)






