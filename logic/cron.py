from datetime import datetime, timedelta
import time

# Some utility classes / functions first
class AllMatch(set):
    """Universal set - match everything"""
    def __contains__(self, item):
        return True

allMatch = AllMatch()

# The actual Event class
class Event(object):
    def __init__(self, action, min=allMatch, hour=allMatch,
                       day=allMatch, month=allMatch, dow=allMatch,
                       args=(), kwargs={}):
        self.mins = self._conv_to_set(min)
        self.hours= self._conv_to_set(hour)
        self.days = self._conv_to_set(day)
        self.months = self._conv_to_set(month)
        self.dow = self._conv_to_set(dow)
        self.action = action
        self.args = args
        self.kwargs = kwargs

    def matchtime(self, t):
        """Return True if this event should trigger at the specified datetime"""
        return ((t.minute     in self.mins) and
                (t.hour       in self.hours) and
                (t.day        in self.days) and
                (t.month      in self.months) and
                (t.weekday()  in self.dow))

    def check(self, t):
        if self.matchtime(t):
            self.action(*self.args, **self.kwargs)

    def _conv_to_set(self,obj):  # Allow single integer to be provided
        if isinstance(obj, (int,long)):
            return set([obj])  # Single item
        if not isinstance(obj, set):
            obj = set(obj)
        return obj

class CronTab(object):
    def __init__(self, *events):
        self.events = events

    def run(self):
        t=datetime(*datetime.now().timetuple()[:5])
        while 1:
            for e in self.events:
                e.check(t)

            t += timedelta(minutes=1)
            n = datetime.now()
            while n < t:
                s = (t - n).seconds + 1
                time.sleep(s)
                n = datetime.now()
