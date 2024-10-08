from odoo import api, fields, models, _
from datetime import datetime, timedelta

class InvoiceReportPDF(models.TransientModel):
    _name = 'invoice.report.pdf'
    _description = "Invoice Report PDF"

    name = fields.Char('Name')
    pdf_file = fields.Binary('Click On Download Link To Download \
        PDF', readonly=True)

    def action_back(self):
        return {'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'invoice.report.pdf',
            'target': 'new'}

