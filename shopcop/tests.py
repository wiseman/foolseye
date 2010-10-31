import subprocess
import tempfile
import random
import time
import os

import flask
from flask import request, g
import pymongo

import shopcop
import shopcop.tasks
from shopcop import app


g_tests = {}

def register_test(app, name, function):
    print 'Registering test %s/%s' % (name, function)
    g_tests[name] = function
    app.add_url_rule('/_tsk/%s' % (name,), None, function)

def all_tests():
    return g_tests.keys()

def get_test(name):
    return g_tests[name]


class register(object):
    def __init__(self, app, name=None):
        self.name = name
        self.app = app

    def __call__(self, fn):
        if self.name is None:
            self.name = fn.__name__
        register_test(app, self.name, fn)
        
        return fn
    


def start_test_task(test, app, suspect_oid, image_oid):
    print 'test=%s' % (`test`,)
    shopcop.tasks.add_task(url='http://localhost:5000/_tsk/%s' % (test,),
                           params={'suspect_oid': str(suspect_oid),
                                   'image_oid': str(image_oid)},
                           method='GET')


def write_image_to_file(img_oid, path, database):
    img_reader = shopcop.views.get_image_from_store(img_oid, database=database)
    # Note that we don't have to close the img_reader.
    with open(path, 'wb') as img_writer:
        img_writer.write(img_reader.read())




@register(app)
@app.route('/_tsk/dummy_test')
def dummy_test():
    suspect_oid = request.args['suspect_oid']
    sleep_time = random.randint(5, 15)
    print 'Task %s running for %s seconds.' % (suspect_oid, sleep_time,)
    time.sleep(sleep_time)
    print 'Task %s done.' % (suspect_oid,)
    return ''

@register(app)
@app.route('/_tsk/copymove_5_7')
def copymove_5_7():
    suspect_oid = pymongo.objectid.ObjectId(request.args['suspect_oid'])
    image_oid = pymongo.objectid.ObjectId(request.args['image_oid'])
    return copymove(app, g.db, suspect_oid, image_oid, quality=5, threshold=7)

def copymove(app, db, suspect_oid, image_oid, quality, threshold):
    temp_dir = tempfile.mkdtemp()
    input_img_path = os.path.join(temp_dir, 'image.jpg')
    output_img_path = os.path.join(temp_dir, 'copymove.png')
    write_image_to_file(image_oid, input_img_path, db)
    args = ['/Users/wiseman/src/shopcop/copymove/copymove', input_img_path, output_img_path,
            str(quality), str(threshold)]
    print args
    status = subprocess.call(args)
    if status != 0:
        abort(500)
    return ''
