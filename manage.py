import subprocess

import flaskext.script
from flaskext.script import Manager

from shopcop import app
import shopcop


manager = Manager(app)


manager.add_command('runserver', flaskext.script.Server(threaded=True))


UPLOAD_URL = 'http://localhost:5000/upload'

@manager.command
def uploadimage(path):
    args = ['curl',
            '-F', 'file=@%s' % (path,), UPLOAD_URL]
    status = subprocess.call(args)


@manager.command
def wipedb():
    connection, db = shopcop.connect_db()
    connection.drop_database(db)
    
    




  
if __name__ == "__main__":
    manager.run()
