from glob import glob
from re import A

from sortedcontainers import SortedDict
import datetime

from aggregator import utils

a = 0
@utils.memoize_2
def inc(sorted_dates, day):
    global a
    a += 1
    return a

def test_memoize_2():
    arg = SortedDict()
    day = datetime.datetime.now()
    res = inc(arg, day)
    res2 = inc(arg, day)
    assert res == res2
