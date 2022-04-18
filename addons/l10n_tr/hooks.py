# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from io import StringIO
from os.path import join, dirname, realpath
from odoo import _
from odoo.exceptions import MissingError

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    _load_neighborhood(cr, registry)


def uninstall_hook(cr, registry):
    cr.execute("DELETE FROM l10n_tr_neighborhood;")
    cr.execute("DELETE FROM ir_model_data WHERE model='l10n_tr.neighborhood';")


def _load_neighborhood(cr, registry):
    """Import CSV data would take +60 seconds to load it with
    the regular ORM methods, while here, it is under 3 seconds
    """
    csv_path = join(dirname(realpath(__file__)), 'data',
                    'l10n_tr.neighborhood.csv')
    _logger.info('loading l10n_tr/data/l10n_tr.neighborhood.csv')
    csv_file = open(csv_path, 'rt')
    csv_file.readline()  # Read the header, so we avoid copying it to the db

    cr.execute("SELECT name, res_id FROM ir_model_data where model='l10n_tr.area'")
    areas = {rec[0]: str(rec[1]) for rec in cr.fetchall()}

    csv_with_id = StringIO()
    count = 0
    for line in csv_file:
        row = list(map(str.strip, line.split('|')))
        if row[1] not in areas:
            _logger.error('Error while loading Neighborhoods, matching area %s not found for %s.', row[1], row[0])
            raise MissingError(_('Error while loading Neighborhoods, Area with id: %s not defined.') % row[1])
        csv_with_id.write('|'.join([row[0], areas[row[1]]]) + '\n')
        count += 1
    csv_with_id.seek(0)
    cr.copy_expert(
        """COPY l10n_tr_neighborhood (name,area_id)
           FROM STDIN WITH DELIMITER '|'""", csv_with_id)
    # Create xml_id, to allow make reference to this data
    cr.execute(
        """INSERT INTO ir_model_data
           (name, res_id, module, model, noupdate)
           SELECT concat('l10n_tr_neighborhood_', id), id, 'l10n_tr', 'l10n_tr.neighborhood', 't'
           FROM l10n_tr_neighborhood""")
    _logger.info('total of %s Turkish neighborhoods loaded.', count)
