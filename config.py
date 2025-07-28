import os

import logfire
from dotenv import load_dotenv

load_dotenv(override=True)

logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))
logfire.instrument_pydantic_ai()
