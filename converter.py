import streamlit as st
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pdfplumber
import re
from datetime import datetime
import os
import requests
import json


# Configurações globais
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "accrossconverter@gmail.com"
SENDER_PASSWORD = "jmhv smap mkrf btdv"
OCR_API_URL = "https://api.ocr.space/parse/image"
OCR_API_KEY = 'K85741052388957'
VISIT_COUNT_FILE = "visit_count.txt"

# Função para carregar e incrementar o contador de visitantes
def update_visit_count():
    if not os.path.exists(VISIT_COUNT_FILE):
        with open(VISIT_COUNT_FILE, "w") as f:
            f.write("0")
    with open(VISIT_COUNT_FILE, "r+") as f:
        count = int(f.read())
        count += 1
        f.seek(0)
        f.write(str(count))
        f.truncate()
    return count

# Atualiza e exibe o contador de visitantes
visit_count = update_visit_count()



# Função para enviar e-mail
def send_email(name, email, phone, message):
    try:
        receiver_email = "gilberto@gbernardoti.com.br"
        subject = f"Novo comentário de {name}"
        body = f"""
        Nome: {name}
        E-mail: {email}
        Telefone: {phone}
        
        Mensagem:
        {message}
        """
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        return "Mensagem enviada com sucesso!"
    except Exception as e:
        return f"Erro ao enviar mensagem: {e}"


# Função para OCR com API OCR Space
def perform_ocr(image_path, api_key=OCR_API_KEY):
    with open(image_path, "rb") as f:
        response = requests.post(
            OCR_API_URL,
            files={"file": f},
            data={"apikey": api_key, "language": "por"}
        )
    try:
        result = response.json()
        return result.get("ParsedResults", [{}])[0].get("ParsedText", "")
    except (json.JSONDecodeError, KeyError):
        return "Erro ao processar OCR."


# Funções auxiliares para manipulação de dados
def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y%m%d")
    except ValueError:
        return None


def parse_amount(amount_str):
    try:
        return float(amount_str.replace(",", ".").replace(" ", ""))
    except ValueError:
        return 0.0


# Funções de conversão de PDF e OFX
def extract_transactions_from_pdf(pdf_file):
    transactions = []
    date_pattern = re.compile(r"\d{2}/\d{2}/\d{4}")
    amount_pattern = re.compile(r"[-+]?\d+,\d{2}")
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            for line in page.extract_text().split("\n"):
                date_match = date_pattern.search(line)
                amount_match = amount_pattern.search(line)
                if date_match and amount_match:
                    transactions.append({
                        "date": parse_date(date_match.group()),
                        "description": line[:date_match.start()].strip(),
                        "amount": parse_amount(amount_match.group())
                    })
    return transactions


def create_ofx_content(transactions, bank_id="123", acct_id="000111222"):
    header = f"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
<OFX>
  <SIGNONMSGSRSV1>
    <SONRS>
      <STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
      <DTSERVER>{datetime.now().strftime("%Y%m%d%H%M%S")}</DTSERVER>
      <LANGUAGE>POR</LANGUAGE>
    </SONRS>
  </SIGNONMSGSRSV1>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <STMTRS>
        <BANKTRANLIST>
"""
    body = ""
    for transaction in transactions:
        body += f"""
          <STMTTRN>
            <TRNTYPE>{"DEBIT" if transaction["amount"] < 0 else "CREDIT"}</TRNTYPE>
            <DTPOSTED>{transaction["date"]}</DTPOSTED>
            <TRNAMT>{transaction["amount"]:.2f}</TRNAMT>
            <FITID>{hash(transaction["description"] + transaction["date"])}</FITID>
            <NAME>{transaction["description"]}</NAME>
          </STMTTRN>
"""
    footer = """
        </BANKTRANLIST>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>
"""
    return header + body + footer


# Interface Streamlit
st.title("Conversor de PDF para OFX")
st.markdown("---")

# Layout com área de conteúdo principal e anúncios
col1, col2 = st.columns([4, 2])  # Define proporção de colunas (4:1)

with col1:

    # Conversão de PDF para OFX
    st.subheader("1. Converter PDF para OFX")
    uploaded_pdf = st.file_uploader("Escolha um arquivo PDF", type="pdf")
    if uploaded_pdf:
        transactions = extract_transactions_from_pdf(uploaded_pdf)
        ofx_content = create_ofx_content(transactions)
        st.download_button(
            label="Baixar arquivo OFX",
            data=ofx_content.encode("utf-8"),
            file_name="extrato.ofx",
            mime="application/x-ofx"
        )

    # OCR e conversão para OFX
    st.subheader("2. Converter imagem ou PDF digitalizado para OFX")
    uploaded_image = st.file_uploader("Escolha uma imagem ou PDF digitalizado", type=["jpg", "png", "jpeg", "pdf"])
    if uploaded_image:
        temp_path = f"temp_file.{uploaded_image.name.split('.')[-1]}"
        with open(temp_path, "wb") as temp_file:
            temp_file.write(uploaded_image.read())

        extracted_text = perform_ocr(temp_path)
        os.remove(temp_path)
        st.text_area("Texto OCR", extracted_text)
        if st.button("Converter texto OCR para OFX"):
            ofx_path = create_ofx_content([{"date": "20240101", "description": "Exemplo", "amount": 100.0}])
            st.download_button("Baixar arquivo OFX", data=ofx_path.encode("utf-8"), file_name="ocr_result.ofx")

    # Formulário de contato
    st.subheader("3. Envie sugestões ou pedidos")
    with st.form("contact_form"):
        name = st.text_input("Nome")
        phone = st.text_input("Celular")
        email = st.text_input("E-mail")
        message = st.text_area("Sua mensagem")
        if st.form_submit_button("Enviar mensagem"):
            response = send_email(name, email, phone, message)
            st.success(response)

    st.markdown("---")
    st.subheader("4. Apoie o projeto")
    st.markdown("""
    Para ajudar a manter este projeto e implementar melhorias, considere fazer uma doação de qualquer valor. Sua contribuição é muito importante!
    """)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    qr_code_path = os.path.join("static", "qrcodeOFXConverter.jpg")
    st.image("https://raw.githubusercontent.com/gbernardojr/ofxconverter/refs/heads/main/qrCodeOFXConverter.jpg", 
            width=150, 
            caption="Use o QR Code para enviar sua contribuição.")

    st.markdown("**Chave PIX:** gilberto@gbernardoti.com.br")

    # Rodapé com informações de contato
    st.markdown("---")
    st.markdown("""
    **Desenvolvedores:**  
    - Gilberto Aparecido Bernardo Junior  
    - Gabrielli Leticia Souza Stencel  

    **WhatsApp:** +55 (16) 9.8857-2758  
    **E-mail:** [gilberto@gbernardoti.com.br](mailto:gilberto@gbernardoti.com.br)  
    **Localização:** Araraquara - SP - Brasil
    """)
    st.markdown("---")
    # Exibe o contador de visitantes no topo da página
    st.markdown(f"### 👤 Visitantes únicos: {visit_count}")    
    
with col2:
    st.subheader("Publicidade")
    #st.markdown("### Apoie este projeto exibindo anúncios relevantes.")
    # Adicione o código do Google AdSense
    st.markdown("""
    <script async
            src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"></script>
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-5482408351463332
         data-ad-slot="9361640888"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>
         (adsbygoogle = window.adsbygoogle || []).push({});
    </script>
    """, unsafe_allow_html=True)
