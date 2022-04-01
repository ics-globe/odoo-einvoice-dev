# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import ssl
from base64 import b64decode
from copy import deepcopy
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

import xmlsig
from OpenSSL import crypto
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree
import xades
from xades import XAdESContext
from xades.policy import GenericPolicyId

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import file_open, ormcache

class Certificate(models.Model):
    _name = 'l10n_es_edi_face.certificate'
    _description = 'Facturae Digital Certificate'
    _order = 'date_start desc, id desc'
    _rec_name = 'serial_number'

    content = fields.Binary(string="PFX Certificate", required=True, help="PFX Certificate")
    password = fields.Char(help="Passphrase for the PFX certificate")
    serial_number = fields.Char(readonly=True, index=True, help="The serial number to add to electronic documents")
    date_start = fields.Datetime(readonly=True, help="The date on which the certificate starts to be valid")
    date_end = fields.Datetime(readonly=True, help="The date on which the certificate expires")
    company_id = fields.Many2one(comodel_name='res.company', required=True, default=lambda self: self.env.company)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @ormcache('self.content', 'self.password')
    def _decode_certificate(self):
        """
        Return the content (DER encoded) and the certificate decrypted based in the point 3.1 from the RS 097-2012
        :return tuple: encoded certificate, private key, decrypted certificate
        """

        self.ensure_one()

        decrypted_content = crypto.load_pkcs12(b64decode(self.content), self.password.encode())
        certificate = decrypted_content.get_certificate()
        private_key = decrypted_content.get_privatekey()
        pem_certificate = crypto.dump_certificate(crypto.FILETYPE_PEM, certificate)
        pem_private_key = crypto.dump_privatekey(crypto.FILETYPE_PEM, private_key)

        # Cleanup pem_content.
        for to_clean in ('\n', ssl.PEM_HEADER, ssl.PEM_FOOTER):
            pem_certificate = pem_certificate.replace(to_clean.encode('UTF-8'), b'')

        return pem_certificate, pem_private_key, certificate

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        certificates = super().create(vals_list)
        date_format = '%Y%m%d%H%M%SZ'
        for certificate in certificates:
            try:
                dummy, dummy, certif = certificate._decode_certificate()
                cert_date_start = datetime.datetime.strptime(certif.get_notBefore().decode(), date_format)
                cert_date_end = datetime.datetime.strptime(certif.get_notAfter().decode(), date_format)
                serial_number = certif.get_serial_number()
            except crypto.Error:
                raise ValidationError(_('There has been a problem with the certificate, some usual problems can be:\n'
                                        '- The password given or the certificate are not valid.\n'
                                        '- The certificate content is invalid.'))
            # Assign extracted values from the certificate
            certificate.write({
                'serial_number': str(serial_number)[1::2],
                'date_start': fields.Datetime.to_string(cert_date_start),
                'date_end': fields.Datetime.to_string(cert_date_end),
            })
            if datetime.datetime.now() > cert_date_end:
                raise ValidationError(_('The certificate is expired since %s') % certificate.date_end)
        return certificates

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def sign_xml(self, edi_data, sig_data):
        """
        Signs the given XML data with the certificate and private key.
        :param str edi_data: The XML data to sign.
        :param dict sig_data: The signature data to use.
        :return str: The signed XML data as a sting.
        """
        self.ensure_one()
        nspaces = {
            'xd': 'http://www.w3.org/2000/09/xmldsig#',
            'xades': 'http://uri.etsi.org/01903/v1.3.2#',
            'fac': "http://www.facturae.es/Facturae/2007/v3.1/Facturae"
        }
        root = etree.fromstring(deepcopy(edi_data).encode("utf-8"))
        root.remove(root.xpath('//xd:Signature', namespaces=nspaces)[0])

        signature = xmlsig.template.create(
                xmlsig.constants.TransformInclC14N,
                xmlsig.constants.TransformRsaSha1,
                "Signature",
                ns="xd",
        )

        signature_id = "Signature-SignedProperties"
        ref = xmlsig.template.add_reference(signature, xmlsig.constants.TransformSha1, uri="", name="REF")
        xmlsig.template.add_transform(ref, xmlsig.constants.TransformEnveloped)
        xmlsig.template.add_reference(signature, xmlsig.constants.TransformSha1, uri="#KI")
        xmlsig.template.add_reference(signature, xmlsig.constants.TransformSha1, uri="#" + signature_id)
        ki = xmlsig.template.ensure_key_info(signature, name="KI")
        data = xmlsig.template.add_x509_data(ki)
        xmlsig.template.x509_data_add_certificate(data)
        serial = xmlsig.template.x509_data_add_issuer_serial(data)
        xmlsig.template.x509_issuer_serial_add_issuer_name(serial)
        xmlsig.template.x509_issuer_serial_add_serial_number(serial)
        xmlsig.template.add_key_value(ki)
        qualifying = xades.template.create_qualifying_properties(
                signature,
                etsi='xades',
        )
        props = xades.template.create_signed_properties(
                qualifying,
                name=signature_id,
        )
        xades.template.add_claimed_role(props, sig_data["SignerRole"])

        pol_id = "http://www.facturae.gob.es/politica_de_firma_formato_facturae" \
                 "/politica_de_firma_formato_facturae_v3_1.pdf"
        pol_desc = "Politica de firma Facturae v3.1"
        policy = GenericPolicyId(pol_id, pol_desc, xmlsig.constants.TransformSha1)
        root.append(signature)

        certificate = pkcs12.load_key_and_certificates(
                b64decode(self.content),
                self.password.encode(),
                default_backend()
        )
        ctx = xades.XAdESContext(policy, [certificate[1]])
        ctx.load_pkcs12(certificate)

        try:
            ctx.sign(signature)
            ctx.verify(signature)

        except HTTPError:
            with file_open('l10n_es_facturae/data/politica_de_firma_formato_facturae_v3_1.pdf', 'rb') as f:
                pol_data = f.read()

            with patch(urlopen, pol_data):
                ctx.sign(signature)
                ctx.verify(signature)

        return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True, pretty_print=True)
