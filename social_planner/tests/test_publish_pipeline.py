# -*- coding: utf-8 -*-
# Vertel Sverige AB AGPL-3

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPublishPipelineApproval(TransactionCase):
    """ Publishing pipeline approval stages, deterministic compliance
    snapshot and re-check on policy change. Core dispatch stages are
    covered by social_marketing tests. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.policy = cls.env['communication.policy'].create({
            'name': 'Test Policy',
            'state': 'active',
        })
        cls.plan = cls.env['communication.plan'].create({
            'name': 'Test Plan',
            'policy_id': cls.policy.id,
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
        })
        cls.line = cls.env['communication.plan.line'].create({
            'plan_id': cls.plan.id,
            'channel': 'linkedin',
            'content_type': 'post',
            'date': '2026-06-01',
        })

    def _create_post(self, message='Hello world'):
        return self.env['social_marketing.post'].create({
            'message': message,
            'plan_line_id': self.line.id,
        })

    def _submit_and_approve(self, post):
        post.action_submit_for_approval()
        post.action_approve()

    def test_submit_logs_steps_and_snapshot(self):
        post = self._create_post()
        post.action_submit_for_approval()
        stages = post.pipeline_step_ids.mapped('stage')
        self.assertIn('submitted', stages)
        self.assertIn('compliance_checked', stages)
        self.assertTrue(post.compliance_snapshot)
        self.assertEqual(
            post.compliance_snapshot['policy_version'], self.policy.version)
        self.assertEqual(post.compliance_snapshot['verdict'], 'pass')
        self.assertTrue(post.compliance_checked_at)

    def test_approve_and_reject_log_steps(self):
        post = self._create_post()
        post.action_submit_for_approval()
        post.action_approve()
        self.assertIn(
            'approved', post.pipeline_step_ids.mapped('stage'))
        post2 = self._create_post('Second post')
        post2.action_submit_for_approval()
        post2.action_reject('Not on brand')
        rejected = post2.pipeline_step_ids.filtered(
            lambda s: s.stage == 'rejected')
        self.assertTrue(rejected)
        self.assertEqual(rejected.result, 'Not on brand')

    def test_snapshot_stable_after_policy_change(self):
        post = self._create_post()
        self._submit_and_approve(post)
        snapshot_before = post.compliance_snapshot
        self.policy.write({'prohibited_content': 'banned'})
        self.assertEqual(post.compliance_snapshot, snapshot_before)

    def test_policy_change_flags_inflight_posts(self):
        post = self._create_post()
        self._submit_and_approve(post)
        self.policy.write({'prohibited_content': 'banned'})
        self.assertTrue(post.needs_recheck)
        # completed/posts are never re-checked
        posted = self._create_post('Already posted')
        posted.write({'state': 'posted'})
        self.policy.write({'prohibited_content': 'banned2'})
        self.assertFalse(posted.needs_recheck)

    def test_recheck_cron_fail_flags_deviation(self):
        post = self._create_post('hello banned')
        self._submit_and_approve(post)
        self.policy.write({'prohibited_content': 'banned'})
        self.env['social_marketing.post']._cron_publish_recheck()
        self.assertEqual(post.compliance_recheck_verdict, 'fail')
        self.assertFalse(post.needs_recheck)
        # original snapshot is untouched
        self.assertEqual(post.compliance_snapshot['verdict'], 'pass')
        self.assertIn(
            'failed', post.pipeline_step_ids.mapped('stage'))

    def test_recheck_cron_pass_resets_flag(self):
        post = self._create_post('all clear')
        self._submit_and_approve(post)
        self.policy.write({'prohibited_content': 'banned'})
        self.assertTrue(post.needs_recheck)
        self.policy.write({'prohibited_content': False})
        self.env['social_marketing.post']._cron_publish_recheck()
        self.assertEqual(post.compliance_recheck_verdict, 'pass')
        self.assertFalse(post.needs_recheck)
