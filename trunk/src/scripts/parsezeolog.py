"""Parse the BLATHER logging generated by ZEO.

An example of the log format is:
2002-04-15T13:05:29 BLATHER(-100) ZEO Server storea(3235680, [714], 235339406490168806) ('10.0.26.30', 45514)
"""

import operator
import re
import time

rx_time = re.compile('(\d\d\d\d-\d\d-\d\d)T(\d\d:\d\d:\d\d)')

def parse_time(line):
    """Return the time portion of a zLOG line in seconds or None."""
    mo = rx_time.match(line)
    if mo is None:
        return None
    date, time_ = mo.group(1, 2)
    date_l = [int(elt) for elt in date.split('-')]
    time_l = [int(elt) for elt in time_.split(':')]
    return int(time.mktime(date_l + time_l + [0, 0, 0]))

rx_meth = re.compile("ZEO Server (\w+)\((.*)\) \('(.*)', (\d+)")

def parse_method(line):
    pass

def parse_line(line):
    """Parse a log entry and return time, method info, and client."""
    t = parse_time(line)
    if t is None:
        return None, None, None
    mo = rx_meth.search(line)
    if mo is None:
        return None, None, None
    meth_name = mo.group(1)
    meth_args = mo.group(2)
    meth_args = [s.strip() for s in meth_args.split(",")]
    m = meth_name, tuple(meth_args)
    c = mo.group(3), mo.group(4)
    return t, m, c

class TStats:
    pass

class TransactionParser:

    def __init__(self):
        self.transactions = []
        self.cur_t = {}
        self.skipped = 0

    def parse(self, line):
        t, m, c = parse_line(line)
        if t is None:
            return
        name = m[0]
        meth = getattr(self, name, None)
        if meth is not None:
            meth(t, m[1], c)

    def tpc_begin(self, time, args, client):
        t = TStats()
        t.begin = time
        t.url = args[2]
        t.objects = []
        self.cur_t[client] = t
        
    def tpc_finish(self, time, args, client):
        t = self.cur_t.get(client, None)
        if t is None:
            self.skipped += 1
            return
        t.finish = time
##        self.transactions.append(t)
        self.report(t)
        self.cur_t[client] = None

    def storea(self, time, args, client):
        t = self.cur_t.get(client, None)
        if t is None:
            self.skipped += 1
            return
        # append the oid and the length of the object
        # parse the length as [NNN]
        info = int(args[0]), int(args[1][1:-1])
        t.objects.append(info)

    def report(self, t):
        """Print a report about the transaction"""
        if t.objects:
            bytes = reduce(operator.add, [size for oid, size in t.objects])
        else:
            bytes = 0
        print "%s %2d %4d %10d %s" % (t.begin, t.finish - t.begin,
                                      len(t.objects), bytes, 
                                      time.ctime(t.begin)), t.url

if __name__ == "__main__":
    import fileinput

    p = TransactionParser()
    i = 0
    for line in fileinput.input():
        i += 1
        try:
            p.parse(line)
        except:
            print "line", i
            raise
    print len(p.transactions)
