from http.server import BaseHTTPRequestHandler
from web3 import Web3
from decimal import Decimal
import json
import os
from datetime import datetime

def load_history():
    if os.path.exists('/tmp/reflection_history.json'):
        with open('/tmp/reflection_history.json', 'r') as f:
            return json.load(f)
    return {}

def save_history(history):
    with open('/tmp/reflection_history.json', 'w') as f:
        json.dump(history, f, indent=4)

def track_daily_reflections(contract_address, wallet_addresses, rpc_url):
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            raise Exception("Failed to connect to the blockchain")

        abi = [
            {
                "inputs": [], "name": "decimals", "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
                "stateMutability": "view", "type": "function"
            },
            {
                "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
                "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view", "type": "function"
            },
            {
                "inputs": [], "name": "symbol", "outputs": [{"internalType": "string", "name": "", "type": "string"}],
                "stateMutability": "view", "type": "function"
            }
        ]
        
        contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=abi)
        symbol = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        
        today = datetime.now().strftime('%Y-%m-%d')
        history = load_history()
        if today not in history:
            history[today] = {}
            
        total_reflections = {}
        for address in wallet_addresses:
            checksum_address = w3.to_checksum_address(address)
            current_balance = contract.functions.balanceOf(checksum_address).call()
            adjusted_balance = Decimal(current_balance) / Decimal(10 ** decimals)
            
            if address not in history[today]:
                history[today][address] = {
                    'start_balance': float(adjusted_balance),
                    'end_balance': float(adjusted_balance),
                    'reflections': 0
                }
            else:
                history[today][address]['end_balance'] = float(adjusted_balance)
                history[today][address]['reflections'] = history[today][address]['end_balance'] - history[today][address]['start_balance']
            
            total_reflections[address] = 0
            for date in history:
                if address in history[date]:
                    total_reflections[address] += history[date][address]['reflections']
                    
        save_history(history)
        
        return {
            "symbol": symbol,
            "date": today,
            "summary": [
                {
                    "address": address,
                    "today_reflections": history[today][address]['reflections'],
                    "total_reflections": total_reflections[address]
                }
                for address in wallet_addresses
            ]
        }
    except Exception as e:
        return {"error": str(e)}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Default values
        contract_address = '0x94534EeEe131840b1c0F61847c572228bdfDDE93'
        addresses = ["0x0000000000000000000000000000000000000369"]
        rpc_url = 'https://rpc.pulsechain.com'
        
        try:
            # Parse query parameters if they exist
            if '?' in self.path:
                from urllib.parse import parse_qs, urlparse
                query = parse_qs(urlparse(self.path).query)
                
                if 'contract_address' in query:
                    contract_address = query['contract_address'][0]
                if 'addresses' in query:
                    addresses = query['addresses'][0].split(',')
                if 'rpc_url' in query:
                    rpc_url = query['rpc_url'][0]
            
            response_data = track_daily_reflections(contract_address, addresses, rpc_url)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(response_data).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def handler(request, context):
    return Handler.do_GET(Handler())
