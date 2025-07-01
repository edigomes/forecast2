# 📖 Glossário de Termos Técnicos - Sistema MRP Avançado

## 🎯 Termos Fundamentais

### **MRP** (Material Requirements Planning)
Sistema de planejamento de necessidades de materiais que calcula quando e quanto produzir/comprar baseado na demanda futura.

### **Demanda Esporádica**
Demanda irregular, não constante, que ocorre em intervalos específicos e com quantidades variáveis.

### **Lead Time**
Tempo total entre o pedido de um item e sua chegada/disponibilidade no estoque.

### **Safety Stock** (Estoque de Segurança)
Quantidade extra mantida em estoque para proteger contra variações na demanda ou no lead time.

### **Stockout**
Situação onde o estoque é insuficiente para atender a demanda, resultando em saldo negativo.

---

## 📊 Algoritmos e Métodos

### **EOQ** (Economic Order Quantity)
**Definição**: Quantidade ótima de pedido que minimiza o custo total de estoque.
**Fórmula**: `√(2 × Demanda Anual × Custo de Setup) / Custo de Manutenção`
**Uso**: Estratégia para lead times curtos e demanda estável.

### **Classificação ABC**
**Definição**: Método de categorização de itens por valor/importância:
- **Classe A**: 70-80% do valor total (alta prioridade)
- **Classe B**: 15-25% do valor total (prioridade média)
- **Classe C**: 5-10% do valor total (baixa prioridade)

### **Classificação XYZ**
**Definição**: Categorização por variabilidade/previsibilidade da demanda:
- **Classe X**: Baixa variabilidade (CV < 0.2)
- **Classe Y**: Variabilidade média (CV 0.2-0.5)
- **Classe Z**: Alta variabilidade (CV > 0.5)

### **Consolidação Inteligente**
**Definição**: Agrupamento de múltiplos pedidos para reduzir custos de setup e melhorar eficiência operacional.
**Benefícios**: Economia de escala, redução de complexidade, otimização de recursos.

---

## 🎛️ Estratégias de Planejamento

### **Estratégia EOQ**
**Quando Usar**: Lead times ≤ 14 dias, demanda relativamente estável
**Características**:
- Lotes otimizados economicamente
- Reposição frequente
- Foco na eficiência de custos

### **Estratégia de Buffer Dinâmico**
**Quando Usar**: Alta variabilidade na demanda (CV > 0.5)
**Características**:
- Estoques de segurança aumentados
- Flexibilidade para picos
- Monitoramento contínuo

### **Estratégia de Lead Time Longo**
**Quando Usar**: Lead times > 45 dias
**Características**:
- Poucos lotes grandes
- Planejamento estratégico
- Previsão avançada

### **Estratégia de Consolidação Híbrida**
**Quando Usar**: Múltiplas demandas próximas, custos de setup altos
**Características**:
- Otimização custo-benefício
- Prevenção de sobreposição
- Eficiência operacional

---

## 📈 Métricas de Performance

### **Taxa de Atendimento** (Demand Fulfillment Rate)
**Definição**: Percentual de demandas atendidas sem stockout
**Fórmula**: `(Demandas Atendidas / Total de Demandas) × 100`
**Meta**: ≥ 95%

### **Taxa de Cobertura de Produção** (Production Coverage Rate)
**Definição**: Percentual da produção total em relação à demanda total
**Fórmula**: `(Produção Total / Demanda Total) × 100`
**Ideal**: 120-150%

### **Eficiência de Lote** (Batch Efficiency)
**Definição**: Medida de otimização do tamanho dos lotes
**Fórmula**: `(Produção Efetiva / Produção Planejada) × 100`
**Meta**: > 100%

### **Compliance de Lead Time**
**Definição**: Percentual de lotes que respeitam o lead time estabelecido
**Meta**: 100%

---

## 💰 Termos Financeiros

### **Custo de Setup**
**Definição**: Custo fixo para iniciar uma produção ou fazer um pedido
**Inclui**: Preparação de máquinas, trâmites burocráticos, logística
**Impacto**: Favorecer lotes maiores quando alto

### **Taxa de Custo de Manutenção** (Holding Cost Rate)
**Definição**: Custo anual percentual para manter estoque
**Inclui**: Armazenagem, seguro, obsolescência, capital parado
**Típico**: 15-25% ao ano

### **Custo de Stockout**
**Definição**: Custo por falta de produto
**Inclui**: Vendas perdidas, clientes insatisfeitos, penalidades
**Uso**: Determinar nível de safety stock

### **Nível de Serviço** (Service Level)
**Definição**: Probabilidade de não haver stockout
**Fórmula**: `1 - (Stockouts / Total de Períodos)`
**Típico**: 95-99%

---

## 🔧 Parâmetros Técnicos

### **Margem de Segurança** (Safety Margin Percent)
**Definição**: Percentual extra adicionado aos cálculos de demanda
**Uso**: Compensar incertezas e variações
**Típico**: 5-20%

### **Dias de Segurança** (Safety Days)
**Definição**: Dias extras de buffer no planejamento
**Uso**: Proteção contra atrasos de entrega
**Típico**: 2-7 dias

### **Janela de Consolidação** (Consolidation Window)
**Definição**: Período em dias onde demandas podem ser agrupadas
**Cálculo**: Baseado no lead time e características da demanda
**Típico**: 10-30% do lead time

---

## 📊 Análises Estatísticas

### **Coeficiente de Variação** (CV)
**Definição**: Medida de variabilidade relativa
**Fórmula**: `Desvio Padrão / Média`
**Interpretação**:
- CV < 0.2: Baixa variabilidade
- CV 0.2-0.5: Variabilidade média
- CV > 0.5: Alta variabilidade

### **Z-Score**
**Definição**: Número de desvios padrão em relação à média
**Uso**: Cálculo de safety stock para níveis de serviço específicos
**Exemplos**:
- 95% serviço: Z = 1.65
- 98% serviço: Z = 2.05
- 99% serviço: Z = 2.33

### **Sazonalidade**
**Definição**: Padrão de variação regular na demanda ao longo do tempo
**Detecção**: Análise de frequência e amplitude de variações
**Ajuste**: Fatores sazonais aplicados ao planejamento

---

## 🎯 Indicadores Operacionais

### **Utilização da Linha de Produção**
**Definição**: Medida de quanto a capacidade produtiva está sendo utilizada
**Fórmula**: `Produção Efetiva / Capacidade Máxima`
**Ideal**: 80-95%

### **Gaps de Produção**
**Definição**: Intervalos entre produções
**Tipos**:
- **Normal**: Intervalo planejado
- **Idle**: Ociosidade desnecessária
- **Overlap**: Sobreposição problemática

### **Dias de Cobertura** (Days of Coverage)
**Definição**: Quantos dias o estoque atual pode atender a demanda
**Fórmula**: `Estoque Atual / Demanda Diária Média`
**Uso**: Identificar pontos críticos

---

## 🔍 Análise de Demanda

### **Concentração de Demanda**
**Definição**: Medida de como a demanda está distribuída no tempo
**Índice**: 0 (uniforme) a 1 (concentrada)
**Impacto**: Influencia estratégia de planejamento

### **Previsibilidade da Demanda**
**Definição**: Capacidade de antecipar demandas futuras
**Fatores**: Regularidade, padrões históricos, sazonalidade
**Uso**: Seleção de estratégia de planejamento

### **Análise de Picos**
**Definição**: Identificação de demandas excepcionalmente altas
**Métricas**:
- Ratio de pico (pico/média)
- Frequência de picos
- Duração dos picos

---

## 🛠️ Configurações Avançadas

### **Lote Mínimo/Máximo**
**Definição**: Restrições de tamanho de lote
**Uso**: Limitações operacionais, capacidade, logística
**Considerações**: Pode subotimizar o EOQ

### **Fator de Perecibilidade**
**Definição**: Ajuste para produtos com vida útil limitada
**Efeito**: Reduz holding cost, favorece lotes menores
**Setores**: Alimentos, farmacêuticos, químicos

### **Múltiplos Fornecedores**
**Definição**: Opções de fornecimento com diferentes características
**Variáveis**: Lead time, custo, qualidade, capacidade
**Benefício**: Flexibilidade e redução de risco

---

## 🔄 Processos de Otimização

### **Análise Custo-Benefício**
**Definição**: Avaliação econômica de decisões de consolidação
**Componentes**:
- Economia de setup
- Aumento de holding cost
- Benefícios operacionais

### **Optimização Qualidade**
**Definição**: Medida de quão bem o algoritmo otimizou o resultado
**Escala**: 0-100%
**Fatores**: Atendimento, custo, eficiência

### **Análise de Sensibilidade**
**Definição**: Como mudanças nos parâmetros afetam os resultados
**Uso**: Validar robustez do planejamento
**Parâmetros**: Lead time, custos, demanda

---

## 📱 Termos de API

### **Endpoint**
**Definição**: URL específica para acessar funcionalidades do sistema
**Exemplo**: `/mrp_advanced` para MRP avançado

### **Payload**
**Definição**: Dados enviados na requisição
**Formato**: JSON estruturado
**Validação**: Campos obrigatórios e opcionais

### **Response**
**Definição**: Resposta estruturada do sistema
**Componentes**: Batches, analytics, metadata
**Formato**: JSON padronizado

### **Timeout**
**Definição**: Tempo limite para processamento
**Padrão**: 30 segundos
**Configurável**: Baseado na complexidade

---

## 🔐 Termos de Qualidade

### **Fallback Strategy**
**Definição**: Estratégia de contingência quando algoritmo avançado falha
**Uso**: Garantir continuidade operacional
**Exemplo**: Usar MRP básico se avançado não disponível

### **Graceful Degradation**
**Definição**: Funcionamento com funcionalidades reduzidas
**Cenários**: Biblioteca indisponível, recursos limitados
**Benefício**: Continuidade de serviço

### **Validation**
**Definição**: Verificação de consistência dos dados de entrada
**Níveis**:
- Formato (tipos de dados)
- Lógica (valores válidos)
- Consistência (relações entre campos)

---

*Glossário atualizado em: 30 de Junho de 2025* 