from pprint import pprint
import os
import requests
import time
import json

from virtuals_acp import VirtualsACP, ACPJob, ACPJobPhase
from virtuals_acp.env import EnvSettings

from dotenv import load_dotenv
load_dotenv(override=True)

def predict_volatility(symbol: str, horizon: int):

    XTREAMLY_BASE_URL = os.getenv("XTREAMLY_BASE_URL")
    XTREAMLY_API_KEY = os.getenv("XTREAMLY_API_KEY")

    if not XTREAMLY_API_KEY or not XTREAMLY_BASE_URL:
        raise EnvironmentError('Missing environment variables: XTREAMLY_API_KEY or XTREAMLY_API_BASE_URL')

    url = XTREAMLY_BASE_URL + '/volatility_prediction'
    headers = {
        'x-api-key': XTREAMLY_API_KEY
    }
    params = {
        'symbol': symbol,
        'horizon': f'{horizon}min'
    }
    print("Predicting volatility for symbol:")
    pprint(params)

    res = requests.get(url, params=params, headers=headers)
    # res.raise_for_status()
    if res.status_code != 200:
        return {
            'status': 'error',
            'message': f"Error fetching volatility: {res.text}"
        }

    return {
        'status': 'success',
        'message': res.json(),
    }


def seller():
    env = EnvSettings()

    def on_new_task(job: ACPJob):
        # Convert job.phase to ACPJobPhase enum if it's an integer
        if job.phase == ACPJobPhase.REQUEST:
            # Check if there's a memo that indicates next phase is NEGOTIATION
            for memo in job.memos:
                if memo.next_phase == ACPJobPhase.NEGOTIATION:
                    job.respond(True)
                    break
        elif job.phase == ACPJobPhase.TRANSACTION:
            # Check if there's a memo that indicates next phase is EVALUATION
            for memo in job.memos:
                if memo.next_phase == ACPJobPhase.EVALUATION:
                    print("Delivering job", job)
                    first_memo = job.memos[0]
                    content = json.loads(first_memo.content)
                    pprint("Content")
                    pprint(content)

                    volatility_res = predict_volatility(
                        symbol=content['symbol'],
                        horizon=content['horizon_min']
                    )
                    pprint("Volatility Result")
                    pprint(volatility_res)

                    delivery_data = {
                        "type": "object",
                        "value": {
                            'status': volatility_res['status'],
                            'message': volatility_res['message']
                        }
                    }

                    job.deliver(json.dumps(delivery_data))
                    break
                
    if env.WHITELISTED_WALLET_PRIVATE_KEY is None:
        raise ValueError("WHITELISTED_WALLET_PRIVATE_KEY is not set")
    if env.SELLER_ENTITY_ID is None:
        raise ValueError("SELLER_ENTITY_ID is not set")

    acp_client = VirtualsACP(
        wallet_private_key=env.WHITELISTED_WALLET_PRIVATE_KEY,
        agent_wallet_address=env.SELLER_AGENT_WALLET_ADDRESS,
        on_new_task=on_new_task,
        entity_id=env.SELLER_ENTITY_ID
    )

    print(acp_client.entity_id)
    
    while True:
        print("Waiting for new task...")
        time.sleep(10)

if __name__ == "__main__":
    seller()
