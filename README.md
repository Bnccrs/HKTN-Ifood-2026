# 🥗 IFit Agent — Copiloto Nutricional Autônomo com iFood MCP & Gemini CLI

![IFit Logo](IFit-Logo.png)

Um agente autônomo de inteligência artificial que converte metas de saúde (calorias, macronutrientes e restrições alimentares) em opções reais de refeições no iFood. O sistema combina o raciocínio analítico do **Google Gemini** (via **Gemini CLI**) com a estrutura de integração do **Model Context Protocol (MCP)** do Ifood e uma interface multimodal em **Streamlit** com suporte a voz e texto.

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

O agente processa o pedido do usuário através de um fluxo ponta a ponta que conecta voz, processamento de linguagem natural e o catálogo real do iFood.

```text
[Usuário (Voz/Texto)]
         │
         ▼
[Interface Streamlit (app.py)] ──(STT via voice.py)──► [Texto do Usuário]
                                                              │
                                                              ▼
[Seletor de Agente (agent/mock.py → send_message)] ◄──────────┘
         │
         ├─► AGENT_ENGINE=gemini ─► [Gemini CLI (agent/gemini_cli.py)]
         │                                  │  GEMINI.md + agent/web-instructions.md
         │                                  │  Política: agent/web-policy.toml
         │                                  ▼
         │                          [iFood MCP] (busca de pratos e carrinho real)
         │
         ├─► AGENT_API_URL ───────► [Backend externo] (POST /chat, mesmo contrato)
         │
         └─► (padrão) ────────────► [Agente simulado] (regras locais + catálogo de data.py)
                     │
                     ▼
[Resposta Estruturada (texto + opções + carrinho)]
         │
         ├─► Resposta curta falada (TTS via gTTS)
         ├─► 3 a 4 Cards de opções + justificativa nutricional
         ├─► Atualização do Perfil (modo simulado)
         └─► Carrinho do iFood montado pelo agente (modo Gemini)
```

### Fluxo Geral da Solução:
1. **Entrada Multimodal:** O usuário envia uma mensagem por áudio ou texto. Em caso de áudio, `voice.py` transcreve com *SpeechRecognition* (Google, padrão) ou *Whisper* da OpenAI (`STT_ENGINE=openai`).
2. **Orquestração e Raciocínio (Gemini CLI):** O `app.py` chama o agente diretamente, no mesmo processo. No modo Gemini, cada mensagem vira uma chamada *headless* ao Gemini CLI, que carrega o `GEMINI.md` (persona e regras nutricionais) e as instruções do site. A memória da conversa fica na sessão do próprio CLI (`--resume <session_id>`).
3. **Consulta ao Catálogo (iFood MCP):** O agente busca pratos, restaurantes, preços e tempos de entrega reais pelo MCP do iFood e estima os macronutrientes com base nas tabelas TACO/TBCA/USDA. Sem o Gemini, o agente simulado usa o catálogo fictício de `data.py`.
4. **Devolutiva ao Usuário:** O agente termina a resposta com um bloco ` ```ifit ` em JSON (opções e carrinho), que o site extrai para renderizar os cards. O texto restante é exibido no chat e lido em voz via TTS (*gTTS*).

---

## 03. Racional da Experiência (UX)

* **Voz em Primeiro Lugar (Voice-First):** Fazer um pedido por voz reduz o atrito e permite uma conversação natural, simulando uma consulta rápida com um nutricionista.
* **Explicabilidade Nutricional (Por que este prato?):** Cada refeição recomendada exibe a justificativa clara da escolha (ex: *"45g de proteína e 520 kcal por R$ 32,90"*). Os macros são estimativas do agente (TACO/TBCA/USDA), sinalizadas com nota de incerteza quando necessário.
* **Perfil Vivo e Transparente:** No modo simulado, as preferências extraídas aparecem em tags visuais (Restrições, Objetivos, Gostos, Não gosta, Orçamento) na barra lateral. No modo Gemini, o perfil é mantido pelo próprio agente ao longo da conversa.
* **Usuário no Controle do Pedido:** O agente apenas monta o carrinho no iFood após confirmação explícita. Finalizar pedido, pagamento, cupons e endereços ficam bloqueados pela política do site e devem ser feitos no app do iFood.
* **Visibilidade dos Processos da IA (Tool Calls Log):** A barra lateral expõe o log das chamadas de ferramentas e pesquisas realizadas pelo agente, construindo confiança e transparência.

---

## 04. Interface Visual

A interface web foi desenvolvida em **Streamlit**, organizada para garantir clareza e agilidade na tomada de decisão:

| Componente | Função e Detalhes da Experiência |
| :--- | :--- |
| **Painel de Conversação (Esquerda)** | Chat interativo, gravador de áudio (`st.audio_input`), reprodutor automático de voz do agente e sugestões rápidas em 1 clique. |
| **Vitrine de Opções (Direita)** | Até 4 cards com foto, preço, tempo de entrega, macros e motivo da escolha; a opção #1 ganha borda vermelha iFood. O botão "Adicionar" confirma a opção com o agente (modo Gemini) ou a coloca no carrinho local (modo simulado). |
| **Barra Lateral** | Carrinho (do iFood ou local), perfil do usuário, liga/desliga da voz, "Nova conversa" e log das tool calls. |

---


## 05. Documento Técnico Resumido

### Arquitetura do Sistema
* **Frontend:** Streamlit 1.40+ (`app.py`) responsável pela captura multimodal, renderização de cards e gerenciamento do estado da sessão (`st.session_state`).
* **Camada do Agente:** `agent/mock.py` define o contrato da resposta e escolhe o motor: Gemini CLI (`AGENT_ENGINE=gemini`), backend externo (`AGENT_API_URL`) ou agente simulado local.
* **Engine de IA:** [Gemini CLI](https://github.com/google-gemini/gemini-cli) com o modelo `gemini-3.5-flash-lite` (`temperature=0.7`), configurado em `.gemini/settings.json` e `GEMINI.md`.
* **Integração iFood:** servidor MCP `consumer-mcp.ifood.com.br` com OAuth. A política `agent/web-policy.toml` libera apenas as ferramentas do iFood e bloqueia web search, shell, arquivos e finalização de pedidos.
* **Dados Simulados:** `data.py` contém um catálogo fictício de restaurantes e pratos usado pelo agente simulado.
* **Processamento de Áudio:** `speech_recognition` / `soundfile` (ou Whisper da OpenAI) para transcrição (STT) e `gTTS` para síntese falada (TTS).

### Decisões Técnicas Principais
1. **Gemini CLI como Orquestrador:** O CLI já oferece suporte nativo a MCP, OAuth, políticas de ferramentas e memória de sessão, dispensando um backend próprio.
2. **Saída Estruturada via Bloco ```ifit```:** O agente responde em texto e anexa um JSON com as opções e o carrinho, extraído pelo site para renderizar os cards. Se o bloco vier inválido, a conversa continua e apenas os cards não são atualizados.
3. **Agente Plugável:** O contrato único de `send_message` permite trocar o motor (simulado, Gemini CLI ou um backend `/chat` externo) sem alterar a interface, viabilizando integrações futuras com apps mobile ou WhatsApp.

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
npm i -g @google/gemini-cli   # necessário só para o modo Gemini

# 4. Configure o arquivo de ambiente (.env)
cp .env.example .env
# AGENT_ENGINE=gemini  -> usa o Gemini CLI + iFood MCP (preencha IFOOD_MCP_CLIENT_ID e IFOOD_MCP_CLIENT_SECRET)
# AGENT_ENGINE vazio   -> usa o agente simulado com dados fictícios (sem chaves)
# No modo Gemini, adicione também GEMINI_API_KEY=<sua chave> ao .env (repassada ao Gemini CLI)

# 5. Inicie a aplicação
streamlit run app.py
```

Variáveis opcionais (`.env.example`): `GEMINI_MODEL`, `GEMINI_TIMEOUT`, `GEMINI_BIN`, `STT_ENGINE` (`google` ou `openai` + `OPENAI_API_KEY`) e `AGENT_API_URL` (usa um backend externo `/chat` no lugar dos agentes locais).
