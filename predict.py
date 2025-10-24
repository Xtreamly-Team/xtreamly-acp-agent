import os
from dotenv import load_dotenv
import requests
import logging
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("SellerAgent")
logger.setLevel(logging.INFO)

load_dotenv()

def predict_volatility(symbol: str, horizon: int):

    XTREAMLY_BASE_URL = os.getenv("XTREAMLY_BASE_URL")
    XTREAMLY_API_KEY = os.getenv("XTREAMLY_API_KEY")

    if not XTREAMLY_API_KEY or not XTREAMLY_BASE_URL:
        raise EnvironmentError('Missing environment variables: XTREAMLY_API_KEY or XTREAMLY_API_BASE_URL')

    url = XTREAMLY_BASE_URL + '/api/v1/predictions/latest'
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

if __name__ == '__main__':
    res = predict_volatility('ETH', 15)
    print(res)
