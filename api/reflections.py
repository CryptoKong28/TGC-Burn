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

        daily_summary = {
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
        
        return daily_summary

    except Exception as e:
        return {"error": str(e)}

# Vercel expects the main function to be `handler`
def handler(request):
    contract_address = request.get('contract_address', '0x94534EeEe131840b1c0F61847c572228bdfDDE93')
    addresses = request.get('addresses', ["0x0000000000000000000000000000000000000369"])
    rpc_url = request.get('rpc_url', 'https://rpc.pulsechain.com')
    
    response_data = track_daily_reflections(contract_address, addresses, rpc_url)
    
    return {
        "statusCode": 200,
        "body": json.dumps(response_data)
    }
