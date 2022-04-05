# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import binascii
from concurrent.futures import Future
import io

from PIL import Image, ImageOps
# We can preload Ico too because it is considered safe
from PIL import IcoImagePlugin

from random import randrange

from odoo.exceptions import UserError
from odoo.tools.translate import _


# Preload PIL with the minimal subset of image formats we need
Image.preinit()
Image._initialized = 2

# Maps only the 6 first bits of the base64 data, accurate enough
# for our purpose and faster than decoding the full blob first
FILETYPE_BASE64_MAGICWORD = {
    b'/': 'jpg',
    b'R': 'gif',
    b'i': 'png',
    b'P': 'svg+xml',
    b'U': 'webp',
}

EXIF_TAG_ORIENTATION = 0x112
# The target is to have 1st row/col to be top/left
# Note: rotate is counterclockwise
EXIF_TAG_ORIENTATION_TO_TRANSPOSE_METHODS = {  # Initial side on 1st row/col:
    0: [],                                          # reserved
    1: [],                                          # top/left
    2: [Image.FLIP_LEFT_RIGHT],                     # top/right
    3: [Image.ROTATE_180],                          # bottom/right
    4: [Image.FLIP_TOP_BOTTOM],                     # bottom/left
    5: [Image.FLIP_LEFT_RIGHT, Image.ROTATE_90],    # left/top
    6: [Image.ROTATE_270],                          # right/top
    7: [Image.FLIP_TOP_BOTTOM, Image.ROTATE_90],    # right/bottom
    8: [Image.ROTATE_90],                           # left/bottom
}

# Arbitrary limit to fit most resolutions, including Nokia Lumia 1020 photo,
# 8K with a ratio up to 16:10, and almost all variants of 4320p
IMAGE_MAX_RESOLUTION = 45e6


class ImageProcess():

    def __init__(self, source, verify_resolution=True):
        """Initialize the `source` image for processing.

        :param source: the original image binary

            No processing will be done if the `source` is falsy or if
            the image is SVG.

        :param verify_resolution: if True, make sure the original image size is not
            excessive before starting to process it. The max allowed resolution is
            defined by `IMAGE_MAX_RESOLUTION`.
        :type verify_resolution: bool
        :rtype: ImageProcess

        :raise: ValueError if `verify_resolution` is True and the image is too large
        :raise: UserError if the image can't be identified by PIL
        """
        self.source = source or False
        self.operationsCount = 0

        if not source or source[:1] == b'<' or (source[0:4] == b'RIFF' and source[8:15] == b'WEBPVP8'):
            # don't process empty source or SVG or WEBP
            self.image = False
        else:
            try:
                self.image = Image.open(io.BytesIO(source))
            except (OSError, binascii.Error):
                raise UserError(_("This file could not be decoded as an image file."))

            # Original format has to be saved before fixing the orientation or
            # doing any other operations because the information will be lost on
            # the resulting image.
            self.original_format = (self.image.format or '').upper()

            self.image = image_fix_orientation(self.image)

            w, h = self.image.size
            if verify_resolution and w * h > IMAGE_MAX_RESOLUTION:
                raise ValueError(_("Image size excessive, uploaded images must be smaller than %s million pixels.", str(IMAGE_MAX_RESOLUTION / 10e6)))

    def image_quality(self, quality=0, output_format=''):
        """Return the image resulting of all the image processing
        operations that have been applied previously.

        Return False if the initialized `image` was falsy, and return
        the initialized `image` without change if it was SVG.

        Also return the initialized `image` if no operations have been applied
        and the `output_format` is the same as the original format and the
        quality is not specified.

        :param int quality: quality setting to apply. Default to 0.

            - for JPEG: 1 is worse, 95 is best. Values above 95 should be
              avoided. Falsy values will fallback to 95, but only if the image
              was changed, otherwise the original image is returned.
            - for PNG: set falsy to prevent conversion to a WEB palette.
            - for other formats: no effect.
        :param str output_format: the output format. Can be PNG, JPEG, GIF, or ICO.
            Default to the format of the original image. BMP is converted to
            PNG, other formats than those mentioned above are converted to JPEG.
        :return: image
        :rtype: bytes or False
        """
        if not self.image:
            return self.source

        output_image = self.image

        output_format = output_format.upper() or self.original_format
        if output_format == 'BMP':
            output_format = 'PNG'
        elif output_format not in ['PNG', 'JPEG', 'GIF', 'ICO']:
            output_format = 'JPEG'

        if not self.operationsCount and output_format == self.original_format and not quality:
            return self.source

        opt = {'output_format': output_format}

        if output_format == 'PNG':
            opt['optimize'] = True
            if quality:
                if output_image.mode != 'P':
                    # Floyd Steinberg dithering by default
                    output_image = output_image.convert('RGBA').convert('P', palette=Image.WEB, colors=256)
        if output_format == 'JPEG':
            opt['optimize'] = True
            opt['quality'] = quality or 95
        if output_format == 'GIF':
            opt['optimize'] = True
            opt['save_all'] = True

        if output_image.mode not in ["1", "L", "P", "RGB", "RGBA"] or (output_format == 'JPEG' and output_image.mode == 'RGBA'):
            output_image = output_image.convert("RGB")

        return image_apply_opt(output_image, **opt)

    def resize(self, max_width=0, max_height=0):
        """Resize the image.

        The image is never resized above the current image size. This method is
        only to create a smaller version of the image.

        The current ratio is preserved. To change the ratio, see `crop_resize`.

        If `max_width` or `max_height` is falsy, it will be computed from the
        other to keep the current ratio. If both are falsy, no resize is done.

        It is currently not supported for GIF because we do not handle all the
        frames properly.

        :param int max_width: max width
        :param int max_height: max height
        :return: self to allow chaining
        :rtype: ImageProcess
        """
        if self.image and self.original_format != 'GIF' and (max_width or max_height):
            w, h = self.image.size
            asked_width = max_width or (w * max_height) // h
            asked_height = max_height or (h * max_width) // w
            if asked_width != w or asked_height != h:
                self.image.thumbnail((asked_width, asked_height), Image.LANCZOS)
                if self.image.width != w or self.image.height != h:
                    self.operationsCount += 1
        return self

    def crop_resize(self, max_width, max_height, center_x=0.5, center_y=0.5):
        """Crop and resize the image.

        The image is never resized above the current image size. This method is
        only to create smaller versions of the image.

        Instead of preserving the ratio of the original image like `resize`,
        this method will force the output to take the ratio of the given
        `max_width` and `max_height`, so both have to be defined.

        The crop is done before the resize in order to preserve as much of the
        original image as possible. The goal of this method is primarily to
        resize to a given ratio, and it is not to crop unwanted parts of the
        original image. If the latter is what you want to do, you should create
        another method, or directly use the `crop` method from PIL.

        It is currently not supported for GIF because we do not handle all the
        frames properly.

        :param int max_width: max width
        :param int max_height: max height
        :param float center_x: the center of the crop between 0 (left) and 1
            (right). Defaults to 0.5 (center).
        :param float center_y: the center of the crop between 0 (top) and 1
            (bottom). Defaults to 0.5 (center).
        :return: self to allow chaining
        :rtype: ImageProcess
        """
        if self.image and self.original_format != 'GIF' and max_width and max_height:
            w, h = self.image.size
            # We want to keep as much of the image as possible -> at least one
            # of the 2 crop dimensions always has to be the same value as the
            # original image.
            # The target size will be reached with the final resize.
            if w / max_width > h / max_height:
                new_w, new_h = w, (max_height * w) // max_width
            else:
                new_w, new_h = (max_width * h) // max_height, h

            # No cropping above image size.
            if new_w > w:
                new_w, new_h = w, (new_h * w) // new_w
            if new_h > h:
                new_w, new_h = (new_w * h) // new_h, h

            # Correctly place the center of the crop.
            x_offset = int((w - new_w) * center_x)
            h_offset = int((h - new_h) * center_y)

            if new_w != w or new_h != h:
                self.image = self.image.crop((x_offset, h_offset, x_offset + new_w, h_offset + new_h))
                if self.image.width != w or self.image.height != h:
                    self.operationsCount += 1

        return self.resize(max_width, max_height)

    def colorize(self):
        """Replace the transparent background by a random color.

        :return: self to allow chaining
        :rtype: ImageProcess
        """
        if self.image:
            original = self.image
            color = (randrange(32, 224, 24), randrange(32, 224, 24), randrange(32, 224, 24))
            self.image = Image.new('RGB', original.size)
            self.image.paste(color, box=(0, 0) + original.size)
            self.image.paste(original, mask=original)
            self.operationsCount += 1
        return self


def image_process(source, size=(0, 0), verify_resolution=False, quality=0, crop=None, colorize=False, output_format=''):
    """Process the `source` image by executing the given operations and
    return the result image.
    """
    if not source or ((not size or (not size[0] and not size[1])) and not verify_resolution and not quality and not crop and not colorize and not output_format):
        # for performance: don't do anything if the image is falsy or if
        # no operations have been requested
        return source

    image = ImageProcess(source, verify_resolution)
    if size:
        if crop:
            center_x = 0.5
            center_y = 0.5
            if crop == 'top':
                center_y = 0
            elif crop == 'bottom':
                center_y = 1
            image.crop_resize(max_width=size[0], max_height=size[1], center_x=center_x, center_y=center_y)
        else:
            image.resize(max_width=size[0], max_height=size[1])
    if colorize:
        image.colorize()
    return image.image_quality(quality=quality, output_format=output_format)


# ----------------------------------------
# Misc image tools
# ---------------------------------------

def average_dominant_color(colors, mitigate=175, max_margin=140):
    """This function is used to calculate the dominant colors when given a list of colors

    There are 5 steps:

    1) Select dominant colors (highest count), isolate its values and remove
       it from the current color set.
    2) Set margins according to the prevalence of the dominant color.
    3) Evaluate the colors. Similar colors are grouped in the dominant set
       while others are put in the "remaining" list.
    4) Calculate the average color for the dominant set. This is done by
       averaging each band and joining them into a tuple.
    5) Mitigate final average and convert it to hex

    :param colors: list of tuples having:

        0. color count in the image
        1. actual color: tuple(R, G, B, A)

        -> these can be extracted from a PIL image using
        :meth:`~PIL.Image.Image.getcolors`
    :param mitigate: maximum value a band can reach
    :param max_margin: maximum difference from one of the dominant values
    :returns: a tuple with two items:

        0. the average color of the dominant set as: tuple(R, G, B)
        1. list of remaining colors, used to evaluate subsequent dominant colors
    """
    dominant_color = max(colors)
    dominant_rgb = dominant_color[1][:3]
    dominant_set = [dominant_color]
    remaining = []

    margins = [max_margin * (1 - dominant_color[0] /
                             sum([col[0] for col in colors]))] * 3

    colors.remove(dominant_color)

    for color in colors:
        rgb = color[1]
        if (rgb[0] < dominant_rgb[0] + margins[0] and rgb[0] > dominant_rgb[0] - margins[0] and
            rgb[1] < dominant_rgb[1] + margins[1] and rgb[1] > dominant_rgb[1] - margins[1] and
                rgb[2] < dominant_rgb[2] + margins[2] and rgb[2] > dominant_rgb[2] - margins[2]):
            dominant_set.append(color)
        else:
            remaining.append(color)

    dominant_avg = []
    for band in range(3):
        avg = total = 0
        for color in dominant_set:
            avg += color[0] * color[1][band]
            total += color[0]
        dominant_avg.append(int(avg / total))

    final_dominant = []
    brightest = max(dominant_avg)
    for color in range(3):
        value = dominant_avg[color] / (brightest / mitigate) if brightest > mitigate else dominant_avg[color]
        final_dominant.append(int(value))

    return tuple(final_dominant), remaining


def image_fix_orientation(image):
    """Fix the orientation of the image if it has an EXIF orientation tag.

    This typically happens for images taken from a non-standard orientation
    by some phones or other devices that are able to report orientation.

    The specified transposition is applied to the image before all other
    operations, because all of them expect the image to be in its final
    orientation, which is the case only when the first row of pixels is the top
    of the image and the first column of pixels is the left of the image.

    Moreover the EXIF tags will not be kept when the image is later saved, so
    the transposition has to be done to ensure the final image is correctly
    orientated.

    Note: to be completely correct, the resulting image should have its exif
    orientation tag removed, since the transpositions have been applied.
    However since this tag is not used in the code, it is acceptable to
    save the complexity of removing it.

    :param image: the source image
    :type image: ~PIL.Image.Image
    :return: the resulting image, copy of the source, with orientation fixed
        or the source image if no operation was applied
    :rtype: ~PIL.Image.Image
    """
    getexif = getattr(image, 'getexif', None) or getattr(image, '_getexif', None)  # support PIL < 6.0
    if getexif:
        exif = getexif()
        if exif:
            orientation = exif.get(EXIF_TAG_ORIENTATION, 0)
            for method in EXIF_TAG_ORIENTATION_TO_TRANSPOSE_METHODS.get(orientation, []):
                image = image.transpose(method)
            return image
    return image


def binary_to_image(source):
    try:
        return Image.open(io.BytesIO(source))
    except (OSError, binascii.Error):
        raise UserError(_("This file could not be decoded as an image file."))

def base64_to_image(base64_source):
    """Return a PIL image from the given `base64_source`.

    :param base64_source: the image base64 encoded
    :type base64_source: string or bytes
    :rtype: ~PIL.Image.Image
    :raise: UserError if the base64 is incorrect or the image can't be identified by PIL
    """
    try:
        return Image.open(io.BytesIO(base64.b64decode(base64_source)))
    except (OSError, binascii.Error):
        raise UserError(_("This file could not be decoded as an image file."))


def image_apply_opt(image, output_format, **params):
    """Return the given PIL `image` using `params`.

    :type image: ~PIL.Image.Image
    :param str output_format: :meth:`~PIL.Image.Image.save`'s ``format`` parameter
    :param dict params: params to expand when calling :meth:`~PIL.Image.Image.save`
    :return: the image formatted
    :rtype: bytes
    """
    stream = io.BytesIO()
    image.save(stream, format=output_format, **params)
    return stream.getvalue()


def image_to_base64(image, output_format, **params):
    """Return a base64_image from the given PIL `image` using `params`.

    :type image: ~PIL.Image.Image
    :param str output_format:
    :param dict params: params to expand when calling :meth:`~PIL.Image.Image.save`
    :return: the image base64 encoded
    :rtype: bytes
    """
    stream = image_apply_opt(image, output_format, **params)
    return base64.b64encode(stream)


def is_image_size_above(base64_source_1, base64_source_2):
    """Return whether or not the size of the given image `base64_source_1` is
    above the size of the given image `base64_source_2`.
    """
    if not base64_source_1 or not base64_source_2:
        return False
    if base64_source_1[:1] in (b'P', 'P') or base64_source_2[:1] in (b'P', 'P'):
        # False for SVG
        return False
    source_1 = base64.b64decode(base64_source_1)
    source_2 = base64.b64decode(base64_source_2)
    if (source_1[0:4] == b'RIFF' and source_1[8:15] == b'WEBPVP8') or (source_2[0:4] == b'RIFF' and source_2[8:15] == b'WEBPVP8'):
        # False for WEBP
        return False
    image_source = image_fix_orientation(binary_to_image(source_1))
    image_target = image_fix_orientation(binary_to_image(source_2))
    return image_source.width > image_target.width or image_source.height > image_target.height


def image_guess_size_from_field_name(field_name):
    """Attempt to guess the image size based on `field_name`.

    If it can't be guessed, return (0, 0) instead.

    :param str field_name: the name of a field
    :return: the guessed size
    :rtype: tuple (width, height)
    """
    suffix = '1024' if field_name == 'image' else field_name.split('_')[-1]
    try:
        return (int(suffix), int(suffix))
    except ValueError:
        return (0, 0)


def image_data_uri(base64_source, report_type):
    """This returns data URL scheme according RFC 2397
    (https://tools.ietf.org/html/rfc2397) for all kind of supported images
    (PNG, GIF, JPG and SVG), defaulting on PNG type if not mimetype detected.
    """
    mimetype = FILETYPE_BASE64_MAGICWORD.get(base64_source[:1], 'png'),
    data_uri = 'data:image/%s;base64,%s' % (
        FILETYPE_BASE64_MAGICWORD.get(base64_source[:1], 'png'),
        base64_source.decode(),
    )
    if 'webp' in mimetype and report_type == 'pdf':
        # Convert image so that is recognized by wkhtmltopdf.
        response = Future()
        browser = ChromeBrowser(None, '1366x768', 'Render WebP', response)
        try:
            converter = '''<html><body><img src='%s'/><script>
const img = document.querySelector('img');
document.body.onload = () => {
const canvas = document.createElement('canvas');
canvas.width = img.width;
canvas.height = img.height;
document.body.appendChild(canvas);
canvas.getContext('2d').drawImage(img, 0, 0);
console.log(canvas.toDataURL('image/png'));
};
</script></body></html>''' % data_uri
            data_uri = None
            browser.navigate_to('data:text/html;base64,%s' % base64.b64encode(converter.encode()).decode())
        finally:
            data_uri = response.result(timeout=5)
            browser.stop()
    return data_uri


def get_saturation(rgb):
    """Returns the saturation (hsl format) of a given rgb color

    :param rgb: rgb tuple or list
    :return: saturation
    """
    c_max = max(rgb) / 255
    c_min = min(rgb) / 255
    d = c_max - c_min
    return 0 if d == 0 else d / (1 - abs(c_max + c_min - 1))


def get_lightness(rgb):
    """Returns the lightness (hsl format) of a given rgb color

    :param rgb: rgb tuple or list
    :return: lightness
    """
    return (max(rgb) + min(rgb)) / 2 / 255


def hex_to_rgb(hx):
    """Converts an hexadecimal string (starting with '#') to a RGB tuple"""
    return tuple([int(hx[i:i+2], 16) for i in range(1, 6, 2)])


def rgb_to_hex(rgb):
    """Converts a RGB tuple or list to an hexadecimal string"""
    return '#' + ''.join([(hex(c).split('x')[-1].zfill(2)) for c in rgb])

# TODO WIP - Factorize browser with odoo.tests.common if it makes sense.
from concurrent.futures import Future, CancelledError, wait
import itertools
import json
import logging
import os
import pathlib
import platform
import re
import requests
import signal
import shutil
import subprocess
import tempfile
import threading
import time
import werkzeug.urls
try:
    import websocket
except ImportError:
    # WebP pre-PDF conversion will be skipped
    websocket = None
import odoo
from odoo.tools.misc import find_in_path

HOST = '127.0.0.1'
CHECK_BROWSER_SLEEP = 0.1 # seconds
CHECK_BROWSER_ITERATIONS = 100
BROWSER_WAIT = CHECK_BROWSER_SLEEP * CHECK_BROWSER_ITERATIONS # seconds
_logger = logging.getLogger(__name__)

def get_db_name():
    db = odoo.tools.config['db_name']
    # If the database name is not provided on the command-line,
    # use the one on the thread (which means if it is provided on
    # the command-line, this will break when installing another
    # database from XML-RPC).
    if not db and hasattr(threading.current_thread(), 'dbname'):
        return threading.current_thread().dbname
    return db

class ChromeBrowserException(Exception):
    pass


class ChromeBrowser:
    """ Helper object to control a Chrome headless process. """
    remote_debugging_port = 0  # 9222, change it in a non-git-tracked file

    def __init__(self, logger, window_size, test_class, response):
        self._logger = _logger
        self.test_class = test_class
        if websocket is None:
            self._logger.warning("websocket-client module is not installed")
            raise ChromeBrowserException("websocket-client module is not installed")
        self.devtools_port = None
        self.ws_url = ''  # WebSocketUrl
        self.ws = None  # websocket
        self.user_data_dir = tempfile.mkdtemp(suffix='_chrome_odoo')
        self.chrome_pid = None
        self.response = response

        # otc = odoo.tools.config
        # self.screenshots_dir = os.path.join(otc['screenshots'], get_db_name(), 'screenshots')
        # self.screencasts_dir = None
        # self.screencasts_frames_dir = None
        # if otc['screencasts']:
        #     self.screencasts_dir = os.path.join(otc['screencasts'], get_db_name(), 'screencasts')
        #     self.screencasts_frames_dir = os.path.join(self.screencasts_dir, 'frames')
        #     os.makedirs(self.screencasts_frames_dir, exist_ok=True)
        # self.screencast_frames = []
        # os.makedirs(self.screenshots_dir, exist_ok=True)

        self.window_size = window_size
        self.sigxcpu_handler = None
        self._chrome_start()
        self._find_websocket()
        self._logger.info('Websocket url found: %s', self.ws_url)
        self._open_websocket()
        self._request_id = itertools.count()
        self._result = Future()
        # maps request_id to Futures
        self._responses = {}
        # maps frame ids to callbacks
        self._frames = {}
        self._handlers = {
            'Runtime.consoleAPICalled': self._handle_console,
            'Runtime.exceptionThrown': self._handle_exception,
            'Page.frameStoppedLoading': self._handle_frame_stopped_loading,
            'Page.screencastFrame': self._handle_screencast_frame,
        }
        self._receiver = threading.Thread(
            target=self._receive,
            name="WebSocket events consumer",
            args=(get_db_name(),)
        )
        self._receiver.start()
        self._logger.info('Enable chrome headless console log notification')
        self._websocket_send('Runtime.enable')
        self._logger.info('Chrome headless enable page notifications')
        self._websocket_send('Page.enable')
        # if os.name == 'posix':
        #     self.sigxcpu_handler = signal.getsignal(signal.SIGXCPU)
        #     signal.signal(signal.SIGXCPU, self.signal_handler)

    def signal_handler(self, sig, frame):
        if sig == signal.SIGXCPU:
            _logger.info('CPU time limit reached, stopping Chrome and shutting down')
            self.stop()
            os._exit(0)

    def stop(self):
        if self.chrome_pid is not None:
            self._logger.info("Closing chrome headless with pid %s", self.chrome_pid)
            self._websocket_send('Browser.close')
            self._logger.info("Closing websocket connection")
            self.ws.close()
            self._logger.info("Terminating chrome headless with pid %s", self.chrome_pid)
            os.kill(self.chrome_pid, signal.SIGTERM)
        if self.user_data_dir and os.path.isdir(self.user_data_dir) and self.user_data_dir != '/':
            self._logger.info('Removing chrome user profile "%s"', self.user_data_dir)
            shutil.rmtree(self.user_data_dir, ignore_errors=True)
        # Restore previous signal handler
        # if self.sigxcpu_handler and os.name == 'posix':
        #     signal.signal(signal.SIGXCPU, self.sigxcpu_handler)

    @property
    def executable(self):
        system = platform.system()
        if system == 'Linux':
            for bin_ in ['google-chrome', 'chromium', 'chromium-browser']:
                try:
                    return find_in_path(bin_)
                except IOError:
                    continue

        elif system == 'Darwin':
            bins = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '/Applications/Chromium.app/Contents/MacOS/Chromium',
            ]
            for bin_ in bins:
                if os.path.exists(bin_):
                    return bin_

        elif system == 'Windows':
            bins = [
                '%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe',
                '%ProgramFiles(x86)%\\Google\\Chrome\\Application\\chrome.exe',
                '%LocalAppData%\\Google\\Chrome\\Application\\chrome.exe',
            ]
            for bin_ in bins:
                bin_ = os.path.expandvars(bin_)
                if os.path.exists(bin_):
                    return bin_

        self._logger.warning("Chrome executable not found")
        raise unittest.SkipTest("Chrome executable not found")

    def _spawn_chrome(self, cmd):
        if os.name == 'posix' and platform.system() != 'Darwin':
            # since the introduction of pointer compression in Chrome 80 (v8 v8.0),
            # the memory reservation algorithm requires more than 8GiB of
            # virtual mem for alignment this exceeds our default memory limits.
            def preexec():
                import resource
                resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        else:
            preexec = None

        # pylint: disable=subprocess-popen-preexec-fn
        proc = subprocess.Popen(cmd, stderr=subprocess.DEVNULL, preexec_fn=preexec)
        port_file = pathlib.Path(self.user_data_dir, 'DevToolsActivePort')
        for _ in range(CHECK_BROWSER_ITERATIONS):
            time.sleep(CHECK_BROWSER_SLEEP)
            if port_file.is_file() and port_file.stat().st_size > 5:
                with port_file.open('r', encoding='utf-8') as f:
                    self.devtools_port = int(f.readline())
                    return proc.pid
        raise unittest.SkipTest(f'Failed to detect chrome devtools port after {BROWSER_WAIT :.1f}s.')

    def _chrome_start(self):
        if self.chrome_pid is not None:
            return

        switches = {
            '--headless': '',
            '--no-default-browser-check': '',
            '--no-first-run': '',
            '--disable-extensions': '',
            '--disable-background-networking' : '',
            '--disable-background-timer-throttling' : '',
            '--disable-backgrounding-occluded-windows': '',
            '--disable-renderer-backgrounding' : '',
            '--disable-breakpad': '',
            '--disable-client-side-phishing-detection': '',
            '--disable-crash-reporter': '',
            '--disable-default-apps': '',
            '--disable-dev-shm-usage': '',
            '--disable-device-discovery-notifications': '',
            '--disable-namespace-sandbox': '',
            '--user-data-dir': self.user_data_dir,
            '--disable-translate': '',
            # required for tours that use Youtube autoplay conditions (namely website_slides' "course_tour")
            '--autoplay-policy': 'no-user-gesture-required',
            '--window-size': self.window_size,
            '--remote-debugging-address': HOST,
            '--remote-debugging-port': str(self.remote_debugging_port),
            '--no-sandbox': '',
            '--disable-gpu': '',
            # required for tests that depends on the jquery.touchSwipe library, which detects
            # touch capabilities using "'ontouchstart' in window"
            '--touch-events':'',
        }

        cmd = [self.executable]
        cmd += ['%s=%s' % (k, v) if v else k for k, v in switches.items()]
        url = 'about:blank'
        cmd.append(url)
        try:
            self.chrome_pid = self._spawn_chrome(cmd)
        except OSError:
            raise unittest.SkipTest("%s not found" % cmd[0])
        self._logger.info('Chrome pid: %s', self.chrome_pid)

    def _find_websocket(self):
        version = self._json_command('version')
        self._logger.info('Browser version: %s', version['Browser'])
        infos = self._json_command('', get_key=0)  # Infos about the first tab
        self.ws_url = infos['webSocketDebuggerUrl']
        self._logger.info('Chrome headless temporary user profile dir: %s', self.user_data_dir)

    def _json_command(self, command, timeout=3, get_key=None):
        """Queries browser state using JSON

        Available commands:

        ``''``
            return list of tabs with their id
        ``list`` (or ``json/``)
            list tabs
        ``new``
            open a new tab
        :samp:`activate/{id}`
            activate a tab
        :samp:`close/{id}`
            close a tab
        ``version``
            get chrome and dev tools version
        ``protocol``
            get the full protocol
        """
        command = '/'.join(['json', command]).strip('/')
        url = werkzeug.urls.url_join('http://%s:%s/' % (HOST, self.devtools_port), command)
        self._logger.info("Issuing json command %s", url)
        delay = 0.1
        tries = 0
        failure_info = None
        while timeout > 0:
            try:
                os.kill(self.chrome_pid, 0)
            except ProcessLookupError:
                message = 'Chrome crashed at startup'
                break
            try:
                r = requests.get(url, timeout=3)
                if r.ok:
                    res = r.json()
                    if get_key is None:
                        return res
                    else:
                        return res[get_key]
            except requests.ConnectionError as e:
                failure_info = str(e)
                message = 'Connection Error while trying to connect to Chrome debugger'
            except requests.exceptions.ReadTimeout as e:
                failure_info = str(e)
                message = 'Connection Timeout while trying to connect to Chrome debugger'
                break
            except (KeyError, IndexError):
                message = 'Key "%s" not found in json result "%s" after connecting to Chrome debugger' % (get_key, res)
            time.sleep(delay)
            timeout -= delay
            delay = delay * 1.5
            tries += 1
        self._logger.error("%s after %s tries" % (message, tries))
        if failure_info:
            self._logger.info(failure_info)
        self.stop()
        raise unittest.SkipTest("Error during Chrome headless connection")

    def _open_websocket(self):
        self.ws = websocket.create_connection(self.ws_url, enable_multithread=True)
        if self.ws.getstatus() != 101:
            raise unittest.SkipTest("Cannot connect to chrome dev tools")
        self.ws.settimeout(0.01)

    def _receive(self, dbname):
        threading.current_thread().dbname = dbname
        # So CDT uses a streamed JSON-RPC structure, meaning a request is
        # {id, method, params} and eventually a {id, result | error} should
        # arrive the other way, however for events it uses "notifications"
        # meaning request objects without an ``id``, but *coming from the server
        while True: # or maybe until `self._result` is `done()`?
            try:
                msg = self.ws.recv()
                self._logger.debug('\n<- %s', msg)
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                # if the socket is still connected something bad happened,
                # otherwise the client was just shut down
                self._result.cancel()
                if self.ws.connected:
                    raise
                return

            res = json.loads(msg)
            request_id = res.get('id')
            try:
                if request_id is None:
                    handler = self._handlers.get(res['method'])
                    if handler:
                        handler(**res['params'])
                else:
                    f = self._responses.pop(request_id, None)
                    if f:
                        if 'result' in res:
                            f.set_result(res['result'])
                        else:
                            f.set_exception(ChromeBrowserException(res['error']['message']))
            except Exception:
                _logger.exception("While processing message %s", msg)

    def _websocket_request(self, method, *, params=None, timeout=10.0):
        assert threading.get_ident() != self._receiver.ident,\
            "_websocket_request must not be called from the consumer thread"
        if self.ws is None:
            return

        f = self._websocket_send(method, params=params, with_future=True)
        try:
            return f.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f'{method}({params or ""})')

    def _websocket_send(self, method, *, params=None, with_future=False):
        """send chrome devtools protocol commands through websocket

        If ``with_future`` is set, returns a ``Future`` for the operation.
        """
        if self.ws is None:
            return

        result = None
        request_id = next(self._request_id)
        if with_future:
            result = self._responses[request_id] = Future()
        payload = {'method': method, 'id': request_id}
        if params:
            payload['params'] = params
        self._logger.debug('\n-> %s', payload)
        self.ws.send(json.dumps(payload))
        return result

    def _handle_console(self, type, args=None, stackTrace=None, **kw): # pylint: disable=redefined-builtin
        # console formatting differs somewhat from Python's, if args[0] has
        # format modifiers that many of args[1:] get formatted in, missing
        # args are replaced by empty strings and extra args are concatenated
        # (space-separated)
        #
        # current version modifies the args in place which could and should
        # probably be improved
        if args:
            arg0, args = str(self._from_remoteobject(args[0])), args[1:]
        else:
            arg0, args = '', []
        formatted = [re.sub(r'%[%sdfoOc]', self.console_formatter(args), arg0)]
        # formatter consumes args it uses, leaves unformatted args untouched
        formatted.extend(str(self._from_remoteobject(arg)) for arg in args)
        message = ' '.join(formatted)
        stack = ''.join(self._format_stack({'type': type, 'stackTrace': stackTrace}))
        if stack:
            message += '\n' + stack

        log_type = type
        self._logger.getChild('browser').log(
            self._TO_LEVEL.get(log_type, logging.INFO),
            "%s", message[0:100] # might still have %<x> characters
        )
        if self.response:
            self.response.set_result(message)

        if log_type == 'error':
            self.take_screenshot()
            self._save_screencast()
            try:
                self._result.set_exception(ChromeBrowserException(message))
            except CancelledError:
                ...
            except InvalidStateError:
                self._logger.warning(
                    "Trying to set result to failed (%s) but found the future settled (%s)",
                    message, self._result
                )
        elif 'test successful' in message:
            self._result.set_result(True)

    def _handle_exception(self, exceptionDetails, timestamp):
        message = exceptionDetails['text']
        exception = exceptionDetails.get('exception')
        if exception:
            message += str(self._from_remoteobject(exception))
        exceptionDetails['type'] = 'trace'  # fake this so _format_stack works
        stack = ''.join(self._format_stack(exceptionDetails))
        if stack:
            message += '\n' + stack

        self.take_screenshot()
        self._save_screencast()
        try:
            self._result.set_exception(ChromeBrowserException(message))
        except CancelledError:
            ...
        except InvalidStateError:
            self._logger.warning(
                "Trying to set result to failed (%s) but found the future settled (%s)",
                message, self._result
            )

    def _handle_frame_stopped_loading(self, frameId):
        wait = self._frames.pop(frameId, None)
        if wait:
            wait()

    def _handle_screencast_frame(self, sessionId, data, metadata):
        self._websocket_send('Page.screencastFrameAck', params={'sessionId': sessionId})
        outfile = os.path.join(self.screencasts_frames_dir, 'frame_%05d.b64' % len(self.screencast_frames))
        with open(outfile, 'w') as f:
            f.write(data)
            self.screencast_frames.append({
                'file_path': outfile,
                'timestamp': metadata.get('timestamp')
            })

    _TO_LEVEL = {
        'debug': logging.DEBUG,
        'log': logging.INFO,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        # TODO: what do with
        # dir, dirxml, table, trace, clear, startGroup, startGroupCollapsed,
        # endGroup, assert, profile, profileEnd, count, timeEnd
    }

    # def take_screenshot(self, prefix='sc_', suffix=None):
    #     def handler(f):
    #         base_png = f.result(timeout=0)['data']
    #         if not base_png:
    #             self._logger.warning("Couldn't capture screenshot: expected image data, got ?? error ??")
    #             return
    #
    #         decoded = base64.b64decode(base_png, validate=True)
    #         fname = '{}{:%Y%m%d_%H%M%S_%f}{}.png'.format(
    #             prefix, datetime.now(),
    #             suffix or '_%s' % self.test_class)
    #         full_path = os.path.join(self.screenshots_dir, fname)
    #         with open(full_path, 'wb') as f:
    #             f.write(decoded)
    #         self._logger.runbot('Screenshot in: %s', full_path)
    #
    #     self._logger.info('Asking for screenshot')
    #     f = self._websocket_send('Page.captureScreenshot', with_future=True)
    #     f.add_done_callback(handler)
    #     return f
    #
    # def _save_screencast(self, prefix='failed'):
    #     # could be encododed with something like that
    #     #  ffmpeg -framerate 3 -i frame_%05d.png  output.mp4
    #     if not self.screencast_frames:
    #         self._logger.debug('No screencast frames to encode')
    #         return None
    #
    #     for f in self.screencast_frames:
    #         with open(f['file_path'], 'rb') as b64_file:
    #             frame = base64.decodebytes(b64_file.read())
    #         os.unlink(f['file_path'])
    #         f['file_path'] = f['file_path'].replace('.b64', '.png')
    #         with open(f['file_path'], 'wb') as png_file:
    #             png_file.write(frame)
    #
    #     timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    #     fname = '%s_screencast_%s.mp4' % (prefix, timestamp)
    #     outfile = os.path.join(self.screencasts_dir, fname)
    #
    #     try:
    #         ffmpeg_path = find_in_path('ffmpeg')
    #     except IOError:
    #         ffmpeg_path = None
    #
    #     if ffmpeg_path:
    #         nb_frames = len(self.screencast_frames)
    #         concat_script_path = os.path.join(self.screencasts_dir, fname.replace('.mp4', '.txt'))
    #         with open(concat_script_path, 'w') as concat_file:
    #             for i in range(nb_frames):
    #                 frame_file_path = os.path.join(self.screencasts_frames_dir, self.screencast_frames[i]['file_path'])
    #                 end_time = time.time() if i == nb_frames - 1 else self.screencast_frames[i+1]['timestamp']
    #                 duration = end_time - self.screencast_frames[i]['timestamp']
    #                 concat_file.write("file '%s'\nduration %s\n" % (frame_file_path, duration))
    #             concat_file.write("file '%s'" % frame_file_path)  # needed by the concat plugin
    #         r = subprocess.run([ffmpeg_path, '-intra', '-f', 'concat','-safe', '0', '-i', concat_script_path, '-pix_fmt', 'yuv420p', outfile])
    #         self._logger.log(25, 'Screencast in: %s', outfile)
    #     else:
    #         outfile = outfile.strip('.mp4')
    #         shutil.move(self.screencasts_frames_dir, outfile)
    #         self._logger.runbot('Screencast frames in: %s', outfile)
    #
    # def start_screencast(self):
    #     assert self.screencasts_dir
    #     self._websocket_send('Page.startScreencast')

    def set_cookie(self, name, value, path, domain):
        params = {'name': name, 'value': value, 'path': path, 'domain': domain}
        self._websocket_request('Network.setCookie', params=params)
        return

    def delete_cookie(self, name, **kwargs):
        params = {k: v for k, v in kwargs.items() if k in ['url', 'domain', 'path']}
        params['name'] = name
        self._websocket_request('Network.deleteCookies', params=params)
        return

    def _wait_ready(self, ready_code, timeout=60):
        self._logger.info('Evaluate ready code "%s"', ready_code)
        start_time = time.time()
        result = None
        while True:
            taken = time.time() - start_time
            if taken > timeout:
                break

            result = self._websocket_request('Runtime.evaluate', params={
                'expression': ready_code,
                'awaitPromise': True,
            }, timeout=timeout-taken)['result']

            if result == {'type': 'boolean', 'value': True}:
                time_to_ready = time.time() - start_time
                if taken > 2:
                    self._logger.info('The ready code tooks too much time : %s', time_to_ready)
                return True

        self.take_screenshot(prefix='sc_failed_ready_')
        self._logger.info('Ready code last try result: %s', result)
        return False

    def _wait_code_ok(self, code, timeout):
        self._logger.info('Evaluate test code "%s"', code)
        start = time.time()
        res = self._websocket_request('Runtime.evaluate', params={
            'expression': code,
            'awaitPromise': True,
        }, timeout=timeout)['result']
        if res.get('subtype') == 'error':
            raise ChromeBrowserException("Running code returned an error: %s" % res)
        # if the runcode was a promise which took some time to execute, discount
        # that from the timeout
        if self._result.result(time.time() - start + timeout):
            return

        self.take_screenshot()
        self._save_screencast()
        raise ChromeBrowserException('Script timeout exceeded')


    def navigate_to(self, url, wait_stop=False):
        self._logger.info('Navigating to: "%s"', url[0:20])
        # self._logger.info('Navigating to: "%s"', url)
        nav_result = self._websocket_request('Page.navigate', params={'url': url})
        self._logger.info("Navigation result: %s", nav_result)
        if wait_stop:
            frame_id = nav_result['frameId']
            e = threading.Event()
            self._frames[frame_id] = e.set
            self._logger.info('Waiting for frame %r to stop loading', frame_id)
            e.wait(10)

    def clear(self):
        self._websocket_send('Page.stopScreencast')
        if self.screencasts_dir and os.path.isdir(self.screencasts_frames_dir):
            shutil.rmtree(self.screencasts_frames_dir)
        self.screencast_frames = []
        self._websocket_request('Page.stopLoading')
        self._websocket_request('Runtime.evaluate', params={'expression': """
        ('serviceWorker' in navigator) &&
            navigator.serviceWorker.getRegistrations().then(
                registrations => Promise.all(registrations.map(r => r.unregister()))
            )
        """, 'awaitPromise': True})
        # wait for the screenshot or whatever
        wait(self._responses.values())
        self._logger.info('Deleting cookies and clearing local storage')
        self._websocket_request('Network.clearBrowserCache')
        self._websocket_request('Network.clearBrowserCookies')
        self._websocket_request('Runtime.evaluate', params={'expression': 'try {localStorage.clear();} catch(e) {}'})
        self.navigate_to('about:blank', wait_stop=True)
        # hopefully after navigating to about:blank there's no event left
        self._frames.clear()
        # wait for the clearing requests to finish in case the browser is re-used
        wait(self._responses.values())
        self._responses.clear()
        self._result.cancel()
        self._result = Future()

    def _from_remoteobject(self, arg):
        """ attempts to make a CDT RemoteObject comprehensible
        """
        objtype = arg['type']
        subtype = arg.get('subtype')
        if objtype == 'undefined':
            # the undefined remoteobject is literally just {type: undefined}...
            return 'undefined'
        elif objtype != 'object' or subtype not in (None, 'array'):
            # value is the json representation for json object
            # otherwise fallback on the description which is "a string
            # representation of the object" e.g. the traceback for errors, the
            # source for functions, ... finally fallback on the entire arg mess
            return arg.get('value', arg.get('description', arg))
        elif subtype == 'array':
            # apparently value is *not* the JSON representation for arrays
            # instead it's just Array(3) which is useless, however the preview
            # properties are the same as object which is useful (just ignore the
            # name which is the index)
            return '[%s]' % ', '.join(
                repr(p['value']) if p['type'] == 'string' else str(p['value'])
                for p in arg.get('preview', {}).get('properties', [])
                if re.match(r'\d+', p['name'])
            )
        # all that's left is type=object, subtype=None aka custom or
        # non-standard objects, print as TypeName(param=val, ...), sadly because
        # of the way Odoo widgets are created they all appear as Class(...)
        # nb: preview properties are *not* recursive, the value is *all* we get
        return '%s(%s)' % (
            arg.get('className') or 'object',
            ', '.join(
                '%s=%s' % (p['name'], repr(p['value']) if p['type'] == 'string' else p['value'])
                for p in arg.get('preview', {}).get('properties', [])
                if p.get('value') is not None
            )
        )

    LINE_PATTERN = '\tat %(functionName)s (%(url)s:%(lineNumber)d:%(columnNumber)d)\n'
    def _format_stack(self, logrecord):
        if logrecord['type'] not in ['trace']:
            return

        trace = logrecord.get('stackTrace')
        while trace:
            for f in trace['callFrames']:
                yield self.LINE_PATTERN % f
            trace = trace.get('parent')

    def console_formatter(self, args):
        """ Formats similarly to the console API:

        * if there are no args, don't format (return string as-is)
        * %% -> %
        * %c -> replace by styling directives (ignore for us)
        * other known formatters -> replace by corresponding argument
        * leftover known formatters (args exhausted) -> replace by empty string
        * unknown formatters -> return as-is
        """
        if not args:
            return lambda m: m[0]

        def replacer(m):
            fmt = m[0][1]
            if fmt == '%':
                return '%'
            if fmt in 'sdfoOc':
                if not args:
                    return ''
                repl = args.pop(0)
                if fmt == 'c':
                    return ''
                return str(self._from_remoteobject(repl))
            return m[0]
        return replacer
