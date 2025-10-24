from typing import Optional
import json

import threading
from typing import Optional, Deque, Tuple

from virtuals_acp.memo import ACPMemo
from virtuals_acp.job import ACPJob
from virtuals_acp.models import ACPJobPhase, IDeliverable
from virtuals_acp.client import VirtualsACP
from virtuals_acp.env import EnvSettings

from virtuals_acp.contract_clients.contract_client_v2 import ACPContractClientV2

from dotenv import load_dotenv

import logging

from predict import predict_volatility
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("SellerAgent")
logger.setLevel(logging.INFO)


load_dotenv(override=True)
logger.info("Environment variables loaded successfully")

REJECT_JOB = False

def seller():
    env = EnvSettings()

    def on_new_task(job: ACPJob, memo_to_sign: Optional[ACPMemo] = None):
        logger.info(f"[on_new_task] Received job {job.id} (phase: {job.phase})")

        if (
            job.phase == ACPJobPhase.REQUEST
            and memo_to_sign is not None
            and memo_to_sign.next_phase == ACPJobPhase.NEGOTIATION
        ):

            response = False
            logger.info(f"Responding to job {job.id} with requirement: {job.requirement}")
            content = json.loads(memo_to_sign.content)
            logger.info("Content")
            logger.info(content)
            params = content['requirement']
            symbol = params['symbol']
            if symbol.upper() not in ['BTC', 'ETH', 'SOL']:
                job.reject(f"Symbol {symbol} not supported, Supported symbols: [BTC, ETH, SOL]")
            elif params['horizon_min'] not in [1, 5, 15, 60, 240, 720, 1440]:
                job.reject(f"Horizon {params['horizon_min']} not supported. Supported horizons: [1, 5, 15, 60, 240, 720, 1440]")
            else:
                response = True
                job.accept("Job requirement matches agent capability")
                job.create_requirement(f"Job {job.id} accepted, please make payment to proceed")

            logger.info(f"Job {job.id} responded with {response}")

        elif (
            job.phase == ACPJobPhase.TRANSACTION
            and memo_to_sign is not None
            and memo_to_sign.next_phase == ACPJobPhase.EVALUATION
        ):
            # to cater cases where agent decide to reject job after payment has been made
            if REJECT_JOB: # conditional check for job rejection logic
                reason = "Job requirement does not meet agent capability"
                logger.info(f"Rejecting job {job.id} with reason: {reason}")
                job.reject(reason)
                logger.info(f"Job {job.id} rejected")
                return


            content = json.loads(job.memos[0].content)
            logger.info("Content")
            logger.info(content)
            params = content['requirement']

            volatility_res = predict_volatility(
                symbol=params['symbol'],
            )
            logger.info("Volatility Result")
            logger.info(volatility_res)

            deliverable = {
                'status': volatility_res['status'],
                'message': volatility_res['message']
            }

            logger.info(f"Delivering job {job.id} with deliverable {deliverable}")
            job.deliver(deliverable)
            logger.info(f"Job {job.id} delivered")
            return

        elif job.phase == ACPJobPhase.COMPLETED:
            logger.info(f"Job {job.id} completed")

        elif job.phase == ACPJobPhase.REJECTED:
            logger.info(f"Job {job.id} rejected")

    VirtualsACP(
        acp_contract_clients=ACPContractClientV2(
            wallet_private_key=env.WHITELISTED_WALLET_PRIVATE_KEY,
            agent_wallet_address=env.SELLER_AGENT_WALLET_ADDRESS,
            entity_id=env.SELLER_ENTITY_ID
        ),
        on_new_task=on_new_task
    )

    logger.info("Seller agent is running, waiting for new tasks...")
    threading.Event().wait()


if __name__ == "__main__":
    logger.info("Starting seller service...")
    seller()
