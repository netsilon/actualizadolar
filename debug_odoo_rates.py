import xmlrpc.client
import ssl
import json
from datetime import datetime

def check_rates():
    with open('config.json', 'r') as f:
        config = json.load(f)

    url = config['odoo_url']
    db = config['db']
    username = config['username']
    api_key = config['api_key']
    
    context = ssl._create_unverified_context()
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context)
    uid = common.authenticate(db, username, api_key, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context)

    print(f"Authenticated with UID: {uid}")

    # Get companies
    company_ids = models.execute_kw(db, uid, api_key, 'res.company', 'search', [[]])
    companies = models.execute_kw(db, uid, api_key, 'res.company', 'read', [company_ids], {'fields': ['name', 'currency_id']})

    for company in companies:
        print(f"\nCompany: {company['name']} (ID: {company['id']})")
        currency_id = company['currency_id'][0] # ID of base currency
        
        # Determine target currency (checking for VES or USD)
        # Just dump the last 5 rates for this company
        
        rate_ids = models.execute_kw(db, uid, api_key, 'res.currency.rate', 'search', 
            [[['company_id', '=', company['id']]]],
            {'limit': 5, 'order': 'name desc'})
            
        if rate_ids:
            rates = models.execute_kw(db, uid, api_key, 'res.currency.rate', 'read', [rate_ids], 
                {'fields': ['name', 'rate', 'currency_id', 'company_id']})
            for r in rates:
                # Get currency name for the rate
                cur_name = models.execute_kw(db, uid, api_key, 'res.currency', 'read', [[r['currency_id'][0]]], {'fields': ['name']})[0]['name']
                print(f"  Date: {r['name']} | Rate: {r['rate']} | Currency: {cur_name}")
        else:
            print("  No rates found.")

if __name__ == "__main__":
    check_rates()
