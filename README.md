# Chatbot RAG

Chatbot inteligente para consulta de documentos corporativos. O projeto usa
RAG (Retrieval-Augmented Generation) para encontrar informações relevantes na
base de conhecimento da empresa e responder a perguntas com mais contexto,
agilidade e rastreabilidade.

## O problema no mercado

Empresas acumulam manuais, políticas, FAQs, catálogos, relatórios e outros
documentos importantes, mas essas informações normalmente ficam espalhadas em
pastas, sistemas internos e arquivos com formatos diferentes. Como resultado:

- colaboradores gastam tempo procurando respostas;
- equipes de suporte respondem as mesmas perguntas repetidamente;
- informações importantes ficam difíceis de encontrar ou são esquecidas;
- respostas podem variar entre pessoas e canais;
- o conhecimento da empresa torna-se dependente de poucos especialistas.

Esse problema reduz a produtividade, aumenta o tempo de atendimento e dificulta
a padronização das operações. Um chatbot convencional, baseado apenas em
respostas predefinidas, também tem dificuldade para acompanhar documentos que
mudam com frequência.

## A solução

O Chatbot RAG transforma os documentos da empresa em uma base de conhecimento
consultável. Quando uma pessoa envia uma pergunta, o sistema:

1. interpreta a consulta;
2. localiza os trechos mais relevantes nos documentos;
3. monta uma resposta com base nesse contexto;
4. registra histórico e feedback para apoiar a melhoria do atendimento.

Assim, a empresa oferece acesso mais rápido ao próprio conhecimento sem exigir
que cada usuário saiba em qual arquivo ou pasta procurar. O sistema também
possui fallback local, permitindo respostas extrativas mesmo sem uma chave de
API de LLM configurada.

## Principais funcionalidades

- Consulta conversacional sobre documentos internos.
- Busca semântica para encontrar conteúdo relacionado à pergunta.
- Suporte a arquivos TXT, CSV, PDF e DOCX.
- Upload de novos documentos pela API.
- Histórico de conversas por identificador.
- Registro de feedback sobre as respostas.
- Endpoint de analytics para acompanhar o uso.
- Embeddings OpenAI ou processamento local como fallback.

## Tecnologias utilizadas

### Backend

- **Python 3.11:** linguagem principal da aplicação.
- **FastAPI:** criação da API HTTP e dos endpoints do chatbot.
- **Uvicorn:** servidor ASGI usado para executar a API.
- **Pydantic:** validação e tipagem dos dados recebidos pela API.
- **FAISS:** indexação e busca vetorial dos trechos de documentos.
- **NumPy:** suporte ao processamento dos vetores numéricos.
- **SQLite:** persistência de histórico, feedback e métricas.

### Inteligencia artificial e processamento de documentos

- **Embeddings OpenAI:** representação semântica dos documentos e perguntas.
- **Embeddings locais:** alternativa para executar o projeto sem serviço externo.
- **Pipeline RAG:** carregamento, divisão, indexação, recuperação e geração de
  respostas.
- **pypdf:** leitura de documentos PDF.
- **python-docx:** leitura de documentos DOCX.

### Frontend e infraestrutura

- **Vite:** servidor de desenvolvimento e empacotamento da interface web.
- **JavaScript:** implementação da experiência do usuário.
- **Docker e Docker Compose:** execução reproduzível do backend e frontend.
- **GitHub Actions:** automação da integração contínua.

## Estrutura do projeto

```text
pyproject/
├── backend/
│   ├── app/                 # API, configuração e pipeline RAG
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
`.env` e preencha as variáveis `USER_LLM_*`.

Também é possível executar com Docker:

```bash
cd pyproject
docker compose up --build
```

## API

- `GET /health` - verifica a saúde da aplicação.
- `POST /chat` - envia uma pergunta ao chatbot.
- `POST /upload` - adiciona documentos à base de conhecimento.
- `GET /history/{conversation_id}` - consulta o histórico de uma conversa.
- `POST /feedback` - registra feedback sobre uma resposta.
- `GET /analytics` - consulta métricas de uso.

## Testes

```bash
cd pyproject/backend
python -m pytest -q
```

## Documentação adicional

- [Design do chatbot RAG](pyproject/CHATBOT_RAG_DESIGN.md)
- [Guia operacional](pyproject/README.md)
