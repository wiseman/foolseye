import subprocess
import tempfile
import random
import time
import os

import shopcop
import shopcop.tasks


g_tests = {}

def register_test(name, function):
    print 'Registering test %s/%s' % (name, function)
    g_tests[name] = function

def all_tests():
    return g_tests.keys()

def get_test(name):
    return g_tests[name]

def run_test(name, app, suspect_oid, img_oid):
    return apply(g_tests[name], [suspect_oid, img_oid])

def test_runner(name):
    def run_test(app, suspect_oid, img_oid):
        # Get database connection.
        connection, db = shopcop.connect_db(app)
        try:
            apply(get_test(name), [app, db, suspect_oid, img_oid])
        finally:
            connection.end_request()
    return run_test
        

class register(object):
    def __init__(self, name=None):
        self.name = name

    def __call__(self, fn):
        if self.name is None:
            self.name = fn.__name__
        register_test(self.name, fn)
        return fn
    


def start_test_task(test, app, suspect_oid, image_oid):
    task = shopcop.tasks.AsyncTask(test_runner(test), [app, suspect_oid, image_oid])
    task_id = task.start()
    record_task_status(suspect_oid, task)

def record_task_status(suspect_oid, task):
    print 'Recording status for %s' % (task,)


def write_image_to_file(img_oid, path, database):
    img_reader = shopcop.views.get_image_from_store(img_oid, database=database)
    # Note that we don't have to close the img_reader.
    with open(path, 'wb') as img_writer:
        img_writer.write(img_reader.read())




@register()
def dummy_test(app, db, suspect_oid, image_oid):
    sleep_time = random.randint(5, 15)
    print 'Task %s running for %s seconds.' % (suspect_oid, sleep_time,)
    time.sleep(sleep_time)
    print 'Task %s done.' % (suspect_oid,)


@register()
def copymove_5_7(app, db, suspect_oid, image_oid):
    copymove(app, db, suspect_oid, image_oid, quality=5, threshold=7)

def copymove(app, db, suspect_oid, image_oid, quality, threshold):
    temp_dir = tempfile.mkdtemp()
    input_img_path = os.path.join(temp_dir, 'image.jpg')
    output_img_path = os.path.join(temp_dir, 'copymove.png')
    write_image_to_file(image_oid, input_img_path, db)
    args = ['/Users/wiseman/src/shopcop/copymove/copymove', input_img_path, output_img_path,
            str(quality), str(threshold)]
    print args
    status = subprocess.call(args)
