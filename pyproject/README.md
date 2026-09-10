# Chatbot RAG

Chatbot que responde a perguntas com base em documentos da empresa usando RAG
(Retrieval-Augmented Generation, ou geração aumentada por recuperação).

## Tecnologias

- **Backend:** Python 3.11, FastAPI, FAISS e embeddings da OpenAI, com fallback
	local.
- **Frontend:** Vite.
- **Persistência:** SQLite para histórico, feedback e analytics.

## Como executar

### Instalação

```bash
# Instalar as dependências do backend
pip install --break-system-packages -r backend/requirements.txt

# Instalar o frontend
cd frontend
npm install
cd ..
```

### Inicialização

```bash
# Iniciar a API e a interface
bash start.sh
```

Sem `USER_LLM_API_KEY`, o sistema usa embeddings locais e respostas extrativas.

Para usar a OpenAI, copie `.env.example` para `.env` e preencha as variáveis
`USER_LLM_*`.

## Endpoints da API

- `GET /health`: verifica a saúde da aplicação.
- `POST /chat`: envia uma pergunta ao chatbot.
- `POST /upload`: envia documentos para a base de conhecimento.
- `GET /history/{conversation_id}`: consulta o histórico de uma conversa.
- `POST /feedback`: registra feedback sobre uma resposta.
- `GET /analytics`: consulta as métricas de uso.

## Testes

```bash
cd backend
python -m pytest -q
```

## Docker

```bash
docker compose up --build
```
