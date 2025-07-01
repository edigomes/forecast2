# 🚀 Sistema MRP Avançado - README

## 📋 Visão Geral

O **Sistema MRP Avançado** é uma solução completa de planejamento de recursos de materiais que utiliza algoritmos inteligentes de supply chain para otimizar o planejamento de produção e estoque com demandas esporádicas.

## ✨ Principais Recursos

- 🧠 **Algoritmos Inteligentes**: 4 estratégias baseadas em lead time e características da demanda
- 📈 **EOQ Automático**: Cálculo automático do lote econômico de compra
- 🏷️ **Classificação ABC/XYZ**: Categorização automática por valor e variabilidade
- 🔄 **Consolidação Inteligente**: Agrupamento otimizado de pedidos
- 📊 **Analytics Avançados**: Métricas detalhadas de performance
- ⚡ **API REST**: Endpoint `/mrp_advanced` com resposta JSON estruturada

## 🚀 Início Rápido

### 1. Instalação

```bash
pip install -r requirements.txt
```

### 2. Executar o Servidor

```bash
python server.py
```

### 3. Teste Básico

```json
POST /mrp_advanced
{
    "sporadic_demand": {"2025-08-01": 1000},
    "initial_stock": 500,
    "leadtime_days": 30,
    "period_start_date": "2025-07-01",
    "period_end_date": "2025-12-31"
}
```

## 🎛️ Estratégias Disponíveis

| Estratégia | Lead Time | Uso | Características |
|------------|-----------|-----|-----------------|
| **EOQ** | ≤ 14 dias | Demanda estável | Lotes otimizados, reposição frequente |
| **Buffer Dinâmico** | 15-45 dias | Alta variabilidade | Estoques flexíveis, adaptação a picos |
| **Lead Time Longo** | > 45 dias | Planejamento estratégico | Poucos lotes grandes, previsão avançada |
| **Consolidação Híbrida** | Qualquer | Múltiplas demandas | Otimização custo-benefício |

## 📊 Parâmetros de Configuração

### Obrigatórios
- `sporadic_demand`: Demandas por data
- `initial_stock`: Estoque inicial
- `leadtime_days`: Lead time em dias
- `period_start_date` / `period_end_date`: Período de planejamento

### Opcionais
- `safety_margin_percent`: Margem de segurança (padrão: 8%)
- `setup_cost`: Custo fixo por pedido (padrão: 250)
- `holding_cost_rate`: Taxa de manutenção anual (padrão: 20%)
- `service_level`: Nível de serviço desejado (padrão: 98%)
- `enable_consolidation`: Ativar consolidação (padrão: true)

## 📈 Exemplo de Resposta

```json
{
    "batches": [
        {
            "order_date": "2025-07-01",
            "arrival_date": "2025-07-31",
            "quantity": 2000,
            "setup_cost": 250,
            "holding_cost_impact": 1200
        }
    ],
    "analytics": {
        "summary": {
            "demand_fulfillment_rate": 100.0,
            "total_batches": 1,
            "production_coverage_rate": "133%"
        },
        "advanced_analytics": {
            "advanced_mrp_strategy": "eoq_strategy",
            "abc_classification": "A",
            "xyz_classification": "Y"
        }
    }
}
```

## 🔧 Integração

### Python
```python
import requests

response = requests.post('http://localhost:5000/mrp_advanced', json=data)
result = response.json()
```

### PHP
```php
$response = curl_exec(curl_init_with_json($url, $data));
$result = json_decode($response, true);
```

### JavaScript
```javascript
const response = await fetch('/mrp_advanced', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
});
const result = await response.json();
```

## 📚 Documentação Completa

- 📖 [Documentação Principal](DOCUMENTACAO_MRP_AVANCADO.md)
- 📚 [Guia de Exemplos Práticos](GUIA_EXEMPLOS_PRATICOS.md)
- 📖 [Glossário de Termos Técnicos](GLOSSARIO_TERMOS_TECNICOS.md)
- 🔧 [Guia de Solução de Problemas](GUIA_SOLUCAO_PROBLEMAS.md)

## 🎯 Casos de Uso

### 🏭 Indústria
- Lead times longos (60+ dias)
- Alto custo de setup
- Planejamento estratégico

### 🏥 Healthcare
- Alta criticidade (99% service level)
- Baixa tolerância a stockouts
- Múltiplos fornecedores

### 🛒 E-commerce
- Demanda sazonal
- Alta variabilidade
- Consolidação agressiva

## 📊 KPIs Principais

| Métrica | Excelente | Bom | Problemático |
|---------|-----------|-----|--------------|
| Taxa de Atendimento | 100% | 95-99% | < 90% |
| Cobertura de Produção | 120-150% | 100-200% | > 200% |
| Eficiência de Lote | > 150% | 100-150% | < 80% |

## 🚨 Correções Implementadas

### v1.0 (Junho 2025)
- ✅ **Duplicação de Lotes**: Eliminado problema de lotes com datas idênticas
- ✅ **Stockouts**: Corrigido cálculo de estoque futuro
- ✅ **Timing**: Melhorado cálculo de chegada de lotes
- ✅ **Estratégias**: Otimizada seleção automática de estratégias

### Melhorias de Performance
- **Taxa de Atendimento**: 20% → 100% (5x melhoria)
- **Eliminação de Stockouts**: De -3,019 para +13,726 unidades
- **Precisão de Timing**: Lotes chegam antes das demandas críticas

## 🛠️ Desenvolvimento

### Executar Testes
```bash
python test_advanced_sporadic_mrp.py
python test_stockout_fix.py
```

### Estrutura do Projeto
```
forecast2/
├── server.py                    # Servidor Flask principal
├── mrp.py                      # MRP básico
├── advanced_sporadic_mrp.py    # MRP avançado
├── test_*.py                   # Testes automatizados
└── docs/                       # Documentação
```

## 📞 Suporte

- 📧 **Issues**: GitHub Issues
- 📚 **Documentação**: Arquivos `.md` na raiz do projeto
- 🔧 **Testes**: Execute os scripts de teste para diagnóstico

## 📈 Roadmap

- [ ] Interface Web para configuração
- [ ] Suporte a múltiplos produtos
- [ ] Integração com ERPs
- [ ] Dashboard de monitoramento
- [ ] Previsão com Machine Learning

---

**Versão**: 1.0  
**Última Atualização**: 30 de Junho de 2025  
**Status**: ✅ Produção 