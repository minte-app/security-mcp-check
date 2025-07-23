import os
from dotenv import load_dotenv
import logfire

load_dotenv(override=True)

logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))
logfire.instrument_pydantic_ai()