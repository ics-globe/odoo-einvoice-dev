# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import SavepointCase, tagged


@tagged('-at_install', 'post_install')
class TestOverrides(SavepointCase):

    # Ensure all main ORM methods behavior works fine even on empty recordset
    # and that useless operations are avoided in this case.

    def test_creates(self):
        for model in self.env:
            model_env = self.env[model]
            with self.assertQueryCount(0):
                self.assertEqual(
                    model_env.create([]), model_env.browse(),
                    "Invalid create return value for model %s" % model_env._name)

    def test_writes(self):
        for model in self.env:
            model_env = self.env[model]
            with self.assertQueryCount(0):
                self.assertEqual(
                    model_env.browse().write({}), True,
                    "Invalid write return value for model %s" % model_env._name)

    def test_default_get(self):
        for model in self.env:
            model_env = self.env[model]
            if model_env._transient:
                continue
            with self.assertQueryCount(1):
                # allow one query for the call to get_model_defaults.
                self.assertEqual(
                    model_env.browse().default_get([]), {},
                    "Invalid default_get return value for model %s" % model_env._name)

    def test_unlink(self):
        for model in self.env:
            model_env = self.env[model]
            with self.assertQueryCount(0):
                self.assertEqual(
                    model_env.browse().unlink(), True,
                    "Invalid create return value for model %s" % model_env._name)

    def test_active_logic(self):
        for model in self.env:
            model_env = self.env[model]
            if model_env._active_name:
                with self.assertQueryCount(0):
                    model_env.toggle_active()
                    model_env.action_archive()
                    model_env.action_unarchive()
                    self.assertEqual(
                        model_env.write(dict(active=False)), True,
                        "Invalid write return value for model %s" % model_env._name)
                    self.assertEqual(
                        model_env.write(dict(active=True)), True,
                        "Invalid write return value for model %s" % model_env._name)
