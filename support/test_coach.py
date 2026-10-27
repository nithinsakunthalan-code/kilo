from django.test import SimpleTestCase

from . import coach


class CoachParsingTests(SimpleTestCase):
    def test_parses_weight_goal_and_timeframe(self):
        info = coach.parse('i weigh 80 kilograms i need a diet plan so i can reduce 5kg in a month')
        self.assertEqual((info['weight'], info['change'], info['direction'], info['days']), (80.0, 5.0, 'loss', 30))

    def test_parses_gain_pounds_and_weeks(self):
        info = coach.parse('I am 150 lbs and want to gain 6 lb in 12 weeks')
        self.assertAlmostEqual(info['weight'], 68.0, delta=0.1)
        self.assertEqual((info['direction'], info['days']), ('gain', 84))
        self.assertAlmostEqual(info['change'], 2.7, delta=0.1)

    def test_target_weight_phrasing(self):
        info = coach.parse('I am 90 kg, want to get to 80 kg in 5 months')
        self.assertEqual((info['weight'], info['change'], info['direction'], info['days']), (90.0, 10.0, 'loss', 150))

    def test_optional_profile_details(self):
        info = coach.parse("I'm 70 kg, 170 cm, 24 years old female. Lose 4 kg in 2 months")
        self.assertEqual((info['height'], info['age'], info['sex']), (170, 24, 'female'))

    def test_intent_detection(self):
        for text in ('give me a diet plan', 'how many calories should I eat', 'I want to lose 3 kg',
                     'i want to gain 3kg in 3 months', 'what should I eat'):
            self.assertTrue(coach.wants_plan(text), text)
        for text in ('how do I change my calorie goal?', 'what does error 404 mean', 'how do I log a meal?'):
            self.assertFalse(coach.wants_plan(text), text)


class CoachPlanTests(SimpleTestCase):
    def targets(self, message):
        reply = coach.build_reply(message)
        target = int(reply.split('Daily target: ')[1].split(' kcal')[0].replace(',', ''))
        return reply, target

    def test_never_below_calorie_floor(self):
        _, target = self.targets('I weigh 50 kg and want to lose 10 kg in 1 week')
        self.assertGreaterEqual(target, 1500)

    def test_loss_pace_capped_for_aggressive_goal(self):
        reply, _ = self.targets('I weigh 80 kg and want to lose 10 kg in 2 weeks')
        self.assertIn('safer pace', reply)

    def test_reasonable_goal_not_flagged(self):
        reply, _ = self.targets('I weigh 80 kg and want to lose 4 kg in 4 months')
        self.assertNotIn('safer pace', reply)

    def test_gain_target_is_above_maintenance(self):
        reply, target = self.targets('I weigh 60 kg and want to gain 3 kg in 3 months')
        self.assertGreater(target, 60 * 31)
        self.assertIn('gain about', reply)

    def test_macros_add_up_roughly_to_target(self):
        reply, target = self.targets('I weigh 80 kg and want to lose 5 kg in 2 months')
        p = int(reply.split('Protein ')[1].split(' g')[0])
        c = int(reply.split('Carbs ')[1].split(' g')[0])
        f = int(reply.split('Fat ')[1].split(' g')[0])
        self.assertAlmostEqual(p * 4 + c * 4 + f * 9, target, delta=25)

    def test_always_includes_disclaimer(self):
        self.assertIn('not medical advice', coach.build_reply('I weigh 80 kg and want to lose 5 kg'))
