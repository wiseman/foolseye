import subprocess
import tempfile
import random
import time
import os

import flask
from flask import request, g
import pymongo

import shopcop
import shopcop.views
import shopcop.tasks
from shopcop import app


g_tests = {}

def register_test(app, name, function):
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
    record_test_result(suspect_oid, test, 'queued')
    task = shopcop.tasks.Task(url='http://localhost:5000/_tsk/%s' % (test,),
                              params={'suspect_oid': str(suspect_oid),
                                      'image_oid': str(image_oid)},
                              method='GET')
    app.taskqueue.add_task(task)


def write_image_to_file(img_oid, path, database):
    img_reader = shopcop.views.get_image_from_store(img_oid, database=database)
    # Note that we don't have to close the img_reader.
    with open(path, 'wb') as img_writer:
        img_writer.write(img_reader.read())




#@register(app)
#@app.route('/_tsk/dummy_test')
#def dummy_test():
#    suspect_oid = request.args['suspect_oid']
#    sleep_time = random.randint(5, 15)
#    print 'Task %s running for %s seconds.' % (suspect_oid, sleep_time,)
#    time.sleep(sleep_time)
#    print 'Task %s done.' % (suspect_oid,)
#    return ''


@register(app)
@app.route('/_tsk/copymove_3_7')
def copymove_3_7():
    g.test_name = 'copymove_3_7'
    suspect_oid = pymongo.objectid.ObjectId(request.args['suspect_oid'])
    image_oid = pymongo.objectid.ObjectId(request.args['image_oid'])
    return copymove(suspect_oid, image_oid, quality=3, threshold=7)

@register(app)
@app.route('/_tsk/copymove_5_7')
def copymove_5_7():
    g.test_name = 'copymove_5_7'
    suspect_oid = pymongo.objectid.ObjectId(request.args['suspect_oid'])
    image_oid = pymongo.objectid.ObjectId(request.args['image_oid'])
    return copymove(suspect_oid, image_oid, quality=5, threshold=7)

@register(app)
@app.route('/_tsk/copymove_3_10')
def copymove_3_10():
    g.test_name = 'copymove_3_10'
    suspect_oid = pymongo.objectid.ObjectId(request.args['suspect_oid'])
    image_oid = pymongo.objectid.ObjectId(request.args['image_oid'])
    return copymove(suspect_oid, image_oid, quality=3, threshold=10)

@register(app)
@app.route('/_tsk/copymove_5_10')
def copymove_5_10():
    g.test_name = 'copymove_5_10'
    suspect_oid = pymongo.objectid.ObjectId(request.args['suspect_oid'])
    image_oid = pymongo.objectid.ObjectId(request.args['image_oid'])
    return copymove(suspect_oid, image_oid, quality=5, threshold=10)


def copymove(suspect_oid, image_oid, quality, threshold):
    record_test_result(suspect_oid, g.test_name, 'running')
    temp_dir = tempfile.mkdtemp()
    input_img_path = os.path.join(temp_dir, 'image.jpg')
    output_img_path = os.path.join(temp_dir, 'copymove.png')
    write_image_to_file(image_oid, input_img_path, g.db)
    args = ['copymove', input_img_path, output_img_path,
            str(quality), str(threshold)]
    status = subprocess.call(args)
    print 'status=%s, path=%s' % (status, output_img_path)
    if status != 0:
        abort(500)
    with open(output_img_path, 'rb') as img_reader:
        class ImgSaver(object):
            def save(self, gfile):
                gfile.write(img_reader.read())
        record_test_result(suspect_oid, g.test_name, 'finished', ImgSaver())
    return ''


def record_test_result(suspect_oid, test_name, status, result_img=None):
    result = {'name': test_name,
              'status': status}
    if result_img:
        print '!!! saving result image'
        result_img_id = shopcop.views.put_image_in_store(result_img, test_name)
        result['image'] = result_img_id
        result['thumbnails'] = shopcop.views.create_thumbnails(result_img_id)
    suspect = g.db.suspect_images.find_one({'_id': pymongo.objectid.ObjectId(suspect_oid)})
    suspect['tests'][test_name] = result
    g.db.suspect_images.save(suspect)
        
