# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.models.res_users import is_selection_groups, get_selection_groups, name_selection_groups
from odoo.tests.common import TransactionCase, Form, tagged


class TestUsers(TransactionCase):

    def test_name_search(self):
        """ Check name_search on user. """
        User = self.env['res.users']

        test_user = User.create({'name': 'Flad the Impaler', 'login': 'vlad'})
        like_user = User.create({'name': 'Wlad the Impaler', 'login': 'vladi'})
        other_user = User.create({'name': 'Nothing similar', 'login': 'nothing similar'})
        all_users = test_user | like_user | other_user

        res = User.name_search('vlad', operator='ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, test_user)

        res = User.name_search('vlad', operator='not ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, all_users)

        res = User.name_search('', operator='ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, all_users)

        res = User.name_search('', operator='not ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, User)

        res = User.name_search('lad', operator='ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, test_user | like_user)

        res = User.name_search('lad', operator='not ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, other_user)

    def test_user_partner(self):
        """ Check that the user partner is well created """

        User = self.env['res.users']
        Partner = self.env['res.partner']
        Company = self.env['res.company']

        company_1 = Company.create({'name': 'company_1'})
        company_2 = Company.create({'name': 'company_2'})

        partner = Partner.create({
            'name': 'Bob Partner',
            'company_id': company_2.id
        })

        # case 1 : the user has no partner
        test_user = User.create({
            'name': 'John Smith',
            'login': 'jsmith',
            'company_ids': [company_1.id],
            'company_id': company_1.id
        })

        self.assertFalse(
            test_user.partner_id.company_id,
            "The partner_id linked to a user should be created without any company_id")

        # case 2 : the user has a partner
        test_user = User.create({
            'name': 'Bob Smith',
            'login': 'bsmith',
            'company_ids': [company_1.id],
            'company_id': company_1.id,
            'partner_id': partner.id
        })

        self.assertEqual(
            test_user.partner_id.company_id,
            company_1,
            "If the partner_id of a user has already a company, it is replaced by the user company"
        )


    def test_change_user_company(self):
        """ Check the partner company update when the user company is changed """

        User = self.env['res.users']
        Company = self.env['res.company']

        test_user = User.create({'name': 'John Smith', 'login': 'jsmith'})
        company_1 = Company.create({'name': 'company_1'})
        company_2 = Company.create({'name': 'company_2'})

        test_user.company_ids += company_1
        test_user.company_ids += company_2

        # 1: the partner has no company_id, no modification
        test_user.write({
            'company_id': company_1.id
        })

        self.assertFalse(
            test_user.partner_id.company_id,
            "On user company change, if its partner_id has no company_id,"
            "the company_id of the partner_id shall NOT be updated")

        # 2: the partner has a company_id different from the new one, update it
        test_user.partner_id.write({
            'company_id': company_1.id
        })

        test_user.write({
            'company_id': company_2.id
        })

        self.assertEqual(
            test_user.partner_id.company_id,
            company_2,
            "On user company change, if its partner_id has already a company_id,"
            "the company_id of the partner_id shall be updated"
        )

@tagged('post_install', '-at_install')
class TestUsers2(TransactionCase):

    def setUp(self):
        """
            These are the Groups and their Hierarchy we have Used to test Group warnings.
            Groups:
                Sales
                ├── User: All Documents
                └── Administrator
                Timesheets
                ├── Administrator
                ├── User: all timesheets
                └── User: own timesheets only
                Project
                ├── Administrator
                └── User
                Field Service
                ├── Administrator
                └── User

            Hierarchy:
                Sales / Administrator
                └── Sales / User: All Documents

                Timesheets / Administrator
                └── Timesheets / User: all timesheets
                    └── Timehseets / User: own timesheets only

                Project / Administrator
                ├── Project / User
                └── Timesheets / User: all timesheets

                Field Service / Administrator
                ├── Sales / Administrator
                ├── Project / Administrator
                └── Field Service / User
        """
        super().setUp()
        ResGroups = self.env['res.groups']
        cat_sales = self.env['ir.module.category'].create({'name': 'Sales'})
        cat_project = self.env['ir.module.category'].create({'name': 'Project'})
        cat_field_service = self.env['ir.module.category'].create({'name': 'Field Service'})
        cat_timesheets = self.env['ir.module.category'].create({'name': 'Timesheets'})

        # Sales
        self.group_sales_user, self.group_sales_administrator = ResGroups.create([
            {'name': name, 'category_id': cat_sales.id}
            for name in ('User: All Documents', 'Administrator')
        ])
        self.sales_cat_field = name_selection_groups((self.group_sales_user | self.group_sales_administrator).ids)
        self.group_sales_administrator.implied_ids = self.group_sales_user

        # Timesheets
        self.group_timesheets_user_own_timesheet, self.group_timesheets_user_all_timesheet, self.group_timesheets_administrator = ResGroups.create([
            {'name': name, 'category_id': cat_timesheets.id}
            for name in ('User: own timesheets only', 'User: all timesheets', 'Administrator')
        ])
        self.timesheet_cat_field = name_selection_groups((self.group_timesheets_user_own_timesheet |
                                                          self.group_timesheets_user_all_timesheet |
                                                          self.group_timesheets_administrator).ids
                                                         )
        self.group_timesheets_administrator.implied_ids += self.group_timesheets_user_all_timesheet
        self.group_timesheets_user_all_timesheet.implied_ids += self.group_timesheets_user_own_timesheet

        # Project
        self.group_project_user, self.group_project_admnistrator = ResGroups.create([
            {'name': name, 'category_id': cat_project.id}
            for name in ('User', 'Administrator')
        ])
        self.project_cat_field = name_selection_groups((self.group_project_user | self.group_project_admnistrator).ids)
        self.group_project_admnistrator.implied_ids = (self.group_project_user | self.group_timesheets_user_all_timesheet)

        # Field Service
        self.group_field_service_user, self.group_field_service_administrator = ResGroups.create([
            {'name': name, 'category_id': cat_field_service.id}
            for name in ('User', 'Administrator')
        ])
        self.field_service_cat_field = name_selection_groups((self.group_field_service_user | self.group_field_service_administrator).ids)
        self.group_field_service_administrator.implied_ids = (self.group_sales_administrator |
                                                              self.group_project_admnistrator |
                                                              self.group_field_service_user).ids

        # User
        self.test_group_user = self.env['res.users'].create({
            'name': 'Test Group User',
            'login': 'TestGroupUser',
            'groups_id': (
                self.env.ref('base.group_user') |
                self.group_timesheets_administrator |
                self.group_field_service_administrator).ids
        })

    def test_reified_groups(self):
        """ The groups handler doesn't use the "real" view with pseudo-fields
        during installation, so it always works (because it uses the normal
        groups_id field).
        """
        # use the specific views which has the pseudo-fields
        f = Form(self.env['res.users'], view='base.view_users_form')
        f.name = "bob"
        f.login = "bob"
        user = f.save()

        self.assertIn(self.env.ref('base.group_user'), user.groups_id)

    def test_selection_groups(self):
        # create 3 groups that should be in a selection
        app = self.env['ir.module.category'].create({'name': 'Foo'})
        group1, group2, group0 = self.env['res.groups'].create([
            {'name': name, 'category_id': app.id}
            for name in ('User', 'Manager', 'Visitor')
        ])
        # THIS PART IS NECESSARY TO REPRODUCE AN ISSUE: group1.id < group2.id < group0.id
        self.assertLess(group1.id, group2.id)
        self.assertLess(group2.id, group0.id)
        # implication order is group0 < group1 < group2
        group2.implied_ids = group1
        group1.implied_ids = group0
        groups = group0 + group1 + group2

        # determine the name of the field corresponding to groups
        fname = next(
            name
            for name in self.env['res.users'].fields_get()
            if is_selection_groups(name) and group0.id in get_selection_groups(name)
        )
        self.assertCountEqual(get_selection_groups(fname), groups.ids)

        # create a user
        user = self.env['res.users'].create({'name': 'foo', 'login': 'foo'})

        # put user in group0, and check field value
        user.write({fname: group0.id})
        self.assertEqual(user.groups_id & groups, group0)
        self.assertEqual(user.read([fname])[0][fname], group0.id)

        # put user in group1, and check field value
        user.write({fname: group1.id})
        self.assertEqual(user.groups_id & groups, group0 + group1)
        self.assertEqual(user.read([fname])[0][fname], group1.id)

        # put user in group2, and check field value
        user.write({fname: group2.id})
        self.assertEqual(user.groups_id & groups, groups)
        self.assertEqual(user.read([fname])[0][fname], group2.id)

    def test_read_group_with_reified_field(self):
        """ Check that read_group gets rid of reified fields"""
        User = self.env['res.users']
        fnames = ['name', 'email', 'login']

        # find some reified field name
        reified_fname = next(
            fname
            for fname in User.fields_get()
            if fname.startswith(('in_group_', 'sel_groups_'))
        )

        # check that the reified field name has no effect in fields
        res_with_reified = User.read_group([], fnames + [reified_fname], ['company_id'])
        res_without_reified = User.read_group([], fnames, ['company_id'])
        self.assertEqual(res_with_reified, res_without_reified, "Reified fields should be ignored")

        # Verify that the read_group is raising an error if reified field is used as groupby
        with self.assertRaises(ValueError):
            User.read_group([], fnames + [reified_fname], [reified_fname])

    def test_reified_groups_on_change(self):
        """Test that a change on a reified fields trigger the onchange of groups_id."""
        group_public = self.env.ref('base.group_public')
        group_portal = self.env.ref('base.group_portal')
        group_user = self.env.ref('base.group_user')

        # Build the reified group field name
        user_groups = group_public | group_portal | group_user
        user_groups_ids = [str(group_id) for group_id in sorted(user_groups.ids)]
        group_field_name = f"sel_groups_{'_'.join(user_groups_ids)}"

        user_form = Form(self.env['res.users'], view='base.view_users_form')
        user_form.name = "Test"
        user_form.login = "Test"
        self.assertFalse(user_form.share)

        setattr(user_form, group_field_name, group_portal.id)
        self.assertTrue(user_form.share, 'The groups_id onchange should have been triggered')

        setattr(user_form, group_field_name, group_user.id)
        self.assertFalse(user_form.share, 'The groups_id onchange should have been triggered')

        setattr(user_form, group_field_name, group_public.id)
        self.assertTrue(user_form.share, 'The groups_id onchange should have been triggered')

    def test_user_group_inheritance_no_warning(self):
        """
            The warning should not be there when the User tries to Change to Higher rights.
        """
        with Form(self.test_group_user, view='base.view_users_form') as UserForm:
            UserForm._values[self.sales_cat_field] = self.group_sales_administrator.id
            UserForm._perform_onchange([self.sales_cat_field])

            self.assertFalse(UserForm.user_group_warning)

    def test_user_group_parent_inheritance_no_warning(self):
        """
            The warning should not be there when the User Changes Parent rights to Lower one
        """
        with Form(self.test_group_user, view='base.view_users_form') as UserForm:
            UserForm._values[self.field_service_cat_field] = self.group_field_service_user.id
            UserForm._perform_onchange([self.field_service_cat_field])

            self.assertFalse(UserForm.user_group_warning)

    def test_user_group_inheritance_warning(self):
        """
            User makes changes to Sales User from Sales Administrator.
            The warning should be there since Sales Administrator is Required
            when User has Field Service Administrator
        """
        with Form(self.test_group_user, view='base.view_users_form') as UserForm:
            UserForm._values[self.sales_cat_field] = self.group_sales_user.id
            UserForm._perform_onchange([self.sales_cat_field])

            self.assertEqual(
                UserForm.user_group_warning,
                'Since Test Group User is a/an Field Service Administrator, you can set Sales right only to Administrator'
            )

    def test_user_multi_group_inheritance_warning(self):
        """
           User makes changes To Sales User and Project User from Administrator
           The warming should be there since Administrator for both are required
           when User has Field Service Administrator
        """
        with Form(self.test_group_user, view='base.view_users_form') as UserForm:
            UserForm._values[self.sales_cat_field] = self.group_sales_user.id
            UserForm._values[self.project_cat_field] = self.group_project_user.id
            UserForm._perform_onchange([self.sales_cat_field])

            warnings = [
                "Since Test Group User is a/an Field Service Administrator, you can set Sales right only to Administrator",
                "Since Test Group User is a/an Field Service Administrator, you can set Project right only to Administrator"
            ]
            self.assertTrue(all(warning in UserForm.user_group_warning for warning in warnings))

    def test_user_multi_possible_group_inheritance_warning(self):
        """
            User makes changes to Timesheets / User: Own Timesheet from Timesheets / Administrator
            The warning should be there since Timessets / Administrator and Timesheets / User: All Documents
            required when the User has Project Administrator
        """
        with Form(self.test_group_user, view='base.view_users_form') as UserForm:
            UserForm._values[self.timesheet_cat_field] = self.group_timesheets_user_own_timesheet.id
            UserForm._perform_onchange([self.timesheet_cat_field])

            self.assertEqual(
                UserForm.user_group_warning,
                'Since Test Group User is a/an Project Administrator, you can set Timesheets right only to Administrator or User: all timesheets'
            )

    def test_user_group_empty_group_warning(self):
        """
            User Makes Sales Rights to Empty.
            The warning should be there since Sales Administrator is Required
            when User has Field Service Administrator
        """
        with Form(self.test_group_user, view='base.view_users_form') as UserForm:
            UserForm._values[self.sales_cat_field] = False
            UserForm._perform_onchange([self.sales_cat_field])

            self.assertEqual(
                UserForm.user_group_warning,
                'Since Test Group User is a/an Field Service Administrator, they will at the minimum have the Sales: Administrator access too'
            )
