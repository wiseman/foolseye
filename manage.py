import subprocess

from flaskext.script import Manager

from shopcop import app

manager = Manager(app)


UPLOAD_URL = 'http://localhost:5000/upload'

@manager.command
def upload_image(path):
  args = ['curl',
          '-F', 'file=@%s' % (path,), UPLOAD_URL]
  status = subprocess.call(args)
  if status != 0:
    raise ValueError('Attempt to run %s failed with status=%s' % (args, status))



  
if __name__ == "__main__":
    manager.run()
