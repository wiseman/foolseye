import os.path


DEBUG = 'true'

DATABASE_CONNECTION = 'mongodb://localhost'
DATABASE_NAME = 'shopcop'

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

