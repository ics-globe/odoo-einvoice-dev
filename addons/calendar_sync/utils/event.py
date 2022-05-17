from collections import namedtuple, UserDict

# --------------------------------------------------------------------------
# The ProviderData structure contains events coming from a provider, sorted
# by kind of update (added/updated/removed) and then by kind of events (
# single, recurrence).
# Then, each item is a ProviderEvent containing event data in the provider data
# format.
# --------------------------------------------------------------------------
ProviderData = namedtuple('ProviderData', ['added', 'updated', 'removed'])
ProviderEvents = namedtuple('ProviderEvents', ['singles', 'recurrences'])

class ProviderEvent(UserDict):
    """
    A provider event implemented as a dictionary with some specific methods
    which should be overriden for each calendar provider.
    """

    def set_odoo_event(self, odoo_event):
        self['_odoo'] = odoo_event

    def get_odoo_event(self):
        return self.get('_odoo')

    def has_odoo_event(self):
        return self.get('_odoo')

    def is_single_event(self):
        raise Exception("Not overriden")

    def is_recurrence(self):
        raise Exception("Not overriden")

    def is_occurrence(self):
        raise Exception("Not overriden")
