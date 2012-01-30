# -*- coding: utf-8 -*-
#
# Special unit test mode
#########################

# A quick-n-dirty way which sets settings.TEST
# if we're running unit tests.
import sys, os
TEST = False
if len(sys.argv) >= 2:
    if os.path.basename(sys.argv[0]) == 'manage.py' and \
        (sys.argv[1] == 'test' or sys.argv[1] == 'hudson'):
            TEST = True
