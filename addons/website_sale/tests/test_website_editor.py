from odoo.tests import HttpCase, new_test_user, tagged
from json.decoder import JSONDecodeError
GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="  # Tiny blank base64 image data.
ATTACHMENT_COUNT = 5


@tagged('post_install', '-at_install')
class TestProductPictureController(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, "test_user", email="test_user@nowhere.com",
                                 password="Password_test",
                                 groups='website.group_website_publisher,base.group_user,account.group_account_manager')
        cls.product = cls.env['product.product'].create({
            'name': 'Storage Test Box',
            'standard_price': 70.0,
            'list_price': 79.0,
            'website_published': True,
        })

        cls.attachments = cls.env['ir.attachment'].create([
            {
                'datas': GIF,
                'name': f'image0{i}.gif',
                'public': True
            }
            for i in range(ATTACHMENT_COUNT)])

    def create_product_images_from_route(self):
        try:
            self.opener.post(
                url=f'{self.base_url()}/shop/product/extra-images',
                json={
                    'params': {
                        'images': [{
                            'id': i
                        } for i in self.attachments.mapped('id')],
                        'product_product_id': self.product.id,
                        'product_template_id': self.product.product_tmpl_id.id
                    }
                }
            ).json()
            return True
        except JSONDecodeError:
            return False

    def test_authenticated_bulk_image_upload(self):
        self.authenticate("test_user", "Password_test")
        # Turns attachments to product_images
        self.assertTrue(self.create_product_images_from_route())

        # Check if the media now exists on the product :
        for i in self.product.product_template_image_ids:
            # Check if all names are now in the product
            self.assertIn(i.name, self.attachments.mapped('name'))
            # Check if image datas are the same
            self.assertEqual(i.image_1920, GIF)
        # Check if exactly ATTACHMENT_COUNT images were saved (no dupes/misses?)
        self.assertEqual(ATTACHMENT_COUNT, len(self.product.product_template_image_ids))

    def test_authenticated_image_clear(self):
        self.authenticate("test_user", "Password_test")

        # First create some images
        self.assertTrue(self.create_product_images_from_route())
        self.assertEqual(ATTACHMENT_COUNT, len(self.product.product_template_image_ids))

        # Remove all images
        # (Exception raised if error)
        self.opener.post(
            url=f'{self.base_url()}/shop/product/clear-images',
            json={
                'params': {
                    'product_product_id': self.product.id,
                    'product_template_id': self.product.product_tmpl_id.id
                }
            }  # Required to make this a json request.
        )

        # According to the product, there are no variants images.
        self.assertEqual(0, len(self.product.product_template_image_ids))
