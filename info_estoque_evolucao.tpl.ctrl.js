app.controller('InfoMrpEvolucaoCtrl', ['$scope', '$timeout', function($scope, $timeout) {

        $scope.data = $scope.metricas;

        console.log($scope.item);

        $scope.productName = $scope.item.mercadoria.xProd;

        // Funções para cálculos das métricas
        $scope.getRiskLevel = function() {
            var riskProbability = $scope.getRiskProbability();
            
            if (riskProbability >= 15) return 'Crítico';
            if (riskProbability >= 5) return 'Alto';
            if (riskProbability >= 1) return 'Médio';
            return 'Baixo';
        };

        $scope.getRiskProbability = function() {
            // Usar a probabilidade real calculada pelo MRP se disponível
            if ($scope.data.extended_analytics && 
                $scope.data.extended_analytics.risk_analysis && 
                $scope.data.extended_analytics.risk_analysis.stockout_risk) {
                return Math.round($scope.data.extended_analytics.risk_analysis.stockout_risk.probability);
            }
            
            // Fallback: cálculo baseado em pontos críticos (melhorado)
            if (!$scope.data.critical_points || $scope.data.critical_points.length === 0) {
                return 0;
            }
            
            var totalPoints = $scope.data.critical_points.length;
            var criticalPoints = $scope.data.critical_points.filter(p => p.severity === 'critical').length;
            
            // Cálculo mais realista: % de dias com estoque crítico (< 2 dias)
            var criticalDays = $scope.data.critical_points.filter(p => p.days_of_coverage < 2).length;
            return Math.round((criticalDays / totalPoints) * 100);
        };

        $scope.getStockoutDays = function() {
            var criticalPoint = $scope.data.critical_points.find(p => p.severity === 'critical');
            if (criticalPoint) {
                return Math.round(criticalPoint.days_of_coverage);
            }
            var minPoint = Math.min(...$scope.data.critical_points.map(p => p.days_of_coverage));
            return Math.round(minPoint);
        };

        $scope.getSafetyMargin = function() {
            return Math.round($scope.data.summary.final_stock - $scope.data.summary.minimum_stock);
        };

        $scope.getCurrentCoverage = function() {
            var currentStock = $scope.data.summary.initial_stock;
            var dailyDemand = $scope.data.demand_analysis.average_daily_demand;
            return Math.round(currentStock / dailyDemand);
        };

        $scope.getProjectedCoverage = function() {
            // Usar dados do estoque final se available
            if ($scope.data.summary && $scope.data.summary.final_stock && $scope.data.demand_analysis) {
                var finalStock = $scope.data.summary.final_stock;
                var dailyDemand = $scope.data.demand_analysis.average_daily_demand;
                return Math.round(finalStock / dailyDemand);
            }
            
            // Fallback: pegar cobertura do último período se existir monthly
            if ($scope.data.stock_end_of_period && 
                $scope.data.stock_end_of_period.monthly && 
                $scope.data.stock_end_of_period.monthly.length > 0) {
                var lastPeriod = $scope.data.stock_end_of_period.monthly[$scope.data.stock_end_of_period.monthly.length - 1];
                return Math.round(lastPeriod.days_of_coverage);
            }
            
            // Último fallback
            return 0;
        };

        $scope.getCoverageStatus = function() {
            var coverage = $scope.getCurrentCoverage();
            if (coverage < 10) return 'INADEQUADO';
            if (coverage < 30) return 'ATENÇÃO';
            return 'OK';
        };

        $scope.getCoverageStatusClass = function() {
            var status = $scope.getCoverageStatus();
            if (status === 'INADEQUADO') return 'status-inadequado';
            if (status === 'ATENÇÃO') return 'status-warning';
            return 'status-ok';
        };

        $scope.getStockValue = function() {
            // Simulando um valor unitário de R$ 25
            return $scope.data.summary.final_stock * 25;
        };

        $scope.getDailyCost = function() {
            // Simulando 0.1% do valor do estoque por dia
            return $scope.getStockValue() * 0.001;
        };

        $scope.getTurnover = function() {
            var annualDemand = $scope.data.demand_analysis.total_demand * (365 / $scope.data.demand_analysis.period_days);
            var avgStock = ($scope.data.summary.initial_stock + $scope.data.summary.final_stock) / 2;
            return Math.round((annualDemand / avgStock) * 10) / 10;
        };

        $scope.getOrderDate = function() {
            if ($scope.data.stock_end_of_period && 
                $scope.data.stock_end_of_period.before_batch_arrival && 
                $scope.data.stock_end_of_period.before_batch_arrival.length > 0 &&
                $scope.data.stock_end_of_period.before_batch_arrival[0]) {
                return new Date($scope.data.stock_end_of_period.before_batch_arrival[0].date);
            }
            // Fallback: usar primeira data de order_dates se disponível
            if ($scope.data.order_dates && $scope.data.order_dates.length > 0) {
                return new Date($scope.data.order_dates[0]);
            }
            return new Date(); // Data atual como último fallback
        };

        $scope.getDeliveryDate = function() {
            if ($scope.data.stock_end_of_period && 
                $scope.data.stock_end_of_period.after_batch_arrival && 
                $scope.data.stock_end_of_period.after_batch_arrival.length > 0 &&
                $scope.data.stock_end_of_period.after_batch_arrival[0]) {
                var deliveryDate = new Date($scope.data.stock_end_of_period.after_batch_arrival[0].date);
                return deliveryDate.toLocaleDateString('pt-BR');
            }
            // Fallback: usar primeiro batch se disponível
            if ($scope.data.batches && $scope.data.batches.length > 0) {
                var firstBatch = $scope.data.batches[0];
                if (firstBatch.arrival_date) {
                    return new Date(firstBatch.arrival_date).toLocaleDateString('pt-BR');
                }
            }
            return new Date().toLocaleDateString('pt-BR'); // Data atual como último fallback
        };

        $scope.getLeadTime = function() {
            // Tentar calcular lead time dos batches
            if ($scope.data.batches && $scope.data.batches.length > 0) {
                var batch = $scope.data.batches[0];
                if (batch.analytics && batch.analytics.actual_lead_time) {
                    return batch.analytics.actual_lead_time;
                }
                // Calcular baseado em order_date e arrival_date
                if (batch.order_date && batch.arrival_date) {
                    var orderDate = new Date(batch.order_date);
                    var arrivalDate = new Date(batch.arrival_date);
                    return Math.round((arrivalDate - orderDate) / (1000 * 60 * 60 * 24));
                }
            }
            
            // Fallback: calcular baseado nos dados de after_batch_arrival
            if ($scope.data.stock_end_of_period && 
                $scope.data.stock_end_of_period.after_batch_arrival && 
                $scope.data.stock_end_of_period.after_batch_arrival.length > 1) {
                var batches = $scope.data.stock_end_of_period.after_batch_arrival;
                return Math.round((new Date(batches[1].date) - new Date(batches[0].date)) / (1000 * 60 * 60 * 24));
            }
            return 7; // Lead time padrão de 7 dias
        };

        $scope.getNeedDate = function() {
            if ($scope.data.summary.minimum_stock_date) {
                return new Date($scope.data.summary.minimum_stock_date);
            }
            return new Date(); // Fallback para data atual
        };

        $scope.getProductionCoverageRate = function() {
            // O campo já vem formatado como "92%"
            if ($scope.data.summary && $scope.data.summary.production_coverage_rate) {
                return parseFloat($scope.data.summary.production_coverage_rate.replace('%', ''));
            }
            return 92; // Valor dos dados fornecidos
        };

        $scope.getTotalDemand = function() {
            return $scope.data.demand_analysis.total_demand;
        };

        $scope.getAverageBatchSize = function() {
            return $scope.data.production_efficiency.average_batch_size;
        };

        $scope.getProductionUtilization = function() {
            return $scope.data.production_efficiency.production_line_utilization;
        };

        $scope.initChart = function() {
            // Verificar se dados essenciais existem
            if (!$scope.data.stock_evolution) {
                console.warn('stock_evolution não encontrado nos dados');
                return;
            }
            
            var stockDates = Object.keys($scope.data.stock_evolution);
            var stockValues = Object.values($scope.data.stock_evolution);

            // Datas de reposição que DEVEM estar no gráfico
            var batchArrivals = ($scope.data.stock_end_of_period && $scope.data.stock_end_of_period.after_batch_arrival) 
                               ? $scope.data.stock_end_of_period.after_batch_arrival 
                               : [];
            var replenishmentDates = batchArrivals.map(batch => batch.date);
            
            // Datas de início de produção/compras
            var orderDates = $scope.data.order_dates || [];
            var orderDateStrings = orderDates.map(order => {
                // MRP retorna strings simples, não objetos
                return typeof order === 'string' ? order : (order.date || order);
            });
            
            // Datas de demandas programadas (campo opcional)
            var demandsCovered = $scope.data.demands_covered || [];
            var demandDateStrings = demandsCovered.map(demand => {
                return typeof demand === 'string' ? demand : (demand.date || demand);
            });
            
            // Filtrar mantendo 1 a cada 3 dias + todas as datas importantes
            var importantDates = [...replenishmentDates, ...orderDateStrings, ...demandDateStrings];
            var reducedDates = [];
            var reducedValues = [];
            
            stockDates.forEach(function(date, index) {
                // Incluir se for 1 a cada 3 dias OU se for uma data importante
                if (index % 3 === 0 || importantDates.includes(date)) {
                    reducedDates.push(date);
                    reducedValues.push(stockValues[index]);
                }
            });

            // Identificar os pontos de reposição
            var replenishmentPoints = [];
            batchArrivals.forEach(function(batch) {
                var dateIndex = reducedDates.findIndex(d => d === batch.date);
                if (dateIndex >= 0) {
                    replenishmentPoints.push({
                        x: dateIndex,
                        y: batch.stock_after
                    });
                }
            });

            // Identificar os pontos de início de produção
            var orderPoints = [];
            orderDates.forEach(function(order, index) {
                var orderDate = typeof order === 'string' ? order : (order.date || order);
                var dateIndex = reducedDates.findIndex(d => d === orderDate);
                if (dateIndex >= 0) {
                    orderPoints.push({
                        x: dateIndex,
                        y: reducedValues[dateIndex], // Stock no momento do pedido
                        batchNumber: index + 1
                    });
                }
            });

            // Identificar os pontos de demandas programadas
            var demandPoints = [];
            demandsCovered.forEach(function(demand, index) {
                var demandDate = typeof demand === 'string' ? demand : (demand.date || demand);
                var dateIndex = reducedDates.findIndex(d => d === demandDate);
                if (dateIndex >= 0) {
                    demandPoints.push({
                        x: dateIndex,
                        y: reducedValues[dateIndex], // Stock no momento da demanda
                        demandInfo: demand
                    });
                }
            });

            var ctx = document.getElementById('stockChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: reducedDates.map(function(date) {
                        return new Date(date).toLocaleDateString('pt-BR', {month: 'numeric', day: 'numeric'});
                    }),
                    datasets: [{
                        label: 'Nível de Estoque',
                        data: reducedValues,
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        fill: true,
                        tension: 0.1,
                        borderWidth: 2,
                        pointRadius: 1,
                        pointHoverRadius: 4
                    }, {
                        label: 'Nível Mínimo',
                        data: Array(reducedDates.length).fill($scope.data.summary ? $scope.data.summary.minimum_stock || 0 : 0),
                        borderColor: '#dc3545',
                        borderDash: [5, 5],
                        fill: false,
                        borderWidth: 2,
                        pointRadius: 0
                    }, {
                        label: 'Reposições',
                        data: reducedValues.map((val, idx) => {
                            var repPoint = replenishmentPoints.find(p => p.x === idx);
                            return repPoint ? repPoint.y : null;
                        }),
                        borderColor: '#28a745',
                        backgroundColor: '#28a745',
                        pointRadius: function(context) {
                            return context.raw !== null ? 10 : 0;
                        },
                        pointStyle: 'triangle',
                        pointHoverRadius: 12,
                        showLine: false,
                        fill: false
                    }, {
                        label: 'Ordens',
                        data: reducedValues.map((val, idx) => {
                            var orderPoint = orderPoints.find(p => p.x === idx);
                            return orderPoint ? orderPoint.y : null;
                        }),
                        borderColor: '#ffc107',
                        backgroundColor: '#ffc107',
                        pointRadius: function(context) {
                            return context.raw !== null ? 8 : 0;
                        },
                        pointStyle: 'rectRot', // Losango rotacionado
                        pointHoverRadius: 10,
                        showLine: false,
                        fill: false
                    }, {
                        label: 'Demandas',
                        data: reducedValues.map((val, idx) => {
                            var demandPoint = demandPoints.find(p => p.x === idx);
                            return demandPoint ? demandPoint.y : null;
                        }),
                        borderColor: '#6f42c1',
                        backgroundColor: '#6f42c1',
                        pointRadius: function(context) {
                            return context.raw !== null ? 7 : 0;
                        },
                        pointStyle: 'circle', // Círculo
                        pointHoverRadius: 9,
                        showLine: false,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                usePointStyle: true,
                                padding: 15,
                                font: { size: 11 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                title: function(context) {
                                    var dateStr = reducedDates[context[0].dataIndex];
                                    return new Date(dateStr).toLocaleDateString('pt-BR', {
                                        weekday: 'short',
                                        day: '2-digit',
                                        month: '2-digit',
                                        year: 'numeric'
                                    });
                                },
                                label: function(context) {
                                    var label = context.dataset.label || '';
                                    if (label === 'Nível de Estoque') {
                                        var value = context.parsed.y;
                                        var dailyDemand = ($scope.data.demand_analysis && $scope.data.demand_analysis.average_daily_demand) 
                                                         ? $scope.data.demand_analysis.average_daily_demand 
                                                         : 1;
                                        var coverage = Math.round(value / dailyDemand);
                                        return '📊 ' + label + ': ' + value.toLocaleString('pt-BR') + ' un (' + coverage + ' dias)';
                                    } else if (label === 'Nível Mínimo') {
                                        return '📉 ' + label + ': ' + context.parsed.y.toLocaleString('pt-BR') + ' un';
                                    } else if (label === 'Reposições' && context.parsed.y !== null) {
                                        var currentDate = reducedDates[context.dataIndex];
                                        var batch = batchArrivals.find(b => b.date === currentDate);
                                        if (batch) {
                                            return '🔺 Lote ' + batch.batch_number + ': +' + Math.round(batch.batch_quantity).toLocaleString('pt-BR') + ' un';
                                        }
                                        return '🔺 Reposição: ' + context.parsed.y.toLocaleString('pt-BR') + ' un';
                                    } else if (label === 'Ordens' && context.parsed.y !== null) {
                                        var currentDate = reducedDates[context.dataIndex];
                                        var orderPoint = orderPoints.find(p => p.x === context.dataIndex);
                                        if (orderPoint) {
                                            var orderDateFormatted = new Date(currentDate).toLocaleDateString('pt-BR', {
                                                day: '2-digit',
                                                month: '2-digit',
                                                year: 'numeric'
                                            });
                                            return '🏭 Início Lote ' + orderPoint.batchNumber + ' em ' + orderDateFormatted + ' (Lead: 50 dias)';
                                        }
                                        return '🏭 Início Produção';
                                    } else if (label === 'Demandas' && context.parsed.y !== null) {
                                        var currentDate = reducedDates[context.dataIndex];
                                        var demandPoint = demandPoints.find(p => p.x === context.dataIndex);
                                        if (demandPoint) {
                                            var demandDateFormatted = new Date(currentDate).toLocaleDateString('pt-BR', {
                                                day: '2-digit',
                                                month: '2-digit',
                                                year: 'numeric'
                                            });
                                            var demandInfo = demandPoint.demandInfo;
                                            var quantityText = demandInfo.quantity ? ' (' + Math.round(demandInfo.quantity).toLocaleString('pt-BR') + ' un)' : '';
                                            return '🎯 Demanda programada em ' + demandDateFormatted + quantityText;
                                        }
                                        return '🎯 Demanda programada';
                                    }
                                    return null;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            grid: { display: false },
                            ticks: {
                                font: { size: 10 },
                                maxTicksLimit: 12
                            }
                        },
                        y: {
                            display: true,
                            grid: {
                                display: true,
                                color: '#f1f3f4'
                            },
                            ticks: {
                                font: { size: 10 },
                                callback: function(value) {
                                    return value.toLocaleString('pt-BR');
                                }
                            }
                        }
                    }
                }
            });
        };

        $scope.close = function() {
            $scope.dismiss('cancel');
        };

        $timeout(function() {
            $scope.initChart();
        }, 300);
    }]);