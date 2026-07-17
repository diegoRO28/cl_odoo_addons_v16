from odoo import models, fields

class CeiSigner(models.Model):
    _name = 'cei.signer'
    _description = 'Firmantes para documentos académicos'
    _order = 'name'

    name = fields.Char(string="Nombre")
    job_title = fields.Char(string="Cargo")
    sign_signature = fields.Binary(string="Firma Digital", copy=False)