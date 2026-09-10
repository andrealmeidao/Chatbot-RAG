# Chatbot RAG

Chatbot inteligente para consulta de documentos corporativos. O projeto usa
RAG (Retrieval-Augmented Generation) para encontrar informacoes relevantes na
base de conhecimento da empresa e responder perguntas com mais contexto,
agilidade e rastreabilidade.

## O problema no mercado

Empresas acumulam manuais, politicas, FAQs, catalogos, relatorios e outros
documentos importantes, mas essas informacoes normalmente ficam espalhadas em
pastas, sistemas internos e arquivos com formatos diferentes. Como resultado:

- colaboradores gastam tempo procurando respostas;
- equipes de suporte respondem as mesmas perguntas repetidamente;
- informacoes importantes ficam dificeis de encontrar ou sao esquecidas;
- respostas podem variar entre pessoas e canais;
- o conhecimento da empresa se torna dependente de poucos especialistas.

Esse problema reduz a produtividade, aumenta o tempo de atendimento e dificulta
a padronizacao das operacoes. Um chatbot convencional, baseado apenas em
respostas predefinidas, tambem tem dificuldade para acompanhar documentos que
mudam com frequencia.

## A solução

O Chatbot RAG transforma os documentos da empresa em uma base de conhecimento
consultavel. Quando uma pessoa envia uma pergunta, o sistema:

1. interpreta a consulta;
2. localiza os trechos mais relevantes nos documentos;
3. monta uma resposta com base nesse contexto;
4. registra historico e feedback para apoiar a melhoria do atendimento.

Assim, a empresa oferece acesso mais rapido ao proprio conhecimento sem exigir
que cada usuario saiba em qual arquivo ou pasta procurar. O sistema tambem
possui fallback local, permitindo respostas extrativas mesmo sem uma chave de
API de LLM configurada.

## Principais funcionalidades

- Consulta conversacional sobre documentos internos.
- Busca semantica para encontrar conteudo relacionado a pergunta.
- Suporte a arquivos TXT, CSV, PDF e DOCX.
- Upload de novos documentos pela API.
- Historico de conversas por identificador.
- Registro de feedback sobre as respostas.
- Endpoint de analytics para acompanhar o uso.
- Embeddings OpenAI ou processamento local como fallback.

## Tecnologias utilizadas

### Backend

- **Python 3.11:** linguagem principal da aplicacao.
- **FastAPI:** criacao da API HTTP e dos endpoints do chatbot.
- **Uvicorn:** servidor ASGI usado para executar a API.
- **Pydantic:** validacao e tipagem dos dados recebidos pela API.
- **FAISS:** indexacao e busca vetorial dos trechos de documentos.
- **NumPy:** suporte ao processamento dos vetores numericos.
- **SQLite:** persistencia de historico, feedback e metricas.

### Inteligencia artificial e processamento de documentos

- **Embeddings OpenAI:** representacao semantica dos documentos e perguntas.
- **Embeddings locais:** alternativa para executar o projeto sem servico externo.
- **Pipeline RAG:** carregamento, divisao, indexacao, recuperacao e geracao de
	respostas.
- **pypdf:** leitura de documentos PDF.
- **python-docx:** leitura de documentos DOCX.

### Frontend e infraestrutura

- **Vite:** servidor de desenvolvimento e empacotamento da interface web.
- **JavaScript:** implementacao da experiencia do usuario.
- **Docker e Docker Compose:** execucao reproduzivel do backend e frontend.
- **GitHub Actions:** automacao da integracao continua.

## Estrutura do projeto

```text
pyproject/
├── backend/
│   ├── app/                 # API, configuracao e pipeline RAG
│   ├── data/docs/           # Documentos da base de conhecimento
│   └── tests/               # Testes automatizados
├── frontend/                # Interface web em Vite
├── Dockerfile
├── docker-compose.yml
└── start.sh
```

## Como executar

Requisitos: Python 3.11+, Node.js 18+ e npm.

```bash
cd pyproject
pip install -r backend/requirements.txt
cd frontend
npm install
cd ..
bash start.sh
```

Sem `USER_LLM_API_KEY`, o projeto utiliza embeddings locais e respostas
extrativas. Para configurar um provedor externo, copie `.env.example` para
`.env` e preencha as variaveis `USER_LLM_*`.

Tambem e possivel executar com Docker:

```bash
cd pyproject
docker compose up --build
```

## API

- `GET /health` - verifica a saude da aplicacao.
- `POST /chat` - envia uma pergunta ao chatbot.
- `POST /upload` - adiciona documentos a base de conhecimento.
- `GET /history/{conversation_id}` - consulta o historico de uma conversa.
- `POST /feedback` - registra feedback sobre uma resposta.
- `GET /analytics` - consulta metricas de uso.

## Testes

```bash
cd pyproject/backend
python -m pytest -q
```

## Documentacao adicional

- [Design do chatbot RAG](pyproject/CHATBOT_RAG_DESIGN.md)
- [Guia operacional](pyproject/README.md)
