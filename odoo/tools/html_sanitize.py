# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import markupsafe
import re
import string


from bleach.html5lib_shim import (
    BleachHTMLParser,
    BleachHTMLSerializer,
    getTreeWalker,
)
from bleach.sanitizer import BleachSanitizerFilter


_logger = logging.getLogger(__name__)

safe_attrs = {
    'abbr', 'accept', 'accept-charset', 'accesskey', 'action', 'align', 'alt', 'axis',
    'backdropxmlns', 'bgcolor', 'border', 'cellpadding', 'cellspacing', 'char', 'charoff',
    'charset', 'checked', 'cite', 'class', 'clear', 'color', 'cols', 'colspan', 'compact',
    'content', 'contentxmlns', 'coords', 'data-class', 'data-file-name', 'data-gl-filter',
    'data-id', 'data-interval', 'data-member_id', 'data-mimetype', 'data-o-mail-quote',
    'data-o-mail-quote-container', 'data-o-mail-quote-node', 'data-oe-expression',
    'data-oe-field', 'data-oe-id', 'data-oe-model', 'data-oe-nodeid',
    'data-oe-translation-id', 'data-oe-type', 'data-original-id', 'data-original-mimetype',
    'data-original-src', 'data-publish', 'data-quality', 'data-res_id',
    'data-resize-width', 'data-scroll-background-ratio', 'data-shape', 'data-shape-colors',
    'data-view-id', 'datetime', 'dir', 'disabled', 'enctype', 'equiv', 'face', 'for',
    'headers', 'height', 'hidden', 'href', 'hreflang', 'hspace', 'http-equiv', 'id',
    'ismap', 'itemprop', 'itemscope', 'itemtype', 'label', 'lang', 'loading', 'longdesc',
    'maxlength', 'media', 'method', 'multiple', 'name', 'nohref', 'noshade', 'nowrap',
    'prompt', 'readonly', 'rel', 'res_id', 'res_model', 'rev', 'role', 'rows', 'rowspan',
    'rules', 'scope', 'selected', 'shape', 'size', 'span', 'src', 'start', 'style',
    'summary', 'tabindex', 'target', 'text', 'title', 'token', 'type', 'usemap', 'valign',
    'value', 'version', 'vspace', 'widget', 'width', 'xml:lang', 'xmlns'
}

# Extend the whitelist when sanitize_attributes is set to False
# All data-XXX attributes are already allowed, see check_attribute
extended_safe_attrs = {
    'aria-expanded',
    'loading',
    'style',
}

safe_tags = {
    '?', 'a', 'abbr', 'acronym', 'address', 'applet', 'area', 'article', 'aside',
    'audio', 'b', 'basefont', 'bdi', 'bdo', 'big', 'blink', 'blockquote', 'bodyb',
    'br', 'button', 'c', 'canvas', 'caption', 'center', 'cite', 'code', 'col',
    'colgroup', 'command', 'd', 'datalist', 'dd', 'del', 'details', 'dfn', 'dir',
    'div', 'dl', 'dt', 'e', 'em', 'f', 'fieldset', 'figcaption', 'figure', 'font',
    'footer', 'form', 'frameset', 'h', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header',
    'hgroup', 'hr', 'html', 'i', 'img', 'input', 'ins', 'isindex', 'kbd', 'keygen',
    'l', 'label', 'legend', 'li', 'm', 'main', 'map', 'mark', 'marquee', 'math',
    'menu', 'meter', 'n', 'nav', 'o', 'ol', 'optgroup', 'option', 'output', 'p',
    'param', 'pre', 'progress', 'q', 'role', 'rp', 'rt', 'ruby', 's', 'samp', 'section',
    'select', 'small', 'source', 'span', 'strike', 'strong', 'sub', 'summary', 'sup',
    'svg', 't', 'table', 'tbody', 'td', 'textarea', 'tfoot', 'th', 'thead', 'time',
    'tr', 'track', 'tt', 'u', 'ul', 'var', 'video', 'wbr',
}


# Those tags are remove and their children as well
# If sanitize_tags is False, this blacklist is ignored
kill_tags = {
    'base', 'embed', 'frame', 'head', 'iframe', 'link', 'meta',
    'noscript', 'object', 'script', 'style', 'title',
}

# Those tag are remove even if sanitize_tags is False
clean_tags = {
    'meta',
}

style_whitelist = {
    'background-color', 'color', 'display', 'float', 'font-family', 'font-size',
    'font-weight', 'letter-spacing', 'line-height', 'margin', 'margin-bottom',
    'margin-left', 'margin-right', 'margin-top', 'opacity', 'padding', 'padding-bottom',
    'padding-left', 'padding-right', 'padding-top', 'text-align', 'text-decoration',
    'text-transform', 'vertical-align', 'white-space'
    # box model
    'border', 'border-bottom', 'border-color', 'border-radius', 'border-style',
    'border-top', 'border-width', 'height', 'max-width', 'min-height', 'min-width',
    'width',
    # tables
    'border-collapse', 'border-spacing', 'caption-side',
    'empty-cells', 'table-layout',
    # border style
    *{
        f'border-{position}-{attribute}'
        for position in ('top', 'bottom', 'left', 'right')
        for attribute in ('style', 'color', 'width', 'left-radius', 'right-radius')
    },
}


KILLED_TAG_NAME = '__<killed>__'
re_tag_start = rf'<\s*{KILLED_TAG_NAME}[^>]*>'
re_tag_end = rf'<\/\s*{KILLED_TAG_NAME}\s*>'

re_killed_tag = re.compile(re_tag_start + '.*?' + re_tag_end,)
re_killed_empty = re.compile(re_tag_start)

ATTRIBUTE_SUBSET = string.ascii_letters + string.digits + "-_"


class OdooCleaner(BleachSanitizerFilter):
    """HTML cleaner, allow us to have more control on the bleach sanitizer.

    We do not use the standard bleach Cleaner, because we are limited in the
    customization we can make. E.G. the "data:" protocol is blocked for a good reason.
    But it can be useful to embed image "data:image/png;base64,". With the standard
    cleaner, there's no way to check the entire value (we can only allow the entire
    protocol "data:" or block it).

    We also need to strip some elements all their children. E.G. if we remove a
    <style/> tags, we don't want to keep the CSS code in the HTML source.
    """

    def __init__(self, **kwargs):
        self.sanitize_tags = kwargs.pop('sanitize_tags', True)
        self.sanitize_form = kwargs.pop('sanitize_form', True)
        self.sanitize_style = kwargs.pop('sanitize_style', False)
        super().__init__(**kwargs)

    def sanitize_token(self, token):
        tag_name = token.get('name', '').lower().strip()
        tag_type = token['type']

        if self.sanitize_form and tag_name == 'form':
            # Ignore sanitize_tags, always remove it
            return self._kill_token(token)

        if not self.sanitize_tags:
            if (
                tag_type in ('StartTag', 'EmptyTag', 'EndTag')
                and tag_name not in clean_tags
            ):
                return self.allow_token(token)
            elif tag_type == 'Characters':
                return self.sanitize_characters(token)
            elif tag_type == 'SpaceCharacters':
                return token

            return

        if tag_name in kill_tags:
            # We will strip manually those token because
            # bleach will keep the child elements
            return self._kill_token(token)

        # Sanitize attributes and tags
        return super().sanitize_token(token)

    def _kill_token(self, token):
        """Kill a token, the element and all its children will be removed.

        We just keep the token tag (StartTag, EndTag,...) and use a custom tag name
        to be able to remove it after the bleach sanitation. This is needed because
        bleach only remove the element itself and not its children.
        """
        return {
            'name': KILLED_TAG_NAME,
            'type': token['type'],
            'data': {},
        }

    def sanitize_uri_value(self, value, allowed_protocols):
        if value.startswith('data:image/png;base64,'):
            return value
        elif value.startswith('data:image/jpg;base64,'):
            return value

        return super().sanitize_uri_value(value, allowed_protocols)


def html_sanitize(
    src,
    silent=True,
    sanitize_tags=True,
    sanitize_attributes=True,
    sanitize_style=False,
    sanitize_form=True,
    strip_style=False,
    strip_classes=False,
):
    """Sanitize an un-trusted HTML source to be safe from a XSS point of view.

    Careful if you change one default value, it might create a XSS,
    do not change them if you don't know what you do!

    :param src: HTML string to sanitize
    :param silent: If an error occurs during the parsing, do not raise
    :param sanitize_tags: Allow only a whitelist of HTML tags
    :param sanitize_attributes: Allow only a short whitelist of attributes
        If False, the whitelist will be extended
    :param sanitize_style: Sanitize the style attribute, allow only a whitelist of CSS value
    :param sanitize_form: Remove any <form/> tags
    :param strip_style: Remove any "style" attribute (therefore not sanitized)
    :param strip_classes: Remove any "class" attribute
    """
    if not src or not src.strip():
        return src

    if isinstance(src, bytes):
        src = src.decode()

    safe_tags_ = list(safe_tags)
    safe_attrs_ = list(safe_attrs)

    assert not (
        strip_style and sanitize_style
    ), 'You can not sanitize and remove at the same time the style attributes'

    if strip_style:
        safe_attrs_.remove('style')
    if strip_classes:
        safe_attrs_.remove('class')
    if not sanitize_attributes:
        safe_attrs_.extend(extended_safe_attrs)

    def check_attribute(tag, name, value):
        if name.lower() == 'style':
            return not strip_style
        if name.lower() == 'class':
            return not strip_classes
        if not sanitize_attributes and name.lower().startswith('data-'):
            return all(letter in ATTRIBUTE_SUBSET for letter in name)
        return name.lower() in safe_attrs_

    parser = BleachHTMLParser(
        tags=None,
        strip=False,
        consume_entities=False,
        namespaceHTMLElements=False,
    )
    walker = getTreeWalker('etree')

    serializer = BleachHTMLSerializer(
        quote_attr_values='always',
        omit_optional_tags=False,
        escape_lt_in_attrs=True,
        resolve_entities=False,
        sanitize=False,
        alphabetical_attributes=False,
        minimize_boolean_attributes=False,
        use_trailing_solidus=True,
    )

    filtered = OdooCleaner(
        source=walker(parser.parseFragment(src)),
        allowed_elements=safe_tags_,
        attributes={'*': check_attribute},
        allowed_protocols=[
            'http',
            'https',
            'mailto',
            'tel',
            'sms',
            'mid',
            'cid',
        ],
        strip_disallowed_elements=True,
        strip_html_comments=True,
        allowed_css_properties=style_whitelist,
        # Custom arguments
        sanitize_tags=sanitize_tags,
        sanitize_form=sanitize_form,
        sanitize_style=sanitize_style,
    )

    cleaned_src = serializer.render(filtered)

    # See OdooCleaner, we need to removed the killed elements
    cleaned_src = re_killed_tag.sub('', cleaned_src)
    cleaned_src = re_killed_empty.sub('', cleaned_src)

    if not cleaned_src.strip():
        return cleaned_src

    elif (
        cleaned_src
        and cleaned_src.strip()
        and '<p' not in cleaned_src
        and cleaned_src.strip()[0] != '<'
    ):
        cleaned_src = f'<p>{cleaned_src.strip()}</p>'

    elif cleaned_src.startswith('<div>') and cleaned_src.endswith('</div>'):
        cleaned_src = cleaned_src[5:-6]

    return markupsafe.Markup(cleaned_src.strip())
