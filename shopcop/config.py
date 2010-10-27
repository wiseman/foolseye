import os.path


DEBUG = 'true'

DATABASE_CONNECTION = 'mongodb://localhost'
DATABASE_NAME = 'shopcop'

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])


IMAGE_SIZES = {'square': (75, 75),
               'thumbnail': (100, 100),
               'small': (240,240),
               'medium500': (500, 500),
               'medium640': (640, 640),
               'large': (1024, 1024)}

               
