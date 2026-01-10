import logging
from fastmcp import McpError
import tiktoken
TIKTOKEN = tiktoken.get_encoding("o200k_base")

class Model:
    def __init__(self, format: str, max_tokens: int, temperature: float, name: str, url: str, api_key: str, system_prompt: str, max_tries: int, wait_seconds: int, summarizer_system_prompt: str, summarizer_user_prompt: str, summarizer_max_tokens: int, summarizer_temperature: float, assistant_print, system_print, error_print):
        self.format = format
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.name = name
        self.url = url
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.system = system_prompt
        self.max_tries = max_tries
        self.wait_seconds = wait_seconds
        self.summarizer_system_prompt = summarizer_system_prompt
        self.summarizer_user_prompt = summarizer_user_prompt
        self.summarizer_max_tokens = summarizer_max_tokens
        self.summarizer_temperature = summarizer_temperature
        self.assistant_print = assistant_print
        self.system_print = system_print
        self.error_print = error_print
        self.client = None
        self.response = None
        self.available_tools = None
        self.available_prompts = None
    
    def init(self):
        pass

    def init_tools(self, tools):   
        pass

    def set_system(self, system_prompt: str):
        self.system = system_prompt
    
    def create_message(self):
        pass
    
    def get_user_message(self, query: str):
        return self.get_role_message("user", query)
    
    def get_role_message(self, role: str, content: str):
        return {"role": role, "content": content}
    
    def check_summarize_needed(self, next_message):
        # Summarization must be explicitly configured
        if (
            self.summarizer_max_tokens is None
            or self.summarizer_system_prompt is None
            or self.summarizer_user_prompt is None
        ):
            return False

        try:
            messages_snapshot = list(self.get_messages()) + next_message
        except Exception:
            messages_snapshot = next_message
        if len(TIKTOKEN.encode(str(messages_snapshot))) >= self.max_tokens:
            logging.debug("A summary is needed")
            return True
        return False

    async def _examine_query(self, query):
        message = self.get_user_message(query)
        if isinstance(query, str) and query[:1] == "/":
            try:
                if self.client and hasattr(self.client, "get_prompt"):
                    messages = await self.client.get_prompt(query[1:])
                    for prompt_message in messages.messages:
                        self.messages.append(self.get_role_message(prompt_message.role, prompt_message.content.text))
                else:
                    self.messages.append(message)
            except McpError:
                self.messages.append(message)
        else:
            self.messages.append(message)
    
    async def process_query(self, query):
        pass

    async def summarize(self):
        pass

    def get_messages(self):
        for msg in self.messages:
            yield msg
    
    def set_messages(self, messages):
        self.messages = [{
            "role": "system",
            "content": self.system
        }]
        for message in messages:
            self.messages.append({
                "role": message["role"],
                "content": message["content"]
            })