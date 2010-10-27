import os
import os.path
import datetime
import pprint
import time

from shopcop import app
import flask
from flask import Flask, g, request, redirect, url_for, send_file
import gridfs
import pymongo.objectid
import Image as PILImage
import ImageOps as PILImageOps


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Receive an uploaded file.
        file = request.files['file']
        if file and allowed_file(file.filename):
            img_oid = put_image_in_store(file)
            suspect = {'image': img_oid,
                       'filename': file.filename,
                       'uploaded_at': datetime.datetime.utcnow(),
                       'uploaded_by': request.environ['REMOTE_ADDR'],
                       'thumbnails': create_thumbnails(img_oid)}
            oid = g.db.suspect_images.insert(suspect)
            return redirect(url_for('image', oid=oid))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

def create_thumbnails(img_oid):
    thumbnails = {}
    for size in app.config['IMAGE_SIZES']:
        d = {}
        dimensions = app.config['IMAGE_SIZES'][size]
        oid, dimensions = resize_image(img_oid, dimensions)
        d = {'oid': oid,
             'size': size,
             'dimensions': dimensions}
        thumbnails[size] = d
    return thumbnails
    

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
        gfile = get_image_from_store(pymongo.objectid.ObjectId(oid))
    except pymongo.objectid.InvalidId:
        pass
    if not gfile:
        flask.abort(404)
    return send_file(gfile, mimetype=gfile.content_type, add_etags=False)
    

def put_image_in_store(img_src):
    "Stores an image in the GridFS store."
    fs = gridfs.GridFS(g.db, 'fs_images')
    content_type = 'JPEG'
    if hasattr(img_src, 'content_type'):
        content_type = img_src.content_type
    gfile = fs.new_file(filename=img_src.filename, content_type=content_type)
    try:
        if isinstance(img_src, PILImage.Image):
            img_src = img_src.convert('RGB')
            img_src.save(gfile, 'JPEG')
        else:
            img_src.save(gfile)
    finally:
        gfile.close()
    return gfile._id


def get_image_from_store(oid):
    "Retrieves an image from the GridFS store."
    fs = gridfs.GridFS(g.db, 'fs_images')
    oid = pymongo.objectid.ObjectId(oid)
    gfile = fs.get(oid)
    return gfile


def resize_image(oid, size):
    image = get_image_from_store(oid)
    pil_image = PILImage.open(image)
    print '*** Resizing to %s' % (size,)
    pil_image.thumbnail(size, PILImage.ANTIALIAS)
    print '      Resized to %s' % (pil_image.size,)
    return put_image_in_store(pil_image), pil_image.size
