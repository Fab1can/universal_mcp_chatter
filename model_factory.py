from models.openai import OpenAIModel
from models.gemini import GeminiModel
from models.anthropic import AnthropicModel

class ModelFactory:
    def __init__(self):
        self.format = None
        self.max_tokens = None
        self.temperature = None
        self.name = None
        self.url = None
        self.api_key = None
        self.system_prompt = ""
        self.max_tries = 50
        self.wait_seconds = 6
        self.summarizer_system_prompt = None
        self.summarizer_user_prompt = None
        self.summarizer_max_tokens = None
        self.summarizer_temperature = 0.3
        self.assistant_print = None
        self.system_print = None
        self.error_print = None
    
    def set_openai_api_key(self, api_key: str):
        self.format = "openai"
        self.api_key = api_key
        self.url = None
    
    def set_openai_url(self, url: str):
        self.format = "openai"
        self.url = url
        self.api_key = None
    
    def set_gemini_api_key(self, api_key: str):
        self.format = "gemini"
        self.api_key = api_key
        self.url = None
    
    def set_anthropic_api_key(self, api_key: str):
        self.format = "anthropic"
        self.api_key = api_key
        self.url = None
    
    def set_name(self, name: str):
        self.name = name

    def set_max_tokens(self, max_tokens: int):
        self.max_tokens = max_tokens
    
    def set_temperature(self, temperature: float):
        self.temperature = temperature
    
    def set_prints(self, assistant_print, system_print, error_print):
        self.assistant_print = assistant_print
        self.system_print = system_print
        self.error_print = error_print
    
    def set_summarizer_max_tokens(self, max_tokens: int):
        self.summarizer_max_tokens = max_tokens

    def set_summarizer_language(self, language: str):
        if self.summarizer_max_tokens is None:
            raise ValueError("You must call set_summarizer_max_tokens before setting the language")
        if language.lower() == "english":
            self.summarizer_system_prompt = f"You are an assistant that summarizes conversations into a single text containing the essential points, prioritizing the latest exchanged messages.\nThe new text must be at most {self.summarizer_max_tokens} tokens long"
            self.summarizer_user_prompt = "Briefly summarize the following conversation:\n"
        elif language.lower() == "italian":
            self.summarizer_system_prompt = f"Sei un assistente che riassume le conversazioni in un unico testo che contiene i punti essenziali dando priorità a gli ultimi messaggi scambiati.\nIl nuovo testo deve essere lungo massimo {self.summarizer_max_tokens} tokens"
            self.summarizer_user_prompt = "Riassumi brevemente la seguente conversazione:\n"
        else:
            raise ValueError("Unsupported language for summarizer")
    
    def set_max_tries(self, max_tries: int):
        self.max_tries = max_tries
    
    def set_wait_seconds(self, wait_seconds: int):
        self.wait_seconds = wait_seconds
    
    def set_system_prompt(self, system_prompt: str):
        self.system_prompt = system_prompt
    
    def build(self):
        if self.format is None:
            raise ValueError("Model format not set")
        if self.max_tokens is None:
            raise ValueError("You must call set_max_tokens before building the model")
        if self.temperature is None:
            raise ValueError("You must call set_temperature before building the model")
        if self.name is None:
            raise ValueError("You must call set_name before building the model")
        if self.assistant_print is None or self.system_print is None or self.error_print is None:
            raise ValueError("You must call set_prints before building the model")

        # Ensure summarizer is always configured
        if self.summarizer_max_tokens is None:
            # Default to half of max_tokens, minimum 64
            self.summarizer_max_tokens = max(64, self.max_tokens // 2)
        if self.summarizer_system_prompt is None or self.summarizer_user_prompt is None:
            # Default language for summarizer prompts
            self.set_summarizer_language("italian")
        if self.format == "openai":
            if self.api_key is None and self.url is None:
                raise ValueError("You must call set_openai_api_key or set_openai_url before building the model")
            return OpenAIModel(
                format=self.format,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                name=self.name,
                url=self.url,
                api_key=self.api_key,
                system_prompt=self.system_prompt,
                max_tries=self.max_tries,
                wait_seconds=self.wait_seconds,
                summarizer_system_prompt=self.summarizer_system_prompt,
                summarizer_user_prompt=self.summarizer_user_prompt,
                summarizer_max_tokens=self.summarizer_max_tokens,
                summarizer_temperature=self.summarizer_temperature,
                assistant_print=self.assistant_print,
                system_print=self.system_print,
                error_print=self.error_print
            )
        elif self.format == "gemini":
            if self.api_key is None:
                raise ValueError("You must call set_gemini_api_key before building the model")
            return GeminiModel(
                format=self.format,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                name=self.name,
                url=self.url,
                api_key=self.api_key,
                system_prompt=self.system_prompt,
                max_tries=self.max_tries,
                wait_seconds=self.wait_seconds,
                summarizer_system_prompt=self.summarizer_system_prompt,
                summarizer_user_prompt=self.summarizer_user_prompt,
                summarizer_max_tokens=self.summarizer_max_tokens,
                summarizer_temperature=self.summarizer_temperature,
                assistant_print=self.assistant_print,
                system_print=self.system_print,
                error_print=self.error_print
            )
        elif self.format == "anthropic":
            if self.api_key is None:
                raise ValueError("You must call set_anthropic_api_key before building the model")
            return AnthropicModel(
                format=self.format,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                name=self.name,
                url=self.url,
                api_key=self.api_key,
                system_prompt=self.system_prompt,
                max_tries=self.max_tries,
                wait_seconds=self.wait_seconds,
                summarizer_system_prompt=self.summarizer_system_prompt,
                summarizer_user_prompt=self.summarizer_user_prompt,
                summarizer_max_tokens=self.summarizer_max_tokens,
                summarizer_temperature=self.summarizer_temperature,
                assistant_print=self.assistant_print,
                system_print=self.system_print,
                error_print=self.error_print
            )
        else:
            raise ValueError(f"Unsupported model format: {self.format}")
