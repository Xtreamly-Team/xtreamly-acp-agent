import json
from pprint import pprint
from datetime import datetime, timedelta
import time
from typing import Optional

from virtuals_acp import ACPMemo
from virtuals_acp.client import VirtualsACP
from virtuals_acp.job import ACPJob
from virtuals_acp.models import ACPAgentSort, ACPJobPhase
from virtuals_acp.env import EnvSettings

from dotenv import load_dotenv

load_dotenv(override=True)

def test_buyer():
    env = EnvSettings()
    def on_new_task(job: ACPJob, memo_to_sign: Optional[ACPMemo] = None):
        if job.phase == ACPJobPhase.NEGOTIATION:
            # Check if there's a memo that indicates next phase is TRANSACTION
            for memo in job.memos:
                if memo.next_phase == ACPJobPhase.TRANSACTION:
                    print("Paying job", job.id)
                    job.pay(job.price)
                    break
        elif job.phase == ACPJobPhase.COMPLETED:
            print("JOB COMPLETED \n")
            print(job.deliverable)
            volatility_res = json.loads(job.deliverable)
            pprint(volatility_res['value'])
            print("Job completed", job)
        elif job.phase == ACPJobPhase.REJECTED:
            print("Job rejected", job)
    
    def on_evaluate(job: ACPJob):
        print("Evaluation function called", job)
        # Find the deliverable memo
        for memo in job.memos:
            if memo.next_phase == ACPJobPhase.COMPLETED:
                # Evaluate the deliverable by accepting it
                print("EVALUATION DONE")
                job.evaluate(True)
                break
    
    if env.WHITELISTED_WALLET_PRIVATE_KEY is None:
        raise ValueError("WHITELISTED_WALLET_PRIVATE_KEY is not set")
    if env.BUYER_AGENT_WALLET_ADDRESS is None:
        raise ValueError("BUYER_AGENT_WALLET_ADDRESS is not set")
    if env.BUYER_ENTITY_ID is None:
        raise ValueError("BUYER_ENTITY_ID is not set")
    
    acp = VirtualsACP(
        wallet_private_key=env.WHITELISTED_WALLET_PRIVATE_KEY,
        agent_wallet_address=env.BUYER_AGENT_WALLET_ADDRESS,
        on_new_task=on_new_task,
        on_evaluate=on_evaluate,
        entity_id=env.BUYER_ENTITY_ID
    )

    predictive_agent = acp.get_agent('0x6F542716daf62768B6E2e0097b157f582B1a7391')
    if not predictive_agent:
        return
    pprint(predictive_agent)
    
    predict_volatility_job_offering = [offering for offering in predictive_agent.offerings if offering.name.lower() == "Predict Volatility".lower()][0]

    pprint(predict_volatility_job_offering)

    volatility_job = predict_volatility_job_offering.initiate_job(
        service_requirement={
            "symbol": "HBAR", "horizon_min": 15,
        },
        evaluator_address=env.BUYER_AGENT_WALLET_ADDRESS,
        expired_at=datetime.now() + timedelta(days=1)
    )
    #
    print(f"Job {volatility_job} initiated")
    
    while True:
        print("Listening for next steps...")
        time.sleep(30)

if __name__ == "__main__":
    test_buyer()
