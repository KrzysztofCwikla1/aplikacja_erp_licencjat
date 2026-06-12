import os
from fpdf import FPDF
from datetime import datetime

INVOICE_DIR = os.path.join(os.path.dirname(__file__), "invoices")
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")


class InvoicePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("DejaVu", "", os.path.join(FONT_DIR, "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"))

    def header(self):
        self.set_font("DejaVu", "B", 18)
        self.cell(0, 12, "FAKTURA VAT", ln=True, align="C")
        self.set_font("DejaVu", "", 9)
        self.cell(0, 5, "System ERP – Firma Ceramica", ln=True, align="C")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "", 8)
        self.cell(0, 10, f"Dokument wygenerowany przez system ERP – {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")


def generate_invoice_pdf(invoice_data, items):
    pdf = InvoicePDF()
    pdf.add_page()

    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 7, f"Numer: {invoice_data['invoice_number']}", ln=True)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 6, f"Data wystawienia: {invoice_data['issue_date']}", ln=True)
    pdf.cell(0, 6, f"Termin płatności: {invoice_data['due_date']}", ln=True)
    pdf.ln(4)

    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "Nabywca:", ln=True)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 6, invoice_data["client_name"], ln=True)
    if invoice_data.get("client_address"):
        pdf.cell(0, 6, invoice_data["client_address"], ln=True)
    if invoice_data.get("client_nip"):
        pdf.cell(0, 6, f"NIP: {invoice_data['client_nip']}", ln=True)
    pdf.ln(6)

    pdf.set_font("DejaVu", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(80, 8, "Opis", border=1, fill=True)
    pdf.cell(25, 8, "Ilość", border=1, fill=True, align="R")
    pdf.cell(40, 8, "Cena jedn. (EUR)", border=1, fill=True, align="R")
    pdf.cell(40, 8, "Wartość (EUR)", border=1, fill=True, align="R", ln=True)

    pdf.set_font("DejaVu", "", 9)
    for it in items:
        pdf.cell(80, 8, it["description"][:42], border=1)
        pdf.cell(25, 8, f"{it['quantity']:.0f}", border=1, align="R")
        pdf.cell(40, 8, f"{it['unit_price']:,.2f}", border=1, align="R")
        pdf.cell(40, 8, f"{it['line_total']:,.2f}", border=1, align="R", ln=True)
    pdf.ln(4)

    pdf.set_font("DejaVu", "", 10)
    pdf.cell(145, 7, "Razem netto:", align="R")
    pdf.cell(40, 7, f"{invoice_data['total_net']:,.2f} EUR", align="R", ln=True)
    vat = invoice_data["total_gross"] - invoice_data["total_net"]
    pdf.cell(145, 7, "VAT (23%):", align="R")
    pdf.cell(40, 7, f"{vat:,.2f} EUR", align="R", ln=True)
    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(145, 8, "Razem brutto:", align="R")
    pdf.cell(40, 8, f"{invoice_data['total_gross']:,.2f} EUR", align="R", ln=True)

    safe_number = invoice_data["invoice_number"].replace("/", "_")
    filepath = os.path.join(INVOICE_DIR, f"{safe_number}.pdf")
    pdf.output(filepath)
    return filepath


if __name__ == "__main__":
    test_inv = {"invoice_number": "FV/2026/TEST", "client_name": "Spółka Łąkowska Ś.A.",
                "client_address": "ul. Żółtych Łąk 5, Świętochłowice", "client_nip": "PL0123456789",
                "issue_date": "2026-06-05", "due_date": "2026-06-19",
                "total_net": 68400.0, "total_gross": 84132.0}
    test_items = [{"description": "Płytki Marmo 60×60", "quantity": 4200, "unit_price": 16.29, "line_total": 68400.0}]
    path = generate_invoice_pdf(test_inv, test_items)
    print(f"Faktura wygenerowana: {path}, rozmiar: {os.path.getsize(path)} B")
