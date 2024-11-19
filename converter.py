import streamlit as st
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pdfplumber
import re
from datetime import datetime
from pytesseract import image_to_string
from PIL import Image
import io

# Configurações de e-mail
def send_email(name, email, phone, message):
    sender_email = "accrossconverter@gmail.com"
    sender_password = "jmhv smap mkrf btdv"
    receiver_email = "gilberto@gbernardoti.com.br"

    subject = f"Novo comentário de {name}"
    body = f"""
    Nome: {name}
    E-mail: {email}
    Telefone: {phone}
    
    Mensagem:
    {message}
    """

    # Criar o e-mail
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:  # Servidor e porta do Gmail
            server.starttls()  # Inicia conexão segura
            server.login(sender_email, sender_password)  # Login no servidor
            server.sendmail(sender_email, receiver_email, msg.as_string())  # Envia o e-mail
        return "Mensagem enviada com sucesso!"
    except Exception as e:
        return f"Erro ao enviar mensagem: {e}"


# Funções de conversão
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
    amount_pattern = re.compile(r"[-+]?\d+,\d{2}")

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

def extract_transactions_from_image(image_file):
    img = Image.open(image_file)
    text = image_to_string(img, lang="por")
    transactions = []
    date_pattern = re.compile(r"\d{2}/\d{2}/\d{4}")
    amount_pattern = re.compile(r"[-+]?\d+,\d{2}")

    for line in text.split("\n"):
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


# Interface do Streamlit
st.title("Conversor de PDF e Relatórios Digitalizados para OFX")

st.markdown("---")
st.subheader("1. Converter PDF para OFX")
uploaded_pdf = st.file_uploader("Escolha um arquivo PDF", type="pdf")
if uploaded_pdf is not None:
    transactions = extract_transactions_from_pdf(uploaded_pdf)
    ofx_content = create_ofx_content(transactions)
    st.download_button(
        label="Baixar arquivo OFX",
        data=ofx_content.encode('utf-8'),
        file_name="extrato.ofx",
        mime="application/x-ofx"
    )

st.markdown("---")
st.subheader("2. Converter relatório digitalizado para OFX")
uploaded_image = st.file_uploader("Escolha uma imagem do relatório digitalizado", type=["png", "jpg", "jpeg"])
if uploaded_image is not None:
    transactions = extract_transactions_from_image(uploaded_image)
    ofx_content = create_ofx_content(transactions)
    st.download_button(
        label="Baixar arquivo OFX",
        data=ofx_content.encode('utf-8'),
        file_name="extrato_digitalizado.ofx",
        mime="application/x-ofx"
    )

st.markdown("---")
st.subheader("3. Envie sugestões ou pedidos")
with st.form(key="contact_form"):
    name = st.text_input("Nome")
    phone = st.text_input("Celular")
    email = st.text_input("E-mail")
    message = st.text_area("Sua mensagem")
    submitted = st.form_submit_button("Enviar mensagem")
    if submitted:
        response = send_email(name, email, phone, message)
        st.success(response)

st.markdown("---")
st.subheader("4. Apoie o projeto")
st.markdown("""
Para ajudar a manter este projeto e implementar melhorias, considere fazer uma doação de qualquer valor. Sua contribuição é muito importante!
""")
st.image("./images/qrcodeOFXConverter.jpg", width=150, caption="Use o QR Code para enviar sua contribuição.")
st.markdown("**Chave PIX:** gilberto@gbernardoti.com.br")

st.markdown("---")
st.markdown("""
#### Desenvolvedores:
**Gabrielli Letícia**  
**Gilberto Aparecido Bernardo Junior**

**WhatsApp:** +55 (16) 9.8857-2758  
**E-mail:** [gilberto@gbernardoti.com.br](mailto:gilberto@gbernardoti.com.br)  
Araraquara - SP - Brasil
""")
