import cachetools

def memoize(f):
    memo = {}
    def helper(x, *args):
        key = '-'.join([x, *args])
        if key not in memo:
            memo[key] = f(x, *args)
        return memo[key]
    return helper

def memoize_with_id(f):
    memo = cachetools.LFUCache(maxsize=10)
    def helper(x, *args):
        key = id(x)
        if key not in memo:
            memo[key] = (f(x, *args), x)
        return memo[key][0]
    return helper

def memoize_with_ids(f):
    memo = cachetools.LFUCache(maxsize=10)
    def helper(*args):
        key = tuple(id(v) for v in args)
        if key not in memo:
            memo[key] = (f(*args), args)
        else:
            print('found')
        return memo[key][0]
    return helper

def compute_hash(value):
    if value.__hash__ is None:
        return id(value)
    return value

def memoize_2(f):
    memo = cachetools.LRUCache(maxsize=50)
    def helper(*args, **kwargs):
        key = tuple(compute_hash(v) for v in args)
        if key not in memo:
            memo[key] = (f(*args, **kwargs), args)
        else:
            #print('found')
            pass
        return memo[key][0]
    return helper


def cprofile(fun, sortby='cumulative'):
    import cProfile
    import io
    import pstats
    import time
    import six

    """
    Prints out a summary of how much time is spent in nested functions.
    sortby: "calls", "ncalls", "cumtime", "cumulative", "file", "filename",
            "line", "module", "name", "nfl", "pcalls", "stdname", "time",
            "tottime"
    """
    @six.wraps(fun)
    def wrapped(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()

        ret = fun(*args, **kwargs)

        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats(200)

        print(fun.__name__, s.getvalue())

        return ret
    return wrapped