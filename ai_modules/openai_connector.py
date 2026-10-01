from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
def zai_connector(prompt):
    """ Utilize Zai OpenAI compatible endpoint to query the glm 5.3 flash model using prompt generated from the create_prompt module

    Arg:
    User and System prompt in the format:
    [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]

    Returns:
    LLM response
    """
    api_key = os.getenv("ZAI_KEY")
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.z.ai/api/coding/paas/v4/" 
    )

    response = client.chat.completions.create(
        model="glm-5.3-flash",
        messages=prompt
    )

    return response.choices[0].message.content

