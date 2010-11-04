import os.path
import subprocess
import tempfile
import shutil

import shopcop.tests
import shopcop.views
from shopcop import app


class CopyMove(shopcop.tests.Test):
    def __init__(self, blur, threshold):
        self.blur = blur
        self.threshold = threshold

    def display_name(self):
        return 'copymove blur=%s, threshold=%s' % (self.blur, self.threshold)

    def perform(self, db, suspect_oid, image_oid):
        temp_dir = tempfile.mkdtemp()
        try:
            input_img_path = os.path.join(temp_dir, 'image.jpg')
            output_img_path = os.path.join(temp_dir, 'copymove.jpg')
            shopcop.tests.write_image_to_file(db, image_oid, input_img_path)
            args = ['copymove', input_img_path, output_img_path,
                    str(self.blur), str(self.threshold)]
            print 'Calling [%s]' % (' '.join(args),)
            status = subprocess.call(args)
            if status != 0:
                abort(500)
            print 'DONE WITH task %s' % (self.name,)
            result_img_oid = shopcop.views.put_image_file_in_store(db, output_img_path, self.name)
            result = {'image': result_img_oid,
                      'thumbnails': shopcop.views.create_thumbnails(result_img_oid)}
            return result
        finally:
            shutil.rmtree(temp_dir)


shopcop.tests.register_test(app, 'copymove_3_7',  CopyMove(3, 7))
shopcop.tests.register_test(app, 'copymove_3_10', CopyMove(3, 10))
shopcop.tests.register_test(app, 'copymove_5_7',  CopyMove(5, 7))
shopcop.tests.register_test(app, 'copymove_5_10', CopyMove(5, 10))

            
