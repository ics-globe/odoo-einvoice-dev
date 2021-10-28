# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# from dateutil.relativedelta import relativedelta
# from itertools import groupby

from datetime import datetime, timedelta

from odoo import models
from odoo.tools import populate
from odoo.addons.crm.populate import tools

# _logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    _populate_dependencies = [
        'res.company',  # MC setup
        'res.partner',  # customer
    ]
    _populate_sizes = {
        'small': 5,
        'medium': 150,
        'large': 400
    }

    def _populate_factories(self):
        partner_ids = self.env.registry.populated_models['res.partner']

        # phone based on country
        country_be, country_us, country_in = self.env.ref('base.be'), self.env.ref('base.us'), self.env.ref('base.in')
        phones_per_country = {
            country_be.id: [False, '+32456555432', '+32456555675', '+32456555627'],
            country_us.id: [False, '+15555564246', '+15558455343', '+15557129033'],
            country_in.id: [False, '+919755538077', '+917555765232', '+918555199309'],
            False: [False, '', '+3212345678', '003212345678', '12345678'],
        }

        # example of more complex generator composed of multiple sub generators
        # this define one subgenerator per "country"
        address_factories_groups = [
            [ # Falsy, 2 records
                ('street', populate.iterate([False, ''])),
                ('street2', populate.iterate([False, ''])),
                ('city', populate.iterate([False, ''])),
                ('zip', populate.iterate([False, ''])),
                ('country_id', populate.iterate([False])),
            ], [  # BE, 2 records
                ('street', populate.iterate(['Rue des Bourlottes {counter}', 'Rue Pinckaers {counter}'])),
                ('city', populate.iterate(['Brussels', 'Ramillies'])),
                ('zip', populate.iterate([1020, 1367])),
                ('country_id', populate.iterate([self.env.ref('base.be').id])),
            ], [  # US, 3 records
                ('street', populate.iterate(['Main street', '3th street {counter}', False])),
                ('street2', populate.iterate([False, '', 'Behind the tree {counter}'], [90, 5, 5])),
                ('city', populate.randomize(['San Fransisco', 'Los Angeles', '', False])),
                ('zip', populate.iterate([False, '', '50231'])),
                ('country_id', populate.iterate([self.env.ref('base.us').id])),
            ], [  # IN, 2 records
                ('street', populate.iterate(['Main Street', 'Some Street {counter}'])),
                ('city', populate.iterate(['ગાંધીનગર (Gandhinagar)'])),
                ('zip', populate.randomize(['382002', '382008'])),
                ('country_id', populate.randomize([self.env.ref('base.in').id])),
            ], [  # other corner cases, 2 records
                ('street', populate.iterate(['万泉寺村', 'საბჭოს სკვერი {counter}'])),
                ('city', populate.iterate(['北京市', 'თბილისი'])),
                ('zip', populate.iterate([False, 'UF47'])),
                ('country_id', populate.randomize([False] + self.env['res.country'].search([]).ids)),
            ]
        ]

        def _compute_address(iterator, *args):
            address_generators = [
                populate.chain_factories(address_factories, self._name)
                for address_factories in address_factories_groups
            ]
            # first, exhaust all address_generators
            for adress_generator in address_generators:
                for adress_values in adress_generator:
                    if adress_values['__complete']:
                        break
                    values = next(iterator)  # only consume main iterator if usefull
                    yield {**values, **adress_values}
            # then, go pseudorandom between generators
            r = populate.Random('res.partner+address_generator_selector')
            for values in iterator:
                adress_generator = r.choice(address_generators)
                adress_values = next(adress_generator)
                yield {**adress_values, **values}

        def _compute_contact_name(values=None, counter=0, **kwargs):
            """ Generate lead names a bit better than lead_counter because this is Odoo. """
            partner_id = values['partner_id']
            print('cacaboum', partner_id, counter, values)
            complete = values['__complete']

            # if is_company:
            #     nn = kwargs['random'].choice(self.c_name_groups)
            #     sn = kwargs['random'].choice(self.c_surname_groups)
            #     return '%s %s (%d_%s)' % (nn, sn, int(complete), counter)

            fn = kwargs['random'].choice(tools._p_forename_groups)
            mn = kwargs['random'].choices(
                [False] + tools._p_middlename_groups,
                weights=[1] + [1 / (len(tools._p_middlename_groups) or 1)] * len(tools._p_middlename_groups)
            )[0]
            sn = kwargs['random'].choice(tools._p_surname_groups)
            return  '%s%s %s (%s_%s (partner %s))' % (
                fn,
                ' "%s"' % mn if mn else '',
                sn,
                int(complete),
                counter,
                partner_id
            )

        def _compute_name(values=None, counter=0, **kwargs):
            """ Generate lead names a bit better than lead_counter because this is Odoo. """
            complete = values['__complete']

            fn = kwargs['random'].choice(tools._t_prefix_groups)
            sn = kwargs['random'].choice(tools._t_object_groups)
            return  '%s %s (%s_%s)' % (
                fn,
                sn,
                int(complete),
                counter
            )

        def _compute_phone_number(values=None, random=None, **kwargs):
            country_id = values['country_id']
            if country_id not in phones_per_country.keys():
                country_id = False
            return random.choice(phones_per_country[country_id])

        def _compute_date_open(random=None, values=None, **kwargs):
            user_id = values['user_id']
            if user_id:
                delta = random.randint(0, 10)
                return datetime.now() - timedelta(days=delta)
            return False

        return [
            ('_address', _compute_address),
            ('partner_id', populate.iterate(
                [False] + partner_ids,
                [2] + [1 / (len(partner_ids) or 1)] * len(partner_ids))
            ),
            ('contact_name', populate.compute(_compute_contact_name)),  # uses partner_id
            ('name', populate.compute(_compute_name)),
            ('phone', populate.compute(_compute_phone_number)),  # uses country_id
            ('mobile', populate.compute(_compute_phone_number)),  # uses country_id
            ('user_id', populate.iterate(
                [False],
                [2])
            ),
            ('date_open', populate.compute(_compute_date_open)),  # uses user_id
            ('type', populate.iterate(['lead', 'opportunity'], [0.8, 0.2])),
        ]
