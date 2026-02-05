import requests
from bs4 import BeautifulSoup
import urllib3
import json
import argparse
import sys
import xmlrpc.client
import ssl
from datetime import datetime

# Disable SSL warnings for BCV site if needed (common issue)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BCVFetcher:
    def __init__(self):
        self.url = "http://www.bcv.org.ve/"

    def get_rate(self):
        try:
            # BCV often has SSL issues, verify=False is usually needed
            response = requests.get(self.url, verify=False, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # The rate is usually in a div with id 'dolar' or similar specific structure
            # Based on standard BCV layout inspection (need to be robust here)
            # Typically: <div id="dolar"> ... <strong> 60.50 </strong> ... </div>
            
            # Debug: Print all currencies found to stderr
            dollar_div = soup.find('div', {'id': 'dolar'})
            euro_div = soup.find('div', {'id': 'euro'})
            
            if dollar_div:
                raw_text = dollar_div.find('strong').text.strip()
                print(f"DEBUG: Found Dollar Div. Text: '{raw_text}'", file=sys.stderr)
                rate_text = raw_text.replace(',', '.')
                return float(rate_text)
            
            if euro_div:
                 print(f"DEBUG: Found Euro Div instead? Text: '{euro_div.find('strong').text.strip()}'", file=sys.stderr)

            # Fallback: look for commonly used classes or structures if IDs change
            # Example: <div class="recuadrotsmc"> ... <span> USD </span> ... <strong> 60.50 </strong> ... </div>
            # This is a robust fallback attempt
            containers = soup.find_all('div', {'class': 'recuadrotsmc'})
            for c in containers:
                currency_label = c.find('span')
                if currency_label and 'USD' in currency_label.text:
                    rate_text = c.find('strong').text.strip()
                    print(f"DEBUG: Found USD via class. Text: '{rate_text}'", file=sys.stderr)
                    return float(rate_text.replace(',', '.'))
            
            print("DEBUG: No valid rate container found.", file=sys.stderr)
            return 0.0
            
        except Exception as e:
            print(f"Error fetching BCV rate: {e}", file=sys.stderr)
            return 0.0

class OdooUpdater:
    def __init__(self, config_path="config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.url = self.config['odoo_url']
        self.db = self.config['db']
        self.username = self.config['username']
        self.api_key = self.config['api_key']
        
        # Create unverified SSL context
        context = ssl._create_unverified_context()

        self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common', context=context)
        self.uid = self.common.authenticate(self.db, self.username, self.api_key, {})
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object', context=context)

    def get_current_rates(self, bcv_rate):
        if not self.uid:
            return {"success": False, "message": "Authentication failed"}

        try:
            # 1. Get all allowed companies
            company_ids = self.models.execute_kw(self.db, self.uid, self.api_key,
                'res.company', 'search', [[]])
            
            companies = self.models.execute_kw(self.db, self.uid, self.api_key,
                'res.company', 'read', [company_ids], {'fields': ['name', 'currency_id']})

            current_status = []
            all_match = True

            for company in companies:
                c_id = company['id']
                c_name = company['name']
                currency_id = company['currency_id'][0]
                
                # Get currency details
                currency_data = self.models.execute_kw(self.db, self.uid, self.api_key,
                    'res.currency', 'read', [[currency_id]], {'fields': ['name']})
                base_currency_code = currency_data[0]['name']

                target_currency_name = ""
                expected_rate = 0.0

                # Determine expected rate logic
                if base_currency_code in ['USD', 'US$'] or 'USD' in base_currency_code:
                    ves_ids = self.models.execute_kw(self.db, self.uid, self.api_key,
                        'res.currency', 'search', [[['name', 'in', ['VES', 'VEF', 'Bs.']]]])
                    if ves_ids:
                        target_currency_id = ves_ids[0]
                        target_currency_name = "VES"
                        expected_rate = bcv_rate
                    else:
                        current_status.append({
                            "company": c_name,
                            "error": "Target VES currency not found"
                        })
                        all_match = False
                        continue
                elif base_currency_code in ['VES', 'VEF', 'Bs.']:
                    usd_ids = self.models.execute_kw(self.db, self.uid, self.api_key,
                        'res.currency', 'search', [[['name', 'in', ['USD', 'US$']]]])
                    if usd_ids:
                        target_currency_id = usd_ids[0]
                        target_currency_name = "USD"
                        expected_rate = 1.0 / bcv_rate if bcv_rate > 0 else 0.0
                    else:
                        current_status.append({
                            "company": c_name,
                            "error": "Target USD currency not found"
                        })
                        all_match = False
                        continue
                else:
                    current_status.append({
                        "company": c_name,
                        "error": f"Base currency '{base_currency_code}' not supported"
                    })
                    all_match = False
                    continue

                # Get latest rate (effective rate)
                today = datetime.now().strftime('%Y-%m-%d')
                existing_rate_ids = self.models.execute_kw(self.db, self.uid, self.api_key,
                    'res.currency.rate', 'search', [
                        [['company_id', '=', c_id], ['currency_id', '=', target_currency_id]]
                    ], {'limit': 1, 'order': 'name desc'})
                
                current_rate_val = 0.0
                rate_date = ""
                
                if existing_rate_ids:
                    rate_data = self.models.execute_kw(self.db, self.uid, self.api_key,
                        'res.currency.rate', 'read', [existing_rate_ids], {'fields': ['rate', 'name']})
                    if rate_data:
                        current_rate_val = rate_data[0]['rate']
                        rate_date = rate_data[0]['name']

                # Compare with 4 decimals
                diff = abs(current_rate_val - expected_rate)
                
                # Match only if date is today AND rate matches
                # If date is old, we consider it a mismatch because we want to force daily update (or at least notify)
                rate_match = diff < 0.0001
                date_match = (rate_date == today)
                
                match = rate_match and date_match
                
                if not match:
                    all_match = False

                current_status.append({
                    "company": c_name,
                    "base_currency": base_currency_code,
                    "target_currency": target_currency_name,
                    "current_rate": current_rate_val,
                    "rate_date": rate_date,
                    "expected_rate": expected_rate,
                    "match": match
                })

            return {
                "success": True, 
                "bcv_rate": bcv_rate,
                "server_date": datetime.now().strftime('%d/%m/%Y'),
                "companies": current_status, 
                "all_match": all_match
            }

        except Exception as e:
            return {"success": False, "message": str(e)}

    def update_rates(self, bcv_rate):
        if not self.uid:
            return {"success": False, "message": "Authentication failed"}

        try:
            # 1. Get all allowed companies for the user
            # searching res.company
            company_ids = self.models.execute_kw(self.db, self.uid, self.api_key,
                'res.company', 'search', [[]])
            
            companies = self.models.execute_kw(self.db, self.uid, self.api_key,
                'res.company', 'read', [company_ids], {'fields': ['name', 'currency_id']})

            updates_log = []

            for company in companies:
                c_id = company['id']
                c_name = company['name']
                currency_id = company['currency_id'][0] # [id, name]
                
                # Get currency details to know its symbol/name
                currency_data = self.models.execute_kw(self.db, self.uid, self.api_key,
                    'res.currency', 'read', [[currency_id]], {'fields': ['name', 'symbol']})
                base_currency_code = currency_data[0]['name']

                target_rate = 0.0
                target_currency_name = ""
                
                # Logic determination using flexible matching
                # Check for USD variations
                if base_currency_code in ['USD', 'US$'] or 'USD' in base_currency_code:
                    # Base is USD, we need to update VES rate
                    # Find VES currency ID
                    ves_ids = self.models.execute_kw(self.db, self.uid, self.api_key,
                        'res.currency', 'search', [[['name', 'in', ['VES', 'VEF', 'Bs.']]]])
                    
                    if ves_ids:
                        target_currency_id = ves_ids[0]
                        target_currency_name = "VES"
                        target_rate = bcv_rate # 1 USD = X VES
                    else:
                        updates_log.append(f"Skipped {c_name}: Target VES currency not found.")
                        continue

                elif base_currency_code in ['VES', 'VEF', 'Bs.']:
                    # Base is VES, we need to update USD rate
                    # Find USD currency ID
                    usd_ids = self.models.execute_kw(self.db, self.uid, self.api_key,
                        'res.currency', 'search', [[['name', 'in', ['USD', 'US$']]]])
                    
                    if usd_ids:
                        target_currency_id = usd_ids[0]
                        target_currency_name = "USD"
                        target_rate = 1.0 / bcv_rate if bcv_rate > 0 else 0.0 # 1 VES = 1/X USD
                    else:
                        updates_log.append(f"Skipped {c_name}: Target USD currency not found.")
                        continue
                else:
                    updates_log.append(f"Skipped {c_name}: Base currency '{base_currency_code}' not identified as USD or VES.")
                    continue

                # Create or Update the rate
                today = datetime.now().strftime('%Y-%m-%d')
                
                # Check if rate already exists for today
                existing_rate_ids = self.models.execute_kw(self.db, self.uid, self.api_key,
                    'res.currency.rate', 'search', [[
                        ['name', '=', today],
                        ['company_id', '=', c_id],
                        ['currency_id', '=', target_currency_id]
                    ]])
                
                rate_vals = {
                    'rate': target_rate
                }

                if existing_rate_ids:
                    # Update existing
                    self.models.execute_kw(self.db, self.uid, self.api_key,
                        'res.currency.rate', 'write', [existing_rate_ids, rate_vals])
                    action_verb = "Updated (Overwrite)"
                else:
                    # Create new
                    rate_vals['name'] = today
                    rate_vals['currency_id'] = target_currency_id
                    rate_vals['company_id'] = c_id
                    
                    self.models.execute_kw(self.db, self.uid, self.api_key,
                        'res.currency.rate', 'create', [rate_vals])
                    action_verb = "Created"
                
                updates_log.append(f"{action_verb} {c_name}: {target_currency_name} set to {target_rate:.6f} (Base {base_currency_code})")

            return {"success": True, "log": updates_log}

        except Exception as e:
            return {"success": False, "message": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-connection', action='store_true')
    parser.add_argument('--update', action='store_true')
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()

    updater = None
    init_error = None
    
    try:
        updater = OdooUpdater()
    except Exception as e:
        init_error = str(e)

    if args.check_connection:
        if updater and updater.uid:
             print(json.dumps({"status": "OK", "uid": updater.uid}))
        else:
             print(json.dumps({"status": "Failed", "error": init_error or "Authentication Failed"}))
        sys.exit(0)

    fetcher = BCVFetcher()
    rate = fetcher.get_rate()
    
    if args.status:
        if rate > 0:
            if updater:
                result = updater.get_current_rates(rate)
                print(json.dumps(result))
            else:
                print(json.dumps({"success": False, "message": f"Odoo Init Error: {init_error}"}))
        else:
            print(json.dumps({"success": False, "message": "Could not fetch BCV rate"}))
            
    elif args.update:
        if rate > 0:
            if updater:
                result = updater.update_rates(rate)
                print(json.dumps({"rate": rate, "result": result}))
            else:
                 print(json.dumps({"rate": rate, "result": {"success": False, "message": f"Odoo Init Error: {init_error}"}}))
        else:
            print(json.dumps({"success": False, "message": "Could not fetch BCV rate"}))
    else:
        # Default: just print rate (dry run)
        print(json.dumps({"rate": rate}))
