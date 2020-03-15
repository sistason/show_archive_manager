import asyncio
import aiohttp
import requests
import logging
import bs4
import re


class PirateBayResult:
    def __init__(self, beautiful_soup_tag):
        self.title = self.magnet = ''
        self.seeders = self.leechers = 0
        try:
            tds = beautiful_soup_tag.find_all('td')
            self.title = tds[1].a.text
            self.magnet = tds[1].find_all('a')[1].attrs.get('href')
            self.seeders = int(tds[-2].text)
            self.leechers = int(tds[-1].text)
        except (IndexError, ValueError, AttributeError):
            return

    def __bool__(self):
        return bool(self.title)


class PiratebayGrabber:
    proxy_url = "http://proxybay.one"

    def __init__(self, event_loop):
        self.event_loop = event_loop
        self.aiohttp_session = None
        self.max_simultaneous_requests = asyncio.Semaphore(10)

        self.parser = PirateBayParser()
        self.proxies = self.setup_proxies()

    def setup_proxies(self):
        ret = requests.get(self.proxy_url)
        if ret.ok:
            bs4_response = bs4.BeautifulSoup(ret.text, "lxml")
            proxylist = bs4_response.find('table', attrs={'id': 'proxyList'})
            return [p.td.a.attrs.get('href') for p in proxylist.find_all('tr') if p.td]

    async def close(self):
        if self.aiohttp_session is not None:
            await self.aiohttp_session.close()

    async def _make_request(self, url):
        async with self.max_simultaneous_requests:
            if self.aiohttp_session is None:
                self.aiohttp_session = aiohttp.ClientSession(loop=self.event_loop)
            for retry in range(3):
                try:
                    async with self.aiohttp_session.post(url, timeout=5, ssl=False) as r_:
                        text = await r_.text()
                        if r_.status == 200:
                            return text
                        if r_.status == 404:
                            continue
                        else:
                            logging.warning('{} returned status "{}", parser corrupt?'.format(self.proxy_url, r_.status))
                except (asyncio.TimeoutError, aiohttp.ClientConnectionError):
                    await asyncio.sleep(1)
                except Exception as e:
                    logging.debug(
                        'Caught Exception "{}" while making a get-request to "{}"'.format(e.__class__, url))
                    return
            logging.warning('Connection to {} failed. Site down?'.format(self.proxy_url))

    async def search(self, show, object_):
        query = "{} {}".format(show.get_search_query(), object_.str_short())
        query = re.sub(r'[^\w\d\s.]', '', query)
        for proxy_url in self.proxies:
            logging.debug('Searching {} for "{}"'.format(proxy_url, query))
            response = await self._make_request(proxy_url + '/search/{}/0/99/200'.format(query))
            if response:
                return self.parser.parse_piratebay_response(response)
        return []


class PirateBayParser:
    @staticmethod
    def parse_piratebay_response(text):
        bs4_response = bs4.BeautifulSoup(text, "lxml")
        main_table = bs4_response.find('table', attrs={'id': 'searchResult'})
        if main_table:
            return [PirateBayResult(tag) for tag in main_table.find_all('tr')[1:]]
        return []
