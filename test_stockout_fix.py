#!/usr/bin/env python3
"""
Test script to verify the stockout fix in advanced MRP algorithm
"""

import requests
import json
from datetime import datetime

def test_stockout_fix():
    """Test the improved algorithm against the problematic input"""
    
    # EXACT USER INPUT from the issue report
    test_data = {
        'sporadic_demand': {
            '2025-07-07': 4000,
            '2025-08-27': 4000,
            '2025-10-17': 4000
        },
        'initial_stock': 1941,
        'leadtime_days': 70,
        'period_start_date': '2025-05-01',
        'period_end_date': '2025-12-31', 
        'start_cutoff_date': '2025-05-01',
        'end_cutoff_date': '2025-12-31',
        'safety_margin_percent': 8,
        'safety_days': 2,
        'minimum_stock_percent': 0,
        'enable_consolidation': True,
        'id': 3327
    }

    try:
        print("🧪 Testing improved MRP algorithm...")
        print("=" * 60)
        
        response = requests.post('http://localhost:5000/mrp_advanced', json=test_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract key metrics
            total_batches = len(result['batches'])
            fulfillment_rate = result['analytics']['summary']['demand_fulfillment_rate']
            stockout_occurred = result['analytics']['summary']['stockout_occurred']
            final_stock = result['analytics']['summary']['final_stock']
            total_demand = sum(test_data['sporadic_demand'].values())
            
            print(f"📊 RESULTS SUMMARY:")
            print(f"   Total Demand: {total_demand:,} units")
            print(f"   Initial Stock: {test_data['initial_stock']:,} units")
            print(f"   Lead Time: {test_data['leadtime_days']} days")
            print(f"   Total Batches Created: {total_batches}")
            print(f"   Demand Fulfillment Rate: {fulfillment_rate}%")
            print(f"   Stockout Occurred: {'❌ YES' if stockout_occurred else '✅ NO'}")
            print(f"   Final Stock: {final_stock}")
            print()
            
            print("📦 BATCH DETAILS:")
            print("-" * 60)
            total_produced = 0
            
            for i, batch in enumerate(result['batches']):
                strategy = batch['analytics'].get('advanced_mrp_strategy', 'N/A')
                demands_covered = batch['analytics'].get('demands_covered', [])
                total_produced += batch['quantity']
                
                print(f"Batch {i+1}: {batch['quantity']:,.1f} units")
                print(f"  📅 Order Date: {batch['order_date']}")
                print(f"  📦 Arrival Date: {batch['arrival_date']}")
                print(f"  🎯 Strategy: {strategy}")
                print(f"  📋 Demands Covered: {len(demands_covered)}")
                if demands_covered:
                    for demand in demands_covered:
                        print(f"      • {demand['date']}: {demand['quantity']:,} units")
                print()
            
            print("📈 PERFORMANCE ANALYSIS:")
            print("-" * 60)
            print(f"   Total Produced: {total_produced:,.1f} units")
            print(f"   Total Required: {total_demand:,} units")
            print(f"   Production Coverage: {(total_produced/total_demand)*100:.1f}%")
            
            if stockout_occurred:
                print(f"   ❌ STOCKOUT ISSUES REMAIN:")
                unmet_demands = result['analytics']['summary'].get('unmet_demand_details', [])
                for unmet in unmet_demands:
                    print(f"      • {unmet['date']}: {unmet['shortage']:,} units short")
            else:
                print(f"   ✅ NO STOCKOUTS - ALGORITHM FIXED!")
            
            print()
            print("🎯 ALGORITHM EFFECTIVENESS:")
            print("-" * 60)
            if fulfillment_rate >= 95 and not stockout_occurred:
                print("   ✅ EXCELLENT: Algorithm working perfectly!")
                print("   ✅ All demands covered with no stockouts")
            elif fulfillment_rate >= 80:
                print("   ⚠️  GOOD: Significant improvement but room for optimization")
            else:
                print("   ❌ POOR: Algorithm still needs work")
                
            return {
                'success': True,
                'fulfillment_rate': fulfillment_rate,
                'stockout_occurred': stockout_occurred,
                'total_batches': total_batches,
                'total_produced': total_produced
            }
            
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Server not running")
        print("💡 Start server with: python server.py")
        return {'success': False, 'error': 'Connection failed'}
    except Exception as e:
        print(f"❌ Test Error: {str(e)}")
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    print("🚀 MRP Stockout Fix Verification Test")
    print("=" * 60)
    print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    result = test_stockout_fix()
    
    print()
    print("=" * 60)
    if result['success']:
        if result.get('fulfillment_rate', 0) >= 95 and not result.get('stockout_occurred', True):
            print("🎉 TEST PASSED: Stockout issues resolved!")
        else:
            print("⚠️  TEST PARTIALLY SUCCESSFUL: Improvements made but optimization needed")
    else:
        print(f"❌ TEST FAILED: {result.get('error', 'Unknown error')}") 