import re
import html2text
import async_timeout

from urllib.parse import urljoin
from aiohttp import ClientSession, web
from itertools import cycle

SITE_URL = "https://lifehacker.ru"
LOCAL_URL = "http://0.0.0.0:8080"
REGEX_LINKS = r"(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)"
EMOJI_LIST = ["😀", "😃 ", "😄", " 😁", "😆", " 😅", "😂", "🤣", "😇", "😉", "😊", "🙂"]
TYPE_MODIF = "text/html"
WORD_LENGTH = 6

routes = web.RouteTableDef()


def re_links_as_empty(text: str) -> str:
    return re.sub(REGEX_LINKS, "", text)


def re_check_word(word: str) -> list:
    return re.findall(r"\b\w+\b", re_links_as_empty(word))


def get_validated_words(text: str) -> list:
    all_words = html2text.html2text(text).replace("\n", "").split(" ")
    return [word for i in all_words for word in re_check_word(i) if len(word) == WORD_LENGTH]


def re_links_as_local(text: str, old_link: str, new_link: str) -> str:
    return re.sub(rf"\b{old_link}\b", new_link, text)


def get_modified_text(text: str) -> str:
    words = get_validated_words(text=text)
    for word, emoji in zip(set(words), cycle(EMOJI_LIST)):
        text = re.sub(rf"\b{word}\b", f"{word}{emoji}", text)
    return re_links_as_local(text=text, old_link=SITE_URL, new_link=LOCAL_URL)


@routes.view("/{path:.*}")
class Proxy(web.View):
    async def get_remote_text(self, url: str) -> tuple:
        async with ClientSession() as session, async_timeout.timeout(30):
            async with session.get(url) as resp:
                return (
                    get_modified_text(text=await resp.text())
                    if resp.content_type == TYPE_MODIF
                    else await resp.read(),
                    resp.content_type,
                )

    async def get(self):
        url = urljoin(SITE_URL, self.request.match_info["path"])
        text, content_type = await self.get_remote_text(url=url)
        return web.Response(body=text, content_type=content_type)


if __name__ == "__main__":
    app = web.Application()
    app.router.add_routes(routes)
    web.run_app(app)
