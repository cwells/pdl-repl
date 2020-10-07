from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

PDL_VERSION = "v5"
PDL_ENRICH_URL = f"https://api.peopledatalabs.com/{PDL_VERSION}/person/enrich"
PDL_SEARCH_URL = f"https://api.peopledatalabs.com/{PDL_VERSION}/person/search"

PROMPT_STYLE = Style.from_dict({
    "completion-menu.completion": "bg:#008888 #ffffff",
    "completion-menu.completion.current": "bg:#00aaaa #000000",
    "scrollbar.background": "bg:#88aaaa",
    "scrollbar.button": "bg:#222222",
})


def toolbar_factory(settings):
    def tool_items(s, prefix=''):
        for k, v in s.items():
            if isinstance(v, dict):
                for item in tool_items(v, prefix=f"{k}."):
                    yield item
            else:
                yield f"{prefix}{k}:{v}"

    def toolbar():
        tools = list(tool_items(settings))
        status = "  ".join(tools)
        return HTML(
            f'<style fg="blue" bg="white">{status:^40}</style>'
            '      '
            'Press [Alt+Enter] to evaluate an expression or [Ctrl+d] to exit.'
        )
    return toolbar


def prompt_continuation(width, line_number, is_soft_wrap):
    return '.' * (width - 1) + ' '

