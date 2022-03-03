# -*- coding: utf-8 -*-
import base64
import io
import logging
import PyPDF2


_logger = logging.getLogger(__name__)

global _wand_lib_warning
_wand_lib_warning = False

global _wand_lib_imported
_wand_lib_imported = False

global _wand_lib_security_warning
_wand_lib_security_warning = False

try:
    from wand.image import Image
    from wand.exceptions import PolicyError
    _wand_lib_imported = True

except ImportError:

    if not _wand_lib_warning:
        _logger.warning(
            "The `wand` Python module is not installed, some pdf preview will be missing "
            "Try: sudo apt-get install python3-wand."
        )
        _phonenumbers_lib_warning = True


def render_first_page_of_pdf_base64_to_jpeg_base64(pdf_binary_base64, resolution_dpi=300):
    """ Render the first page of the provided pdf (in base 64) as an image (jpeg in base 64).

        :param pdf_binary_base64: pdf in binary base 64 encoded form
        :param resolution_dpi: rendering resolution in dpi

        :return: image rendered in binary base 64 encoded form or None if an error has occurred (library missing, ...)
    """
    if not _wand_lib_imported:
        return None
    try:
        pdf = PyPDF2.PdfFileReader(io.BytesIO(base64.b64decode(pdf_binary_base64)))
        tmp_pdf = PyPDF2.PdfFileWriter()
        tmp_pdf.addPage(pdf.getPage(0))

        tmp_pdf_bytes = io.BytesIO()
        tmp_pdf.write(tmp_pdf_bytes)
        tmp_pdf_bytes.seek(0)

        img = Image(file=tmp_pdf_bytes, resolution=resolution_dpi)
        return base64.b64encode(img.make_blob('jpeg'))
    except PolicyError as e:
        global _wand_lib_security_warning
        if not _wand_lib_security_warning:
            _logger.warning(str(e))
            _wand_lib_security_warning = True
        return None
    except Exception:
        return None
