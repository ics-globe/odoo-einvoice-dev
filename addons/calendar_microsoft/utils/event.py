from odoo.addons.calendar_sync.utils.event import ProviderEvent

class MicrosoftEvent(ProviderEvent):

    def __getattr__(self, name):
        return self.get(name)

    def is_single_event(self):
        raise Exception("Not overriden")

    def is_recurrence(self):
        return self.get('type') == 'seriesMaster'

    def is_removed(self):
        return self.get('@removed') and self.get('@removed').get('reason') == 'deleted'

    def is_occurrence(self) -> bool:
        return bool(self.seriesMasterId)
