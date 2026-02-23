from openai import OpenAI
import os

def llm_text(system, user):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return resp.output_text
