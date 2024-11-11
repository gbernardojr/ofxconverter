import streamlit as st
import pdfplumber
import re
from datetime import datetime
import io

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y%m%d")
    except ValueError:
        return None

def parse_amount(amount_str):
    return float(amount_str.replace(",", ".").replace(" ", ""))

def extract_transactions_from_pdf(pdf_file):
    transactions = []
    date_pattern = re.compile(r"\d{2}/\d{2}/\d{4}")
    amount_pattern = re.compile(r"[-+]?\d+,\d{2}")  # Formato com vírgula para valores em moeda

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split("\n")
            for line in lines:
                date_match = date_pattern.search(line)
                amount_match = amount_pattern.search(line)
                if date_match and amount_match:
                    date = parse_date(date_match.group())
                    amount = parse_amount(amount_match.group())
                    description = line[:date_match.start()].strip()
                    transactions.append({
                        "date": date,
                        "description": description,
                        "amount": amount
                    })
    
    return transactions

def create_ofx_content(transactions, bank_id="123", acct_id="000111222"):
    ofx_content = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
  <SIGNONMSGSRSV1>
    <SONRS>
      <STATUS>
        <CODE>0</CODE>
        <SEVERITY>INFO</SEVERITY>
      </STATUS>
      <DTSERVER>{}</DTSERVER>
      <LANGUAGE>ENG</LANGUAGE>
    </SONRS>
  </SIGNONMSGSRSV1>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <TRNUID>1001</TRNUID>
      <STATUS>
        <CODE>0</CODE>
        <SEVERITY>INFO</SEVERITY>
      </STATUS>
      <STMTRS>
        <CURDEF>BRL</CURDEF>
        <BANKACCTFROM>
          <BANKID>{}</BANKID>
          <ACCTID>{}</ACCTID>
          <ACCTTYPE>CHECKING</ACCTTYPE>
        </BANKACCTFROM>
        <BANKTRANLIST>
""".format(datetime.now().strftime("%Y%m%d%H%M%S"), bank_id, acct_id)

    for transaction in transactions:
        ofx_content += """
          <STMTTRN>
            <TRNTYPE>{}</TRNTYPE>
            <DTPOSTED>{}</DTPOSTED>
            <TRNAMT>{:.2f}</TRNAMT>
            <FITID>{}</FITID>
            <NAME>{}</NAME>
          </STMTTRN>
""".format(
            "DEBIT" if transaction["amount"] < 0 else "CREDIT",
            transaction["date"],
            transaction["amount"],
            hash(transaction["description"] + transaction["date"]),
            transaction["description"]
        )

    ofx_content += """
        </BANKTRANLIST>
        <LEDGERBAL>
          <BALAMT>0.00</BALAMT>
          <DTASOF>{}</DTASOF>
        </LEDGERBAL>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>
""".format(datetime.now().strftime("%Y%m%d%H%M%S"))

    return ofx_content

def convert_ofx_to_bytes(ofx_data):
    return ofx_data.encode('utf-8')

# Início da aplicação Streamlit
st.title("Conversor de PDF para OFX - Accross Business Intelligence")

st.markdown("---")
st.markdown("### Bem-vindo ao conversor de PDF para OFX da Accross Business Intelligence")
st.markdown("**Este aplicativo permite converter arquivos PDF de extratos bancários para o formato OFX**.")
st.markdown("---")

uploaded_file = st.file_uploader("Escolha um arquivo PDF", type="pdf")

if uploaded_file is not None:
    st.write("Arquivo carregado com sucesso.")
    
    # Processamento do arquivo PDF
    transactions = extract_transactions_from_pdf(uploaded_file)
    ofx_content = create_ofx_content(transactions)
    ofx_bytes = convert_ofx_to_bytes(ofx_content)
    
    # Botão de download do arquivo OFX gerado
    st.download_button(
        label="Baixar arquivo OFX",
        data=ofx_bytes,
        file_name="extrato.ofx",
        mime="application/x-ofx"
    )

# Rodapé com informações de contato
st.markdown("---")
st.markdown("**Contato:** gilberto@gbernardojr.com.br | **WhatsApp:** (16) 9.8857-2758")
