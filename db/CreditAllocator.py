#
#
#

from db.models import *

# main entry point
def main():
    all_users = OceanUser.objects.all()

    for u in all_users:
        if u.credit < u.quota:
            u.credit = u.credit + u.monthly_rate
        if u.credit > u.quota:
            u.credit = u.quota
        print "Add %d credits to %s. Total: %d" % ( u.monthly_rate, u.name, u.credit )
        u.save()

#
main()