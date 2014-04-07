# Adapted from http://docs.python.org/2/library/csv.html

import csv
import codecs
import cStringIO


class UnicodeWriter(object):
    """CSV Unicode Writer

    A CSV writer which will write rows to CSV file "f", which is encoded in the
    given encoding.

    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8",
                 errors='replace', **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)(errors=errors)

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
