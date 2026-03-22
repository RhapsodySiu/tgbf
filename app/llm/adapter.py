import json
from openai import AsyncOpenAI

from app.config import settings

class LLMAdapter:
    def __init__(self, base_url: str, api_key: str, model: str, max_tokens: int, temperature: float):
        self.client: AsyncOpenAI = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.model: str = model
        self.max_tokens: int = max_tokens
        self.temperature: float = temperature
    
    async def chat(self, messages: list[dict]) -> str:
        # messages format: [{"role": "system", "content": "..."}, 
        #                    {"role": "user", "content": "..."},
        #                    {"role": "assistant", "content": "..."}]
        # call client.chat.completions.create(...)
        # return the reply string only

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=1.0, # Nucleus sampling???
                n=1,
                stop=["<END>", "\n\nUser:"],
            )

            reply_text = response.choices[0].message.content.strip()
            print("Raw model output:", reply_text)

            return reply_text

        except Exception as e:
            print(f"Error while generating chat completion: {e}")
            return "Error while generating response. Please try later."

llm = LLMAdapter(
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
    model=settings.llm_model,
    max_tokens=settings.llm_max_tokens,
    temperature=settings.llm_temperature,
)