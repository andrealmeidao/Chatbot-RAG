# Chatbot RAG

Chatbot que responde perguntas com base em documentos da empresa (RAG: retrieval + geracao).

## Stack

- Backend: Python 3.11, FastAPI, FAISS, embeddings OpenAI (com fallback local)
- Frontend: Vite
- Persistencia: SQLite (historico, feedback, analytics)

## Como rodar

```bash
# Instalar dependencias do backend
pip install --break-system-packages -r backend/requirements.txt

# Instalar frontend
cd frontend
npm install
cd ..

# Subir API e interface
bash start.sh
```

Sem `USER_LLM_API_KEY`, o sistema usa embeddings locais e respostas extrativas.

Para usar OpenAI, copie `.env.example` e preencha as variaveis `USER_LLM_*`.

## API

- `GET /health`
- `POST /chat`
- `POST /upload`
- `GET /history/{conversation_id}`
- `POST /feedback`
- `GET /analytics`

## Testes

```bash
cd backend
python3 -m pytest -q
```

## Docker

```bash
docker compose up --build
```
