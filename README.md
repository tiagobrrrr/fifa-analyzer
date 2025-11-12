# FIFA Analyzer

Projeto: fifa-analyzer
E-mail de envio configurado por padrão em .env.example: tiagoh736@gmail.com

## Como usar (local)
1. clone
2. criar e ativar venv
3. instale dependências:
    pip install -r requirements.txt
4. copie `.env.example` para `.env` e preencha `EMAIL_PASSWORD`
5. rode:
    python app.py

## Deploy (Render)
- Crie um Web Service no Render e conecte ao GitHub.
- Build command: `pip install -r requirements.txt`
- Start command: `python app.py`
- Adicione as variáveis de ambiente no painel do Render (EMAIL_ADDRESS, EMAIL_PASSWORD, etc.)
