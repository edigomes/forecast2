# 📚 Advanced MRP System - API Reference

## 🚀 Core Classes and Methods

### MRPOptimizer

Main class for MRP calculations and optimizations.

#### Constructor

```python
MRPOptimizer(optimization_params: Optional[OptimizationParams] = None)
```

**Parameters:**
- `optimization_params`: Optional custom optimization parameters

**Example:**
```python
from mrp import MRPOptimizer, OptimizationParams

# Default parameters
optimizer = MRPOptimizer()

# Custom parameters
params = OptimizationParams(setup_cost=300.0, holding_cost_rate=0.25)
optimizer = MRPOptimizer(params)
```

---

### calculate_batches_for_sporadic_demand()

Main method for sporadic demand planning.

#### Signature

```python
def calculate_batches_for_sporadic_demand(
    self,
    sporadic_demand: Dict[str, float],
    initial_stock: float,
    leadtime_days: int,
    period_start_date: str,
    period_end_date: str,
    start_cutoff_date: str,
    end_cutoff_date: str,
    safety_margin_percent: float = 8.0,
    safety_days: int = 2,
    minimum_stock_percent: float = 0.0,
    max_gap_days: int = 999,
    **kwargs
) -> Dict
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `sporadic_demand` | Dict[str, float] | ✅ | - | Demands by date {"YYYY-MM-DD": quantity} |
| `initial_stock` | float | ✅ | - | Available stock at period start |
| `leadtime_days` | int | ✅ | - | Lead time in days |
| `period_start_date` | str | ✅ | - | Period start date "YYYY-MM-DD" |
| `period_end_date` | str | ✅ | - | Period end date "YYYY-MM-DD" |
| `start_cutoff_date` | str | ✅ | - | Earliest order date "YYYY-MM-DD" |
| `end_cutoff_date` | str | ✅ | - | Latest arrival date "YYYY-MM-DD" |
| `safety_margin_percent` | float | ❌ | 8.0 | Safety margin percentage |
| `safety_days` | int | ❌ | 2 | Additional safety days |
| `minimum_stock_percent` | float | ❌ | 0.0 | Minimum stock as % of max demand |
| `max_gap_days` | int | ❌ | 999 | Maximum gap between orders |

#### Return Value

Returns a dictionary with the following structure:

```python
{
    "batches": [
        {
            "order_date": "2024-06-15",
            "arrival_date": "2024-07-15", 
            "quantity": 2850.5,
            "analytics": {
                "stock_before_arrival": 125.0,
                "stock_after_arrival": 2975.5,
                "demands_covered": [
                    {"date": "2024-07-15", "quantity": 1000},
                    {"date": "2024-08-20", "quantity": 1500}
                ],
                "coverage_days": 67,
                "consolidated_group": true,
                "consolidation_quality": "high",
                "urgency_level": "normal",
                "efficiency_ratio": 1.9
            }
        }
    ],
    "analytics": {
        "summary": { ... },
        "advanced_mrp_strategy": { ... },
        "performance_metrics": { ... },
        "cost_analysis": { ... }
    }
}
```

#### Example Usage

```python
# Basic usage
result = optimizer.calculate_batches_for_sporadic_demand(
    sporadic_demand={
        "2024-07-15": 1000,
        "2024-08-20": 1500,
        "2024-09-10": 800
    },
    initial_stock=500,
    leadtime_days=30,
    period_start_date="2024-07-01",
    period_end_date="2024-12-31",
    start_cutoff_date="2024-06-01",
    end_cutoff_date="2024-11-30"
)

# Advanced usage with custom parameters
result = optimizer.calculate_batches_for_sporadic_demand(
    sporadic_demand=demands,
    initial_stock=1500,
    leadtime_days=45,
    period_start_date="2024-01-01",
    period_end_date="2024-12-31", 
    start_cutoff_date="2023-12-01",
    end_cutoff_date="2024-11-30",
    safety_margin_percent=12.0,
    safety_days=7,
    minimum_stock_percent=15.0,
    max_gap_days=60,
    # Additional parameters
    enable_consolidation=True,
    force_consolidation_within_leadtime=True,
    min_consolidation_benefit=200.0
)
```

---

### OptimizationParams

Configuration class for optimization parameters.

#### Constructor

```python
OptimizationParams(
    setup_cost: float = 250.0,
    holding_cost_rate: float = 0.20,
    stockout_cost_multiplier: float = 15,
    service_level: float = 0.98,
    min_batch_size: float = 200.0,
    max_batch_size: float = 10000.0,
    review_period_days: int = 7,
    safety_days: int = 15,
    consolidation_window_days: int = 5,
    daily_production_capacity: float = float('inf'),
    enable_eoq_optimization: bool = True,
    enable_consolidation: bool = True,
    force_consolidation_within_leadtime: bool = True,
    min_consolidation_benefit: float = 50.0,
    operational_efficiency_weight: float = 1.0,
    overlap_prevention_priority: bool = True
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `setup_cost` | float | 250.0 | Fixed cost per order |
| `holding_cost_rate` | float | 0.20 | Annual holding cost rate |
| `stockout_cost_multiplier` | float | 15 | Stockout cost multiplier |
| `service_level` | float | 0.98 | Target service level (0-1) |
| `min_batch_size` | float | 200.0 | Minimum order quantity |
| `max_batch_size` | float | 10000.0 | Maximum order quantity |
| `enable_consolidation` | bool | True | Enable intelligent consolidation |
| `force_consolidation_within_leadtime` | bool | True | Force consolidation to prevent overlap |
| `min_consolidation_benefit` | float | 50.0 | Minimum benefit for consolidation |
| `operational_efficiency_weight` | float | 1.0 | Weight of operational benefits |
| `overlap_prevention_priority` | bool | True | Prioritize overlap prevention |

---

## 📊 Response Data Structures

### Batch Object

Each batch in the `batches` array has the following structure:

```python
{
    "order_date": "YYYY-MM-DD",        # When to place the order
    "arrival_date": "YYYY-MM-DD",      # When batch arrives
    "quantity": 2850.5,               # Order quantity
    "analytics": {
        # Stock levels
        "stock_before_arrival": 125.0,
        "stock_after_arrival": 2975.5,
        "consumption_since_last_arrival": 890.0,
        
        # Coverage and timing
        "coverage_days": 67,
        "actual_lead_time": 30,
        "safety_margin_days": 5,
        "arrival_delay": 0,
        
        # Demand coverage
        "demands_covered": [
            {"date": "2024-07-15", "quantity": 1000},
            {"date": "2024-08-20", "quantity": 1500}
        ],
        "coverage_count": 2,
        "target_demand_date": "2024-07-15",
        "target_demand_quantity": 1000,
        "shortfall_covered": 875.0,
        
        # Quality metrics
        "urgency_level": "normal",        # critical|high|normal
        "efficiency_ratio": 1.9,
        "is_critical": false,
        
        # Consolidation info (if applicable)
        "consolidated_group": true,
        "group_size": 3,
        "consolidation_savings": 250.0,
        "consolidation_quality": "high",  # high|medium|low
        "net_savings": 425.50,
        
        # Advanced MRP (if using advanced planner)
        "advanced_mrp_strategy": "hybrid_consolidation",
        "eoq_used": 1847.3,
        "abc_classification": "A",
        "xyz_classification": "X"
    }
}
```

### Analytics Object

The `analytics` object contains comprehensive performance metrics:

```python
{
    "summary": {
        "initial_stock": 500.0,
        "final_stock": 1250.5,
        "minimum_stock": 25.0,
        "minimum_stock_date": "2024-08-15",
        "stockout_occurred": false,
        "total_batches": 3,
        "total_produced": 5500.0,
        "production_coverage_rate": "110%",
        "stock_consumed": 4500.0,
        "demand_fulfillment_rate": 100.0,
        "demands_met_count": 5,
        "demands_unmet_count": 0,
        "average_batch_per_demand": 0.6
    },
    
    "stock_evolution": {
        "2024-07-01": 500.0,
        "2024-07-15": 2475.5,
        "2024-08-20": 975.5,
        // ... daily stock levels
    },
    
    "critical_points": [
        {
            "date": "2024-08-15",
            "stock": 25.0,
            "days_of_coverage": 0.5,
            "severity": "warning",          # stockout|critical|warning
            "demand_on_date": 0
        }
    ],
    
    "performance_metrics": {
        "realized_service_level": 98.5,
        "inventory_turnover": 8.2,
        "average_days_of_inventory": 44.5,
        "setup_frequency": 6,
        "average_batch_size": 1833.3,
        "stock_variability_cv": 0.15,
        "perfect_order_rate": 92.0
    },
    
    "cost_analysis": {
        "total_cost": 15420.50,
        "setup_cost": 1500.00,
        "holding_cost": 12850.30,
        "stockout_cost": 1070.20,
        "cost_breakdown_percentage": {
            "setup": 9.7,
            "holding": 83.3,
            "stockout": 6.9
        }
    },
    
    "demand_analysis": {
        "total_demand": 5000.0,
        "average_daily_demand": 27.4,
        "demand_by_month": {
            "2024-07": 1000.0,
            "2024-08": 1500.0,
            "2024-09": 2500.0
        },
        "period_days": 183,
        "demand_events": 5,
        "average_demand_per_event": 1000.0,
        "first_demand_date": "2024-07-15",
        "last_demand_date": "2024-12-20",
        "demand_distribution": {
            "2024-07-15": 1000.0,
            "2024-08-20": 1500.0
            // ... all demands
        }
    },
    
    "sporadic_demand_metrics": {
        "demand_concentration": {
            "concentration_index": 0.027,
            "concentration_level": "low",
            "days_with_demand": 5,
            "total_period_days": 183
        },
        "interval_statistics": {
            "average_interval_days": 45.0,
            "min_interval_days": 25,
            "max_interval_days": 65,
            "interval_variance": 285.5
        },
        "demand_predictability": "medium",  # high|medium|low
        "peak_demand_analysis": {
            "peak_count": 2,
            "peak_threshold": 1500.0,
            "peak_dates": ["2024-08-20", "2024-12-20"],
            "average_peak_size": 1750.0
        }
    }
}
```

### Advanced MRP Strategy Object

When using the advanced planner, additional strategic information is provided:

```python
{
    "advanced_mrp_strategy": {
        "strategy_name": "hybrid_consolidation",      # Strategy used
        "eoq_used": 1847.3,                          # Calculated EOQ
        "safety_stock_calculated": 245.8,            # Safety stock
        "reorder_point": 1456.2,                     # Reorder point
        "abc_classification": "A",                    # Value classification
        "xyz_classification": "X",                    # Predictability
        "demand_variability_cv": 0.28,              # Coefficient of variation
        "demand_regularity_score": 0.85,             # Regularity (0-1)
        "optimization_quality": "excellent",          # Quality assessment
        "seasonality_detected": true,                # Seasonal patterns
        "trend_direction": "stable",                 # Trend analysis
        "total_setup_cost": 750.0,                  # Setup costs
        "total_holding_cost": 2150.5,               # Holding costs
        "total_estimated_cost": 2900.5,             # Total cost
        "consolidation_groups": 2,                   # Number of groups
        "consolidation_efficiency": 0.85             # Efficiency score
    }
}
```

---

## 🌐 REST API Endpoints

### POST /mrp_sporadic

Calculate sporadic demand batches via REST API.

#### Request

```http
POST /mrp_sporadic HTTP/1.1
Content-Type: application/json

{
    "sporadic_demand": {
        "2024-07-15": 1000,
        "2024-08-20": 1500,
        "2024-09-10": 800
    },
    "initial_stock": 500,
    "leadtime_days": 30,
    "period_start_date": "2024-07-01",
    "period_end_date": "2024-12-31",
    "start_cutoff_date": "2024-06-01",
    "end_cutoff_date": "2024-11-30",
    "safety_margin_percent": 8.0,
    "safety_days": 5,
    "enable_consolidation": true,
    "force_consolidation_within_leadtime": true,
    "min_consolidation_benefit": 100.0
}
```

#### Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "batches": [ ... ],
    "analytics": { ... }
}
```

#### Error Responses

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
    "error": true,
    "message": "Invalid date format: period_start_date must be YYYY-MM-DD",
    "batches": [],
    "analytics": { ... }
}
```

---

## 🔧 Configuration Examples

### High-Volume Manufacturing

```python
params = OptimizationParams(
    setup_cost=500.0,                        # Higher setup costs
    holding_cost_rate=0.15,                  # Lower holding rate
    min_batch_size=1000,                     # Larger minimum batches
    service_level=0.99,                      # High service level
    enable_consolidation=True,               # Enable consolidation
    operational_efficiency_weight=2.0,      # High operational focus
    force_consolidation_within_leadtime=True # Prevent overlap
)
```

### Cost-Sensitive Operations

```python
params = OptimizationParams(
    setup_cost=100.0,                        # Lower setup costs
    holding_cost_rate=0.30,                  # Higher holding rate
    service_level=0.95,                      # Moderate service level
    min_consolidation_benefit=200.0,         # Higher threshold
    overlap_prevention_priority=True,        # Prevent waste
    operational_efficiency_weight=0.5       # Lower operational weight
)
```

### Long Lead Time Operations

```python
params = OptimizationParams(
    setup_cost=400.0,                        # Higher setup costs
    safety_days=21,                          # Extended safety buffer
    service_level=0.99,                      # High service level
    max_batch_size=20000,                    # Allow larger batches
    force_consolidation_within_leadtime=True, # Critical for long LT
    min_consolidation_benefit=300.0          # Higher threshold
)
```

---

## 🚫 Error Handling

### Common Error Codes

| Code | Message | Solution |
|------|---------|----------|
| `INVALID_DATE` | "Invalid date format" | Use YYYY-MM-DD format |
| `NEGATIVE_STOCK` | "Initial stock cannot be negative" | Provide positive stock value |
| `INVALID_LEADTIME` | "Lead time must be >= 0" | Use non-negative lead time |
| `EMPTY_DEMAND` | "No valid demands provided" | Provide at least one demand |
| `DATE_ORDER` | "End date before start date" | Check date order |

### Exception Handling

```python
try:
    result = optimizer.calculate_batches_for_sporadic_demand(**params)
except ValueError as e:
    print(f"Parameter error: {e}")
except KeyError as e:
    print(f"Missing required parameter: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## 📈 Performance Guidelines

### Recommended Limits

| Parameter | Recommended Limit | Performance Impact |
|-----------|-------------------|-------------------|
| Number of demands | < 100 | Linear |
| Lead time (days) | < 365 | Minimal |
| Period length (days) | < 730 | Linear |
| Batch size range | 10x - 1000x | Minimal |

### Optimization Tips

1. **Use appropriate date ranges** - Avoid unnecessarily long periods
2. **Limit demand complexity** - Group similar demands when possible
3. **Tune consolidation parameters** - Balance between consolidation and performance
4. **Enable caching** - For repeated calculations with similar parameters

---

**📝 This API reference provides complete details for integrating and using the Advanced MRP system.** 