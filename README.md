# Briefr 📋

Gerador inteligente de propostas comerciais com busca na web, geração via IA e exportação em PDF.

## Como usar

### 1. Instalar dependências
```bash
pip install -r requirements.txt
```

### 2. Executar
```bash
streamlit run app.py
```

### 3. Configurar
- Insira sua **OpenRouter API Key** (gratuita em [openrouter.ai](https://openrouter.ai))
- Escolha o modelo (Mistral 7B e Llama 3 8B são gratuitos!)
- Preencha os dados do projeto e clique em **Gerar Proposta**

## Fluxo do app

```
Briefing do projeto
       ↓
Busca automática na web (DuckDuckGo)
       ↓
Geração da proposta com IA (OpenRouter)
       ↓
Exportação em PDF profissional
```

## Modelos disponíveis (OpenRouter)

| Modelo | Custo |
|--------|-------|
| Mistral 7B | Gratuito |
| Llama 3 8B | Gratuito |
| Llama 3 70B | Pago |
| GPT-4o Mini | Pago |
| Claude 3 Haiku | Pago |
| Gemini Flash 1.5 | Pago |

## Stack
- **Frontend**: Streamlit
- **IA**: OpenRouter (múltiplos modelos)
- **Busca**: DuckDuckGo Search
- **PDF**: ReportLab
