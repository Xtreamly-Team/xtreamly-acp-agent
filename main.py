import os
from typing import Optional
from pydantic import BaseModel
import requests
import json

import threading
import time
from collections import deque
from typing import Optional, Deque, Tuple

from virtuals_acp import ACPMemo, IDeliverable, VirtualsACP, ACPJob, ACPJobPhase
from virtuals_acp.env import EnvSettings

from dotenv import load_dotenv

import logging
load_dotenv(override=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)

logger.info("Environment variables loaded successfully")

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
        'horizon': f'{horizon}'
    }
    logger.info("Predicting volatility for symbol:")
    logger.info(params)

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

def seller(use_thread_lock: bool = True):
    env = EnvSettings()

    if env.WHITELISTED_WALLET_PRIVATE_KEY is None:
        raise ValueError("WHITELISTED_WALLET_PRIVATE_KEY is not set")
    if env.SELLER_AGENT_WALLET_ADDRESS is None:
        raise ValueError("SELLER_AGENT_WALLET_ADDRESS is not set")
    if env.SELLER_ENTITY_ID is None:
        raise ValueError("SELLER_ENTITY_ID is not set")

    job_queue: Deque[Tuple[ACPJob, Optional[ACPMemo]]] = deque()
    job_queue_lock = threading.Lock()
    job_event = threading.Event()

    def safe_append_job(job, memo_to_sign: Optional[ACPMemo] = None):
        if use_thread_lock:
            print(f"Acquiring lock to append job {job.id}")
            with job_queue_lock:
                print(f"Lock acquired, appending job {job.id} to queue")
                job_queue.append((job, memo_to_sign))
        else:
            job_queue.append((job, memo_to_sign))

    def safe_pop_job():
        if use_thread_lock:
            print(f"[safe_pop_job] Acquiring lock to pop job")
            with job_queue_lock:
                if job_queue:
                    job, memo_to_sign = job_queue.popleft()
                    print(f"Lock acquired, popped job {job.id}")
                    return job, memo_to_sign
                else:
                    print("Queue is empty after acquiring lock")
                    return None, None
        else:
            if job_queue:
                job, memo_to_sign = job_queue.popleft()
                print(f"Popped job {job.id} without lock")
                return job, memo_to_sign
            else:
                print("Queue is empty (no lock)")
                return None, None

    def job_worker():
        while True:
            job_event.wait()
            while True:
                job, memo_to_sign = safe_pop_job()
                if not job:
                    break
                # Process each job in its own thread to avoid blocking
                threading.Thread(target=handle_job_with_delay, args=(job, memo_to_sign), daemon=True).start()
            if use_thread_lock:
                with job_queue_lock:
                    if not job_queue:
                        job_event.clear()
            else:
                if not job_queue:
                    job_event.clear()

    def handle_job_with_delay(job, memo_to_sign):
        try:
            on_new_task(job, memo_to_sign)
            time.sleep(2)
        except Exception as e:
            print(f"\u274c Error processing job: {e}")

    def on_new_task(job: ACPJob, memo_to_sign: Optional[ACPMemo] = None):
        # Convert job.phase to ACPJobPhase enum if it's an integer
        if job.phase == ACPJobPhase.REQUEST:
            # Check if there's a memo that indicates next phase is NEGOTIATION
            for memo in job.memos:
                if memo.next_phase == ACPJobPhase.NEGOTIATION:
                    content = json.loads(memo.content)
                    logger.info("Content")
                    logger.info(content)
                    params = content['serviceRequirement']
                    symbol = params['symbol']
                    if symbol.upper() not in ['BTC', 'ETH', 'SOL']:
                        job.respond(False, None, f"Symbol {symbol} not supported, Supported symbols: [BTC, ETH, SOL]")
                    elif params['horizon_min'] not in [1, 5, 15, 60, 240, 720, 1440]:
                        job.respond(False, None, f"Horizon {params['horizon_min']} not supported. Supported horizons: [1, 5, 15, 60, 240, 720, 1440]")
                    else:
                        job.respond(True)
                    break
        elif job.phase == ACPJobPhase.TRANSACTION:
            # Check if there's a memo that indicates next phase is EVALUATION
            for memo in job.memos:
                if memo.next_phase == ACPJobPhase.EVALUATION:
                    logger.info(f"Delivering job {job}")
                    first_memo = job.memos[0]
                    content = json.loads(first_memo.content)
                    logger.info("Content")
                    logger.info(content)
                    params = content['serviceRequirement']

                    volatility_res = predict_volatility(
                        symbol=params['symbol'],
                        horizon=params['horizon_min']
                    )
                    logger.info("Volatility Result")
                    logger.info(volatility_res)

                    deliverable_data = IDeliverable(
                        type= "object",
                        value={
                            'status': volatility_res['status'],
                            'message': volatility_res['message']
                        }
                    )
                    job.deliver(deliverable_data)
                    break
                
    threading.Thread(target=job_worker, daemon=True).start()

    acp_client = VirtualsACP(
        wallet_private_key=env.WHITELISTED_WALLET_PRIVATE_KEY,
        agent_wallet_address=env.SELLER_AGENT_WALLET_ADDRESS,
        on_new_task=on_new_task,
        entity_id=env.SELLER_ENTITY_ID
    )

    logger.info("Client created successfully")
    logger.info(acp_client.entity_id)

    print("Waiting for new task...")
    threading.Event().wait()
    
    # while True:
    #     logger.info("Waiting for new task...")
    #     time.sleep(10)

if __name__ == "__main__":
    logger.info("Starting seller service...")
    seller()
