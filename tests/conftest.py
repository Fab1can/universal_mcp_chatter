import sys
import types


def _install_tiktoken_stub():
    mod = types.ModuleType("tiktoken")

    class DummyEncoding:
        def encode(self, s):
            try:
                return list(s.encode("utf-8"))
            except Exception:
                return []

    def get_encoding(name):
        return DummyEncoding()

    mod.get_encoding = get_encoding
    sys.modules["tiktoken"] = mod


def _install_fastmcp_stub():
    fm = types.ModuleType("fastmcp")

    class McpError(Exception):
        pass

    class Client:
        def __init__(self, url=None, log_handler=None):
            self.url = url
            self.log_handler = log_handler

        # Minimal API used in code under test
        async def list_tools(self):
            return []

        async def list_prompts(self):
            return []

    fm.McpError = McpError
    fm.Client = Client

    # fastmcp.client.logging.LogMessage
    client_mod = types.ModuleType("fastmcp.client")
    logging_mod = types.ModuleType("fastmcp.client.logging")

    class LogMessage:
        def __init__(self, level, data):
            self.level = level
            self.data = data

    logging_mod.LogMessage = LogMessage

    sys.modules["fastmcp"] = fm
    sys.modules["fastmcp.client"] = client_mod
    sys.modules["fastmcp.client.logging"] = logging_mod


def _install_openai_stub():
    mod = types.ModuleType("openai")

    class _ChatCompletions:
        def create(self, **kwargs):
            class _ChoiceMsg:
                def __init__(self):
                    self.content = "summary"
            class _Choice:
                def __init__(self):
                    self.message = _ChoiceMsg()
            class _Resp:
                def __init__(self):
                    self.choices = [_Choice()]
            return _Resp()

    class _Chat:
        def __init__(self):
            self.completions = _ChatCompletions()

    class OpenAI:
        def __init__(self, api_key=None, base_url=None):
            self.api_key = api_key
            self.base_url = base_url
            self.chat = _Chat()

    mod.OpenAI = OpenAI
    sys.modules["openai"] = mod


def _install_anthropic_stub():
    mod = types.ModuleType("anthropic")

    class _Messages:
        def create(self, **kwargs):
            class _R:
                content = []
            return _R()

    class Anthropic:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.messages = _Messages()

    mod.Anthropic = Anthropic
    sys.modules["anthropic"] = mod


def _install_google_genai_stub():
    # Create package 'google'
    google_pkg = types.ModuleType("google")
    genai_mod = types.ModuleType("google.genai")
    types_mod = types.ModuleType("google.genai.types")

    class Part:
        def __init__(self, text=""):
            self.text = text

    class Content:
        def __init__(self, role="user", parts=None):
            self.role = role
            self.parts = parts or []

    class GenerateContentConfig:
        def __init__(self, temperature=None, max_output_tokens=None, tools=None):
            self.temperature = temperature
            self.max_output_tokens = max_output_tokens
            self.tools = tools or []

    class _Client:
        def __init__(self, api_key=None):
            self.api_key = api_key

        class aio:
            class models:
                @staticmethod
                async def generate_content(model=None, contents=None, config=None):
                    class _Resp:
                        class _Cand:
                            class _Content:
                                def __init__(self):
                                    self.parts = [Part(text="")] 

                            def __init__(self):
                                self.content = _Resp._Cand._Content()
                                self.finish_reason = "STOP"
                                self.text = ""

                        def __init__(self):
                            self.candidates = [self._Cand()]

                    return _Resp()

    # expose as google.genai.client.Client
    genai_client_mod = types.ModuleType("google.genai.client")
    genai_client_mod.Client = _Client

    # Wire modules
    sys.modules["google"] = google_pkg
    sys.modules["google.genai"] = genai_mod
    sys.modules["google.genai.types"] = types_mod
    sys.modules["google.genai.client"] = genai_client_mod

    # Bind symbols for "from google import genai" and "from google.genai import types"
    setattr(google_pkg, "genai", genai_mod)
    setattr(genai_mod, "client", genai_client_mod)
    setattr(types_mod, "Part", Part)
    setattr(types_mod, "Content", Content)
    setattr(types_mod, "GenerateContentConfig", GenerateContentConfig)


_install_tiktoken_stub()
_install_fastmcp_stub()
_install_openai_stub()
_install_anthropic_stub()
_install_google_genai_stub()
