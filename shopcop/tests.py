import subprocess
import tempfile
import random
import time

import shopcop.tasks


g_tests = {}

def register_test(name, function):
    print 'Registering test %s/%s' % (name, function)
    g_tests[name] = function

def all_tests():
    return g_tests.keys()

def get_test(name):
    return g_tests[name]

def run_test(name, suspect_oid, img_oid):
    return apply(g_tests[name], [suspect_oid, img_oid])


class register(object):
    def __init__(self, name=None):
        self.name = name

    def __call__(self, fn):
        print 'inside __call__'
        if self.name is None:
            self.name = fn.__name__
        register_test(self.name, fn)
        return fn
    


def start_test_task(test, sender, suspect_oid, image_oid):
    task = shopcop.tasks.AsyncTask(get_test(test), [suspect_oid, image_oid])
    task_id = task.start()
    record_task_status(suspect_oid, task)

def record_task_status(suspect_oid, task):
    print 'Recording status for %s' % (task,)




@register()
def dummy_test(suspect_id, image_oid):
    sleep_time = random.randint(5, 15)
    print 'Task %s running for %s seconds.' % (suspect_id, sleep_time,)
    time.sleep(sleep_time)
    print 'Task %s done.' % (suspect_id,)


