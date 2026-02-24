import os
from openai import OpenAI

def llm(system, user):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL","gpt-4.1-mini"),
        messages=[
            {"role":"system","content":system},
            {"role":"user","content":user}
        ],
        temperature=0.3
    )
    return resp.choices[0].message.content
