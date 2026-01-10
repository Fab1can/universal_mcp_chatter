from model import Model
from utils import normalize_args

import logging
import asyncio
from openai import OpenAI

def mcp_tools_to_openai_tools(mcp_tools):
    converted = []
    for t in mcp_tools:
        converted.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema if hasattr(t, "input_schema") else {"type": "object", "properties": {}}
            }
        })
    return converted

class OpenAIModel(Model):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = None
        if self.url is None or self.url=="":
            self.openai = OpenAI(api_key=self.api_key)
        else:
            self.openai = OpenAI(api_key=self.api_key, base_url=self.url)
        self.messages = [{
            "role": "system",
            "content": self.system
        }]

    def init(self):
        super().init()
        
    
    def init_tools(self, tools):
        super().init_tools(tools)
        self.available_tools = mcp_tools_to_openai_tools(tools)
    
    def set_system(self, system_prompt):
        super().set_system(system_prompt)
        self.messages[0] = {
            "role": "system",
            "content": system_prompt
        }
    
    async def create_message(self):
        super().create_message()
        tries = 0
        while tries < self.max_tries:
            try:
                tries += 1
                return self.openai.chat.completions.create(
                    model=self.name,
                    messages=self.messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    tools=self.available_tools
                ).choices[0]
            
            except Exception as e:
                if not hasattr(e, "body"):
                    self.error_print(f"{e}")
                else:
                    if "error" in e.body and "message" in e.body["error"]:
                        self.error_print(f"{e.body['error']['message']}")
                    else:
                        self.error_print(f"{e}")
            await asyncio.sleep(self.wait_seconds)
        self.error_print("Maximum number of attempts reached, please try again later")
    
    async def process_query(self, query):
        """Process a query using a model and the available tools"""
        await self._examine_query(query)

        tool_use_detected = True
        # Interaction loop with the model
        while tool_use_detected:
            # Check if summarization is needed
            next_message = [{
                "role": "user",
                "content": query
            }]
            if self.check_summarize_needed(next_message):
                await self.summarize()
            # Request to the model
            self.response = await self.create_message()

            tool_use_detected = False

            if self.response.finish_reason == "stop":
                # The answer is complete; there are no tools to call
                self.messages.append({
                    "role": "assistant",
                    "content": self.response.message.content
                })
                self.assistant_print(self.response.message.content)
            elif self.response.finish_reason == "tool_calls":
                tool_use_detected = True
                tool_calls = self.response.message.tool_calls
                self.messages.append(self.response.message)
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = normalize_args(tool_call.function.arguments)
                    result = await self.client.call_tool(tool_name, tool_args)

                    self.messages.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": result.content[0].text
                    })
    
    async def summarize(self):
        logging.debug("Started summarization")
        history = [
            {"role":"system", "content": self.summarizer_system_prompt},
            {"role": "user", "content": f"{self.summarizer_user_prompt}{str(self.messages[1:-2])}"}
        ]
        summarizer = self.openai.chat.completions.create(
            model=self.name,
            messages=history,
            max_tokens=self.summarizer_max_tokens,
            temperature=self.summarizer_temperature
        )
        summary = summarizer.choices[0].message.content
        logging.debug(f"Summary produced:{summary}")
        new_messages = [
        {
            "role": "system",
            "content": self.system
        },
        {
            "role": "system",
            "content": summary
        }]
        new_messages.extend(self.messages[-2:])
        self.messages = new_messages
        logging.debug("Finished summarization")