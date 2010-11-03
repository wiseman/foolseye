import subprocess
import tempfile
import random
import time
import os
import shutil
import urlparse
import json

import flask
from flask import request, g
import pymongo
import pymongo.json_util

import Image
import ImageChops
import ImageEnhance

import shopcop
import shopcop.views
import shopcop.tasks
from shopcop import app


RUNNING = 'running'
QUEUED = 'queued'
FINISHED = 'finished'


class Test(object):
    def __init__(self):
        self.name = None
        
    def name(self):
        raise NotImplementedYet

    def display_name(self):
        return self.name

    def run(self, db, suspect_oid, image_oid):
        record_test_status(db, suspect_oid, self.name, RUNNING)
        result = self.perform(db, suspect_oid, image_oid)
        record_test_status(db, suspect_oid, self.name, FINISHED, result=result)
        return result

def make_test_view_func(test):
    def view_func():
        suspect_oid = pymongo.objectid.ObjectId(request.args['suspect_oid'])
        image_oid = pymongo.objectid.ObjectId(request.args['image_oid'])
        result = test.run(g.db, suspect_oid, image_oid)
        return json.dumps(result, default=pymongo.json_util.default)
    return view_func


g_tests = {}

def register_test(app, name, test):
    url = '/_tsk/%s' %(name,)
    endpoint = 'task_%s' % (name,)
    test.name = name
    g_tests[name] = (url, test)
    #print 'registering %s %s %s' % (u
    app.add_url_rule(url, endpoint, make_test_view_func(test))

def all_tests():
    return g_tests.keys()

def get_test(name):
    return g_tests[name]
    
def enqueue_test(app, db, name, suspect_oid, image_oid):
    print 'ENQUEUEING %s' % (name, )
    record_test_status(db, suspect_oid, name, QUEUED)
    url, test = get_test(name)
    # In the future maybe we'll distribute tasks to different hosts or
    # something, but for now...
    host = 'localhost'
    port = 5000
    url = urlparse.urljoin('http://%s:%s/' % (host, port), url)
    task = shopcop.tasks.Task(url=url,
                              params={'suspect_oid': str(suspect_oid),
                                      'image_oid': str(image_oid)},
                              method='GET')
    app.taskqueue.add_task(task)

def start_test_task(test, app, suspect_oid, image_oid):
    print 'test=%s' % (`test`,)
    record_test_result(suspect_oid, test, 'queued')
    task = shopcop.tasks.Task(url='http://localhost:5000/_tsk/%s' % (test,),
                              params={'suspect_oid': str(suspect_oid),
                                      'image_oid': str(image_oid)},
                              method='GET')
    app.taskqueue.add_task(task)

def record_test_status(db, suspect_oid, test_name, status, result=None):
    if result == None:
        result = {}
    result['name'] = test_name
    result['display_name'] = get_test(test_name)[1].display_name()
    result['status'] = status
    suspect = db.suspect_images.find_one({'_id': pymongo.objectid.ObjectId(suspect_oid)})
    suspect['tests'][test_name] = result
    db.suspect_images.save(suspect)



def write_image_to_file(db, img_oid, path):
    img_reader = shopcop.views.get_image_from_store(db, img_oid)
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


## @register(app)
## @app.route('/_tsk/copymove_3_7')
## def copymove_3_7():
##     g.test_name = 'copymove_3_7'
##     suspect_oid = pymongo.objectid.ObjectId(request.args['suspect_oid'])
##     image_oid = pymongo.objectid.ObjectId(request.args['image_oid'])
##     return copymove(suspect_oid, image_oid, quality=3, threshold=7)

## @register(app)
## @app.route('/_tsk/copymove_5_7')
## def copymove_5_7():
##     g.test_name = 'copymove_5_7'
##     suspect_oid = pymongo.objectid.ObjectId(request.args['suspect_oid'])
##     image_oid = pymongo.objectid.ObjectId(request.args['image_oid'])
##     return copymove(suspect_oid, image_oid, quality=5, threshold=7)

## @register(app)
## @app.route('/_tsk/copymove_3_10')
## def copymove_3_10():
##     g.test_name = 'copymove_3_10'
##     suspect_oid = pymongo.objectid.ObjectId(request.args['suspect_oid'])
##     image_oid = pymongo.objectid.ObjectId(request.args['image_oid'])
##     return copymove(suspect_oid, image_oid, quality=3, threshold=10)

## @register(app)
## @app.route('/_tsk/copymove_5_10')
## def copymove_5_10():
##     g.test_name = 'copymove_5_10'
##     suspect_oid = pymongo.objectid.ObjectId(request.args['suspect_oid'])
##     image_oid = pymongo.objectid.ObjectId(request.args['image_oid'])
##     return copymove(suspect_oid, image_oid, quality=5, threshold=10)


## def copymove(suspect_oid, image_oid, quality, threshold):
##     record_test_result(suspect_oid, g.test_name, 'running')
##     temp_dir = tempfile.mkdtemp()
##     try:
##         input_img_path = os.path.join(temp_dir, 'image.jpg')
##         output_img_path = os.path.join(temp_dir, 'copymove.png')
##         write_image_to_file(image_oid, input_img_path, g.db)
##         args = ['copymove', input_img_path, output_img_path,
##                 str(quality), str(threshold)]
##         status = subprocess.call(args)
##         print 'status=%s, path=%s' % (status, output_img_path)
##         if status != 0:
##             abort(500)
##         with open(output_img_path, 'rb') as img_reader:
##             class ImgSaver(object):
##                 def save(self, gfile):
##                     gfile.write(img_reader.read())
##             record_test_result(suspect_oid, g.test_name, 'finished', ImgSaver())
##         return ''
##     finally:
##         shutil.rmtree(temp_dir)
        


## def record_test_result(suspect_oid, test_name, status, result_img=None):
##     result = {'name': test_name,
##               'status': status}
##     if result_img:
##         print '!!! saving result image'
##         result_img_id = shopcop.views.put_image_in_store(result_img, test_name)
##         result['image'] = result_img_id
##         result['thumbnails'] = shopcop.views.create_thumbnails(result_img_id)
##     suspect = g.db.suspect_images.find_one({'_id': pymongo.objectid.ObjectId(suspect_oid)})
##     suspect['tests'][test_name] = result
##     g.db.suspect_images.save(suspect)
    


## @register(app)
## @app.route('/_tsk/errorlevelanalysis')
## def errorlevelanalysis():
##     g.test_name = 'errorlevelanalysis'
##     suspect_oid = pymongo.objectid.ObjectId(request.args['suspect_oid'])
##     image_oid = pymongo.objectid.ObjectId(request.args['image_oid'])
##     return error_level_analysis(suspect_oid, image_oid, enhance_factor=40)


## def error_level_analysis(suspect_oid, image_oid, enhance_factor):
##     record_test_result(suspect_oid, g.test_name, 'running')
##     temp_dir = tempfile.mkdtemp()
##     try:
##         input_img_path = os.path.join(temp_dir, 'image.jpg')
##         output_img_path = os.path.join(temp_dir, 'ela.jpg')
##         write_image_to_file(image_oid, input_img_path, g.db)

##         im = Image.open(input_img_path)
##         im.save(os.path.join(temp_dir, '95.jpg'), quality=95)
##         nf = Image.open(os.path.join(temp_dir, '95.jpg'))
##         ela = ImageChops.difference(im, nf)
##         ela.save(os.path.join(temp_dir, 'ela.jpg'), quality=95)
##         enhancer = ImageEnhance.Brightness(ela)
##         enhanced = enhancer.enhance(enhance_factor)
##         enhanced.save(output_img_path, quality=95)

##         with open(output_img_path, 'rb') as img_reader:
##             class ImgSaver(object):
##                 def save(self, gfile):
##                     gfile.write(img_reader.read())
##             record_test_result(suspect_oid, g.test_name, 'finished', ImgSaver())
##         return ''
##     finally:
##         shutil.rmtree(temp_dir)

