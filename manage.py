import subprocess

import flaskext.script
from flaskext.script import Manager

from shopcop import app

manager = Manager(app)


manager.add_command('runserver', flaskext.script.Server(threaded=True))


UPLOAD_URL = 'http://localhost:5000/upload'

@manager.command
def upload_image(path):
    args = ['curl',
            '-F', 'file=@%s' % (path,), UPLOAD_URL]
    status = subprocess.call(args)





  
if __name__ == "__main__":
    manager.run()
