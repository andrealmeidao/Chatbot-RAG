# Chatbot RAG - Documentação de Design e Arquitetura

## 1. Visão Geral do Projeto

### 1.1 Objetivo
Desenvolver um chatbot inteligente que responde perguntas baseado em documentos próprios da empresa, sem depender apenas do conhecimento genérico do modelo de IA.

### 1.2 Problema Resolvido
**Situação Atual:** Chatbots genéricos não conhecem informações específicas da empresa (políticas, procedimentos, base de conhecimento).

**Solução:** Sistema RAG que combina busca em documentos + IA generativa para respostas precisas e contextualizadas.

### 1.3 Valor Agregado
- ✅ Respostas precisas baseadas em documentos reais
- ✅ Reduz custos de atendimento humano
- ✅ Disponível 24/7
- ✅ Escalável (adiciona novos docs facilmente)

---

## 2. Arquitetura do Sistema

### 2.1 Componentes Principais

```
┌─────────────────────────────────────────────────────────┐
│                    CHATBOT RAG SYSTEM                   │
└─────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐
│   Frontend       │◄────────►│     FastAPI      │
│   (Web/App)      │         │   (REST API)     │
└──────────────────┘         └────────┬─────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
            ┌───────▼────────┐              ┌──────────▼──────┐
            │  RAG Pipeline  │              │  Vector Store   │
            │  (LangChain)   │              │    (FAISS)      │
            └────────┬───────┘              └─────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   ┌────▼────┐  ┌────▼────┐  ┌──▼─────┐
   │ Document│  │Embedding│  │  LLM   │
   │ Loader  │  │ Generator│  │(OpenAI)│
   └─────────┘  └─────────┘  └────────┘
```

### 2.2 Fluxo de Dados

#### **FASE 1: PREPARAÇÃO (Offline - Uma única vez)**

```
1. INPUT
   └─► Documentos (PDF, TXT, Word)
       - Políticas da empresa
       - Base de conhecimento
       - Manuais técnicos
       
2. PROCESSAMENTO
   └─► Document Loading
       └─► Text Splitting (Chunks)
           └─► Embedding Generation (OpenAI API)
               └─► Vector Store Indexing (FAISS)

3. OUTPUT
   └─► Vector Store pronto para queries
```

#### **FASE 2: EXECUÇÃO (Online - Cada pergunta)**

```
1. INPUT
   └─► Pergunta do usuário
       "Qual é a política de refund?"

2. BUSCA
   └─► Embed pergunta
       └─► Retrieval (buscar chunks similares)
           └─► Top-K chunks selecionados

3. AUGMENTAÇÃO
   └─► Montar prompt com contexto
       "Use estes trechos: [chunks]"

4. GERAÇÃO
   └─► LLM responde (OpenAI API)

5. OUTPUT
   └─► Resposta ao usuário
       "O refund é válido por 30 dias..."
```

---

## 3. Especificação Técnica

### 3.1 Componentes de Software

#### **3.1.1 Document Loader**
**O quê:** Lê diferentes formatos de arquivo
**Como:**
- PyPDF: PDFs
- TextLoader: TXT
- UnstructuredWord: DOCX
- CSV Loader: CSVs

**Entrada:** Arquivo físico ou URL
**Saída:** Lista de documentos (metadata + conteúdo)

```python
Document(
    page_content="Refund em 30 dias...",
    metadata={"source": "politica.pdf", "page": 1}
)
```

---

#### **3.1.2 Text Splitter**
**O quê:** Divide documentos grandes em chunks
**Por quê:** LLMs têm limite de contexto, FAISS é mais eficiente com chunks pequenos

**Parâmetros:**
- `chunk_size=500` → 500 caracteres por chunk
- `chunk_overlap=100` → 100 chars de sobreposição

**Exemplo:**
```
Documento: "Política de Refund. Refund é permitido em 30 dias. 
            Produto deve estar novo. Sem marcas de uso..."

Chunk 1: "Política de Refund. Refund é permitido em 30 dias."
Chunk 2: "Refund é permitido em 30 dias. Produto deve estar novo."
Chunk 3: "Produto deve estar novo. Sem marcas de uso..."
```

**Entrada:** Lista de documentos
**Saída:** Lista de chunks

---

#### **3.1.3 Embedding Generator**
**O quê:** Converte texto em vetor numérico (embedding)
**Modelo:** OpenAI text-embedding-3-small
**Dimensões:** 1536 números por embedding

**Conceito - Por que embeddings?**
- Texto não é computável diretamente
- Embedding captura "significado" do texto em números
- Textos similares têm embeddings similares (geometricamente próximos)

**Exemplo:**
```
"Qual é o prazo de refund?"
→ [0.123, -0.456, 0.789, ..., 0.234] (1536 números)

"Refund em 30 dias"
→ [0.125, -0.454, 0.791, ..., 0.232] (1536 números)
→ SIMILARES! (distância pequena)

"Qual é o horário de funcionamento?"
→ [0.900, 0.100, -0.200, ..., 0.500] (1536 números)
→ DIFERENTE (distância grande)
```

**Entrada:** Chunks de texto
**Saída:** Vetores (1536-dim cada)

---

#### **3.1.4 Vector Store (FAISS)**
**O quê:** Banco de dados otimizado para busca por similaridade
**Tech:** Facebook AI Similarity Search
**Por quê FAISS:**
- Ultra rápido (busca em milissegundos)
- Suporta milhões de vetores
- Open source + gratuito

**Operações:**
- `add`: Adicionar vetores ao índice
- `similarity_search`: Buscar K vizinhos mais próximos

**Armazenamento:**
```
FAISS Index
├─ Vector 1: [0.123, -0.456, ..., 0.234] → Chunk 1
├─ Vector 2: [0.125, -0.454, ..., 0.232] → Chunk 2
├─ Vector 3: [0.900, 0.100, ..., 0.500] → Chunk 3
└─ ... (N vetores)
```

**Entrada:** Embeddings + Chunks
**Saída:** Índice persistido (arquivo .pkl)

---

#### **3.1.5 Retriever**
**O quê:** Busca chunks relevantes dado uma pergunta
**Processo:**
1. Embed pergunta
2. Calcular similaridade com todos os chunks
3. Retornar Top-K (ex: top-3)

**Exemplo:**
```
Pergunta: "Posso devolver em 45 dias?"
Embedding: [0.122, -0.455, 0.788, ...]

Busca no FAISS:
├─ Chunk "Refund em 30 dias..." → Score: 0.95 ✅
├─ Chunk "Produto novo..." → Score: 0.87
├─ Chunk "Sem marcas..." → Score: 0.82
└─ Chunk "Horários..." → Score: 0.12

Top-3 selecionados para o LLM
```

**Entrada:** Pergunta do usuário
**Saída:** Top-K chunks com score

---

#### **3.1.6 Prompt Engineering**
**O quê:** Construir instrução clara para o LLM
**Template:**
```
You are a helpful support assistant.
Answer questions based ONLY on the provided context.
If you don't know, say "Não tenho informação sobre isso."

Context:
{chunks aqui}

Question: {pergunta do usuário}

Answer:
```

**Entrada:** Chunks + Pergunta
**Saída:** Prompt formatado

---

#### **3.1.7 LLM (OpenAI)**
**O quê:** Gera resposta baseada em prompt
**Modelo:** gpt-3.5-turbo ou gpt-4
**Parâmetros:**
- `temperature=0.3` → Respostas mais determinísticas
- `max_tokens=500` → Limite de tamanho

**Entrada:** Prompt
**Saída:** Texto da resposta

---

#### **3.1.8 FastAPI**
**O quê:** Expõe RAG como API REST
**Endpoints:**
- `POST /chat` → Fazer pergunta
- `GET /health` → Verificar saúde
- `POST /upload` → Adicionar novo documento

**Entrada:** Requisições HTTP
**Saída:** JSON com resposta

---

### 3.2 Fluxo Detalhado da Pergunta

```
1. RECEBER PERGUNTA
   └─ Usuário: "Posso devolver um produto?"
      ↓
2. VALIDAR
   └─ Verificar length, caracteres especiais
      ↓
3. EMBED PERGUNTA
   └─ Converter em vetor (1536 dim)
      ↓
4. RETRIEVAL
   └─ Buscar Top-3 chunks similares no FAISS
      ├─ Chunk A: "Refund em 30 dias" (score: 0.95)
      ├─ Chunk B: "Produto deve estar novo" (score: 0.87)
      └─ Chunk C: "Embalagem intacta" (score: 0.82)
      ↓
5. BUILD PROMPT
   └─ "Use estes trechos: [A, B, C]. Pergunta: ..."
      ↓
6. CALL LLM
   └─ OpenAI API recebe prompt
      ↓
7. GERAR RESPOSTA
   └─ LLM processa e retorna texto
      ↓
8. RETORNAR
   └─ "Sim, você pode devolver em 30 dias desde que..."
```

---

## 4. Estrutura de Dados

### 4.1 Input Documents
```json
{
  "source": "politica.pdf",
  "page": 1,
  "content": "Refund em 30 dias após compra..."
}
```

### 4.2 Chunks
```json
{
  "chunk_id": "chunk_0001",
  "content": "Refund em 30 dias após compra",
  "source": "politica.pdf",
  "page": 1
}
```

### 4.3 Embeddings
```json
{
  "chunk_id": "chunk_0001",
  "embedding": [0.123, -0.456, 0.789, ..., 0.234],
  "dimension": 1536
}
```

### 4.4 Retrieval Results
```json
{
  "chunk_id": "chunk_0001",
  "content": "Refund em 30 dias...",
  "similarity_score": 0.95,
  "source": "politica.pdf"
}
```

### 4.5 Chat Response
```json
{
  "question": "Posso devolver?",
  "answer": "Sim, em 30 dias...",
  "sources": ["politica.pdf:page1"],
  "confidence": 0.92
}
```

---

## 5. Considerações de Performance

### 5.1 Velocidade Esperada
```
Setup (one-time):
├─ Load documentos: 5-10s
├─ Embedding: 1-5s (depende do tamanho)
└─ Indexing: <1s

Query (per pergunta):
├─ Embed pergunta: 0.5-1s
├─ Retrieval: <10ms (FAISS é muito rápido)
├─ LLM call: 1-3s
└─ Total: ~2-4s
```

### 5.2 Limite de Documentos
- Início: até 100 docs (~1000 chunks) ✅
- Escala: com FAISS otimizado, suporta milhões de vetores

### 5.3 Custo (OpenAI API)
```
Embedding: $0.02 / 1M tokens
Completion: $0.5-$3 / 1M tokens (depende do modelo)

Exemplo (10k perguntas/mês):
~$5-15/mês (bem barato)
```

---

## 6. Qualidade de Respostas

### 6.1 Fatores que Afetam
1. **Qualidade dos chunks** → Split bem feito = melhor retrieval
2. **Embeddings** → OpenAI é excelente
3. **Relevância dos trechos** → FAISS encontra os melhores
4. **Prompt engineering** → Instruções claras ao LLM
5. **Modelo LLM** → GPT-4 > GPT-3.5

### 6.2 Métricas de Avaliação
- **Precision:** Respostas relevantes / Total de respostas
- **Recall:** Respostas encontradas / Total relevantes
- **User satisfaction:** Pesquisa com usuários
- **Response time:** Latência da API

### 6.3 Melhorias Possíveis
```
v1.0: RAG básico
  ↓
v1.1: Adicionar feedback do usuário (thumbs up/down)
  ↓
v1.2: Fine-tuning do modelo
  ↓
v1.3: Múltiplas fontes (FAQ + docs + logs)
  ↓
v2.0: Conversação (histórico de chat)
```

---

## 7. Segurança e Privacidade

### 7.1 Dados Sensíveis
- Documentos são armazenados localmente (não em cloud)
- Embeddings são desvinculados do texto original
- Respostas não incluem identificadores pessoais

### 7.2 Autenticação
```
POST /chat
Headers: Authorization: Bearer {token}
```

### 7.3 Rate Limiting
```
Max 100 requests/min por usuário
Max 1000 requests/hora por organização
```

---

## 8. Casos de Uso

### 8.1 Suporte Técnico
```
Doc: Manual de instalação software X
Pergunta: "Como instalo a versão 2.0?"
Resposta: Usa guia de instalação baseado no documento
```

### 8.2 Recursos Humanos
```
Doc: Políticas da empresa (férias, benefícios, dress code)
Pergunta: "Quanto de férias tenho direito?"
Resposta: Extrai da política exata
```

### 8.3 Vendas
```
Doc: FAQ produtos, preços, promoções
Pergunta: "Qual desconto para compra em bulk?"
Resposta: Busca na base de vendas
```

### 8.4 Legal
```
Doc: Termos de serviço, contratos
Pergunta: "Qual é a cláusula de cancelamento?"
Resposta: Encontra no documento legal
```

---

## 9. Stack Tecnológico Final

```
Backend:
├─ Python 3.10+
├─ FastAPI (REST API)
├─ LangChain (Orquestração)
├─ FAISS (Vector Store)
├─ OpenAI API (LLM + Embeddings)
└─ Pydantic (Validação)

Deployment:
├─ Docker (Containerização)
├─ Railway (Hospedagem Backend)
├─ PostgreSQL (Metadados)
└─ GitHub Actions (CI/CD)

Frontend:
├─ React/Vue (Web)
├─ Mobile (Flutter/React Native)
└─ Slack Bot (Integração)
```

---

## 10. Roadmap de Desenvolvimento

### **Fase 1: MVP (v0.1) - Semana 1**
- [ ] Setup FastAPI + LangChain
- [ ] Documento único (TXT)
- [ ] Embed + FAISS
- [ ] Endpoint `/chat` básico
- [ ] Testes unitários

### **Fase 2: v1.0 - Semana 2**
- [ ] Suporte a PDFs
- [ ] Múltiplos documentos
- [ ] Interface web básica
- [ ] Melhorar prompts
- [ ] Logging e monitoring

### **Fase 3: v1.5 - Semana 3**
- [ ] Histórico de conversas
- [ ] Feedback do usuário
- [ ] Analytics (perguntas mais comuns)
- [ ] Testes E2E
- [ ] Docker + Deploy

### **Fase 4: v2.0+ - Future**
- [ ] Fine-tuning de modelos
- [ ] Integração com sistemas internos
- [ ] Multi-idioma
- [ ] Video + áudio input
- [ ] Integração Slack/Teams

---

## Conclusão

Este sistema RAG combina o melhor de dois mundos:
- **Documentos precisos** via retrieval baseado em similaridade
- **Respostas inteligentes** via LLMs

Resultado: Chatbot que responde com precisão, contexto e sem alucinações.

