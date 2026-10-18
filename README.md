# 🥗 IFit Agent — Copiloto Nutricional Autônomo com iFood MCP & Gemini API

![LOGO](IFit-Logo.png)

Um agente autônomo de inteligência artificial que converte metas de saúde (calorias, macronutrientes e restrições alimentares) em opções reais de refeições no iFood. O sistema combina o raciocínio analítico do **Google Gemini API** com a integração em tempo real do **Model Context Protocol (MCP)**.

---

## 🚀 O Problema
A grande maioria das opções nos cardápios de delivery não apresenta tabela nutricional ou contagem clara de calorias e proteínas. Pessoas focadas em reeducação alimentar, dietas específicas ou rotina fitness perdem tempo tentando estimar manualmente a composição nutricional de cada prato.

---

## 💡 A Solução
O **NutriFood Agent** atua como um nutricionista autônomo:
1. Recebe a meta do usuário em linguagem natural (ex: *"Quero um almoço pós-treino com pelo menos 45g de proteína, pouca gordura e gastando até R$ 50"*).
2. Consulta opções reais de restaurantes locais diretamente na API do iFood por meio do **iFood MCP Server**.
3. O **Gemini** analisa as descrições dos ingredientes, estima a divisão de macronutrientes (calorias, proteínas, carboidratos e gorduras) e filtra os pratos que atendem aos critérios.
4. O agente entrega as **3 melhores opções de refeição** justificando a escolha e exibindo valores, preços e macros estimados.

---

## 🛠️ Tech Stack
- **AI Engine / LLM:** Google Gemini API (`gemini-2.0`)
- **Protocolo de Ferramentas:** Model Context Protocol (MCP SDK)
- **Integração de Dados:** iFood Merchant / Catalog API (OAuth 2.0 Client Credentials)
- **Backend / Orquestrador:** Python
- **Interface:** React

---

## 🔄 Arquitetura do Agente

---
