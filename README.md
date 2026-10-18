# 🥗 IFit Agent — Copiloto Nutricional Autônomo com iFood MCP & Gemini API

![IFit Logo](IFit-Logo.png)

Um agente autônomo de inteligência artificial que converte metas de saúde (calorias, macronutrientes e restrições alimentares) em opções reais de refeições no iFood. O sistema combina o raciocínio analítico do **Google Gemini API** com a estrutura de integração do **Model Context Protocol (MCP)** do Ifood e uma interface multimodal em **Streamlit** com suporte a voz e texto.

---

## 01. Proposta de Negócio

### O Problema
A grande maioria das opções nos cardápios de delivery não apresenta tabela nutricional padronizada ou contagem clara de calorias e macronutrientes (proteínas, carboidratos e gorduras). Pessoas focadas em reeducação alimentar, dietas específicas (low carb, ganho de massa) ou com restrições severas (intolerância à lactose, celíacos, veganos) perdem tempo tentando estimar manualmente a composição de cada prato.

### A Proposta de Valor
O **IFit Agent** atua como um nutricionista autônomo integrado ao fluxo do iFood:
* **Tradução de Metas em Pratos Reais:** O usuário expressa sua necessidade em linguagem natural (voz ou texto) e o agente traduz em recomendações concretas de refeições disponíveis para entrega.
* **Personalização Dinâmica:** Aprende e mantém atualizado o perfil do usuário (orçamento, gostos, aversões e restrições) em tempo real a cada interação.
* **Agilidade na Decisão:** Reduz o tempo de escolha de ~15 minutos navegando em cardápios para menos de 10 segundos com indicações direcionadas, quantificadas e justificadas.

---

## 02. Desenho de Solução

O agente processa o pedido do usuário através de um fluxo ponta a ponta que conecta voz, processamento de linguagem natural e banco de dados nutricional.

```text
[Usuário (Voz/Texto)] 
         │
         ▼
[Interface Streamlit (app.py)] ──(STT Transcrição)──► [Texto do Usuário]
                                                              │
                                                              ▼
[FastAPI Backend (server.py)] ◄───────────────────────────────┘
         │
         ├─► [Google Gemini Flash] (System Prompt + JSON Schema)
         │           │
         │           ▼ (Análise, Extração de Preferências e Ranking)
         │
         └─► [Base de Dados / iFood MCP Catalog] (Cross de Pratos e Restaurantes)
                     │
                     ▼
[Resposta Estruturada em JSON]
         │
         ├─► Atualização do Perfil (Restrições, Metas, Orçamento)
         ├─► Resposta Curta para Voz (TTS via gTTS)
         └─► Top 3 Cards Recomendados + Explicabilidade Nutricional
         └─► Opção de adicionar à Sacola de Compras do usuário
```

### Fluxo Geral da Solução:
1. **Entrada Multimodal:** O usuário envia uma mensagem por áudio ou texto. Em caso de áudio, o motor STT (*SpeechRecognition*) realiza a transcrição.
2. **Orquestração e Raciocínio (Gemini Flash):** O backend FastAPI recebe a mensagem, o histórico recente e o perfil atual. O modelo executa o prompt com um *System Instruction* rigoroso que força a saída em formato JSON estruturado.
3. **Consulta ao Catálogo (MCP):** O agente cruza os critérios nutricionais estimados com os pratos cadastrados no catálogo do iFood (macros, tags de restrição, preços e restaurantes).
4. **Devolutiva ao Usuário:** A interface exibe a mensagem no chat, sintetiza a voz de resposta do agente via TTS (*gTTS*), atualiza o perfil visual na barra lateral e renderiza os cards de recomendação com botões de compra.

---

## 03. Racional da Experiência (UX)

* **Voz em Primeiro Lugar (Voice-First):** Fazer um pedido por voz reduz o atrito e permite uma conversação natural, simulando uma consulta rápida com um nutricionista.
* **Explicabilidade Nutricional (Por que este prato?):** Cada refeição recomendada exibe um selo destacado contendo a justificativa clara da escolha (ex: *"45g de proteína e 520 kcal por R$ 32,90"*).
* **Perfil Vivo e Transparente:** O usuário acompanha em tempo real suas preferências sendo extraídas e organizadas em tags visuais (Restrições, Objetivos, Gostos, Orçamento) na barra lateral.
* **Visibilidade dos Processos da IA (Tool Calls Log):** A barra lateral expõe o log das chamadas de ferramentas e pesquisas realizadas pelo agente, construindo confiança e transparência.

---

## 04. Interface Visual

A interface web foi desenvolvida em **Streamlit**, organizada para garantir clareza e agilidade na tomada de decisão:

| Componente | Função e Detalhes da Experiência |
| :--- | :--- |
| **Painel de Conversação (Esquerda)** | Chat interativo, gravador de áudio (`st.audio_input`), reprodutor automático de voz do agente e sugestões rápidas em 1 clique. |
| **Vitrine Inteligente (Direita)** | Painel com os **"⭐ Recomendados para você"** em destaque visual (borda vermelha iFood, badges de macros e botão de adição ao carrinho), seguido pelo cardápio filtrável. |

---


## 05. Documento Técnico Resumido

### Arquitetura do Sistema
* **Frontend:** Streamlit 1.40+ (`app.py`) responsável pela captura multimodal, renderização de cards e gerenciamento do estado da sessão (`st.session_state`).
* **Backend:** FastAPI + Uvicorn (`server.py`) servindo o endpoint de alto desempenho `/chat`.
* **Engine de IA:** `google-genai` utilizando o modelo `gemini-2.0-flash`, configurado com `GenerateContentConfig` para imposição de `response_mime_type="application/json"` e `temperature=0.2`.
* **Processamento de Áudio:** `speech_recognition` / `soundfile` para transcrição (STT) e `gTTS` para síntese falada (TTS).

### Decisões Técnicas Principais
1. **Baixa Latência com Gemini 2.0 Flash:** Tempo de resposta reduzido (< 1s), fundamental para manter a fluidez de interações conversacionais por voz.
2. **Schema Rígido via JSON Output:** Garantia de que a LLM retorne um payload previsível, evitando erros de sintaxe e assegurando a sincronização do perfil do usuário e dos cards.
3. **Desacoplamento (Frontend/Backend):** Separação estrita entre a API do agente (`server.py`) e a interface visual (`app.py`), viabilizando integrações futuras com apps mobile ou WhatsApp.

---

## 06. Feedback sobre os MCPs (iFood MCP)

Durante a integração e simulação do Model Context Protocol (MCP) do iFood, o time identificou oportunidades cruciais de evolução para o ecossistema de desenvolvedores:

1. **Padronização de Dados Nutricionais nos Cardápios:**
   * *Desafio:* A maioria dos restaurantes fornece apenas nome e descrição comercial do prato no catálogo.
   * *Oportunidade:* Expandir o schema do MCP do iFood para aceitar campos opcionais padronizados como `kcal`, `protein`, `carbs`, `fat` e `allergens` diretamente no cadastro de itens.
2. **Consultas com Filtros Semânticos/Nutricionais no Servidor MCP:**
   * *Desafio:* Enviar catálogos inteiros de restaurantes para a LLM gera latência extra e consumo excessivo de tokens.
   * *Oportunidade:* Criar ferramentas nativas no servidor MCP que permitam queries filtradas (ex: `search_dishes_by_nutrition(min_protein=40, max_price=50)`), retornando apenas os itens relevantes para o contexto do agente.
3. **Persistência de Contexto do Usuário no Protocolo:**
   * *Desafio:* Atualmente, todo o histórico de preferências precisa ser gerenciado e repassado pela aplicação cliente.
   * *Oportunidade:* Incorporar suporte a "Memória do Perfil do Usuário" no MCP, permitindo que restrições alimentares permanentes fiquem vinculadas ao token de usuário.

---

## ⚙️ Como Executar o Projeto

```bash
# 1. Clone o repositório
git clone https://github.com/Bnccrs/HKTN-Ifood-2026.git
cd HKTN-Ifood-2026

# 2. Crie e ative o ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt
pip install fastapi uvicorn google-genai

# 4. Configure o arquivo de ambiente (.env)
cp .env.example .env
# Insira sua GEMINI_API_KEY no arquivo .env

# 5. Inicie a API do Backend
python server.py

# 6. Em outro terminal (com o venv ativo), inicie o Frontend
streamlit run app.py
```