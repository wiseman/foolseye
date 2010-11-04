import os.path
import tempfile
import shutil

import Image
import ImageEnhance
import ImageChops

import shopcop.tests
import shopcop.views
from shopcop import app


class ErrorLevelAnalysis(shopcop.tests.Test):
    def __init__(self, enhance_factor=40):
        self.enhance_factor = enhance_factor

    def display_name(self):
        return "error level analysis"

    def perform(self, db, suspect_oid, image_oid):
        temp_dir = tempfile.mkdtemp()
        try:
            input_img_path = os.path.join(temp_dir, 'image.jpg')
            output_img_path = os.path.join(temp_dir, 'ela.jpg')
            shopcop.tests.write_image_to_file(db, image_oid, input_img_path)

            im = Image.open(input_img_path)
            im.save(os.path.join(temp_dir, '95.jpg'), quality=95)
            nf = Image.open(os.path.join(temp_dir, '95.jpg'))
            ela = ImageChops.difference(im, nf)
            ela.save(os.path.join(temp_dir, 'ela.jpg'), quality=95)
            enhancer = ImageEnhance.Brightness(ela)
            enhanced = enhancer.enhance(self.enhance_factor)
            enhanced.save(output_img_path, quality=95)

            result_img_oid = shopcop.views.put_image_file_in_store(db, output_img_path, self.name)
            result = {'image': result_img_oid,
                      'thumbnails': shopcop.views.create_thumbnails(result_img_oid)}
            return result
        finally:
            shutil.rmtree(temp_dir)


shopcop.tests.register_test(app, 'errorlevelanalysis', ErrorLevelAnalysis())
