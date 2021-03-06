import os
import os.path
import datetime
import pprint
import time


from shopcop import app
import shopcop.tests

import flask
from flask import Flask, g, request, redirect, url_for, send_file
import gridfs
import pymongo.objectid
import Image as PILImage
import ImageOps as PILImageOps
import flask.signals



shopcop_signals = flask.signals.Namespace()
suspect_was_uploaded = shopcop_signals.signal('suspect_was_uploaded')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Receive an uploaded file.
        file = request.files['file']
        if file and allowed_file(file.filename):
            img_oid = put_image_in_store(g.db, file, file.filename)
            suspect = {'image': img_oid,
                       'filename': file.filename,
                       'uploaded_at': datetime.datetime.utcnow(),
                       'uploaded_by': request.environ['REMOTE_ADDR'],
                       'thumbnails': create_thumbnails(img_oid),
                       'tests': {},
                       'comments': []}
            oid = g.db.suspect_images.insert(suspect)
            suspect_was_uploaded.send(app, suspect_oid=oid, image_oid=img_oid)
            return redirect(url_for('image', oid=oid))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit name=submit value=Upload>
    </form>
    '''

def create_thumbnails(img_oid):
    start = time.time()
    thumbnails = {}
    for size in app.config['IMAGE_SIZES']:
        d = {}
        dimensions = app.config['IMAGE_SIZES'][size]
        oid, dimensions = resize_image(img_oid, dimensions)
        d = {'oid': oid,
             'size': size,
             'dimensions': dimensions}
        thumbnails[size] = d
    end = time.time()
    print 'Created thumbnails in %s seconds' % (end - start, )
    return thumbnails
    

@app.route('/')
def index():
    return redirect(url_for('newest'))


@app.route('/newest')
def newest():
    page_size = 10
    skip = 0
    if 'skip' in request.args:
        print 'setting skip=%s' % (request.args['skip'],)
        skip = int(request.args['skip'])
    g.db.suspect_images.create_index('uploaded_at')
    suspects, has_prev, has_next = \
              get_page_of_results(g.db.suspect_images,
                                  sort=[('uploaded_at', pymongo.DESCENDING)],
                                  skip=skip,
                                  limit=page_size)
    print 'has_prev=%s' % (has_prev,)
    prev_skip = None
    if has_prev:
        prev_skip = skip - page_size
        if prev_skip <= 0:
            prev_skip = 0
        prev_skip = str(prev_skip)

    print 'prev_skip=%s' % (prev_skip,)
    next_skip = None
    if has_next:
        next_skip = skip + page_size

    return flask.render_template('newest.html',
                                 suspects=suspects, prev_skip=prev_skip, next_skip=next_skip)


def get_page_of_results(collection, sort, skip, limit):
    cursor = collection.find(sort=sort).skip(skip).limit(limit + 1)
    results = list(cursor)
    has_prev_results = skip > 0
    has_next_results = len(results) > limit
    return results[0:limit], has_prev_results, has_next_results
    

@app.route('/image/<oid>')
def image(oid):
    suspect = g.db.suspect_images.find_one({'_id': pymongo.objectid.ObjectId(oid)})
    if not suspect:
        flask.abort(404)
    return flask.render_template('image.html', suspect=suspect)


@app.route('/imgstore/<oid>')
def imgstore(oid):
    "Handles image store URLs."
    gfile = None
    try:
        gfile = get_image_from_store(g.db, pymongo.objectid.ObjectId(oid))
    except pymongo.objectid.InvalidId:
        pass
    if not gfile:
        flask.abort(404)
    return send_file(gfile, mimetype=gfile.content_type, add_etags=False)
    

def put_image_in_store(db, img_src, filename):
    "Stores an image in the GridFS store."
    fs = gridfs.GridFS(db, 'fs_images')
    content_type = 'JPEG'
    if hasattr(img_src, 'content_type'):
        content_type = img_src.content_type
    gfile = fs.new_file(filename=filename, content_type=content_type)
    try:
        if isinstance(img_src, PILImage.Image):
            img_src = img_src.convert('RGB')
            img_src.save(gfile, 'JPEG')
        else:
            img_src.save(gfile)
    finally:
        gfile.close()
    return gfile._id

def put_image_file_in_store(db, path, filename):
    class ImgSaver(object):
        def save(self, gfile):
            with open(path, 'rb') as img_reader:
                gfile.write(img_reader.read())
    return put_image_in_store(db, ImgSaver(), filename)


def get_image_from_store(db, oid):
    "Retrieves an image from the GridFS store."
    fs = gridfs.GridFS(db, 'fs_images')
    oid = pymongo.objectid.ObjectId(oid)
    gfile = fs.get(oid)
    return gfile


def resize_image(oid, size_spec):
    square = False
    size = size_spec
    if isinstance(size_spec, dict):
        if 'square' in size_spec:
            square = size_spec['square']
        size = size_spec['size']
    
    image = get_image_from_store(g.db, oid)
    pil_image = PILImage.open(image)
    if square:
        pil_image = PILImageOps.fit(pil_image, size, PILImage.ANTIALIAS)
    else:
        pil_image.thumbnail(size, PILImage.ANTIALIAS)
    return put_image_in_store(g.db, pil_image, image.filename), pil_image.size


@suspect_was_uploaded.connect_via(app)
def when_suspect_uploaded(sender, suspect_oid, image_oid):
    print '%s: uploaded suspect %s (image %s)' % (sender, suspect_oid, image_oid)
    print 'tests: %s' % (shopcop.tests.all_tests(),)
    for test in shopcop.tests.all_tests():
        shopcop.tests.enqueue_test(app, g.db, test, suspect_oid, image_oid)



@app.route('/new_comment', methods=['POST'])
def new_comment():
    comment = {'author': request.environ['REMOTE_ADDR'],
               'posted_at': datetime.datetime.utcnow(),
               'text': request.form['text']}
    suspect_oid = pymongo.objectid.ObjectId(request.form['suspect_oid'])
    suspect = g.db.suspect_images.find_one({'_id': suspect_oid})
    suspect['comments'] += [comment]
    g.db.suspect_images.save(suspect)
    return redirect(url_for('image', oid=suspect_oid))
