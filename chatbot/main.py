import uvicorn
from chatbot.app import create_app
import logging

logging.basicConfig(level=logging.INFO)

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

