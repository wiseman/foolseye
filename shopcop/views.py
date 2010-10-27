import os
import os.path

from shopcop import app
import flask
from flask import Flask, g, request, redirect, url_for, send_file
import gridfs
import pymongo.objectid



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Receive an uploaded file.
        file = request.files['file']
        if file and allowed_file(file.filename):
            oid = put_image_in_store(file)
            return redirect(url_for('imgstore', oid=oid))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

@app.route('/image/<oid>')
def image(oid):
    img = db.suspect_images.find_one({'_id': pymongo.objectid.ObjectId(oid)})
    if not img:
        flask.abort(404)
    flask.render_template('image.html', image=img)


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
    gfile = fs.new_file(filename=img_src.filename, content_type=img_src.content_type)
    try:
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


