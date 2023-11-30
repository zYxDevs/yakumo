#!/usr/bin/env python
##########################################################################
##########################################################################
####                                                                  ####
####                               YAKUMO                             ####
####                 AUTOMATIC PROXY GRABBER + CHECKER                ####
####                                                                  ####
####                         by elliottophellia                       ####
####                                                                  ####
##########################################################################
####             https://github.com/elliottophellia/yakumo            ####
##########################################################################
####                Buy Me A Coffie : https://rei.my.id               ####
##########################################################################
####                             Credits to:                          ####
####           mmpx12, monosans, TheSpeedX, hookzof, Zaeem20          ####
##########################################################################


import os
import re
import ujson
import time
import shutil
import asyncio
import aiohttp
import aiohttp_socks
from pathlib import Path

sem = asyncio.Semaphore(500)

RED = "\033[31m"
CLEAR = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"

class SessionPool:
    def __init__(self, size):
        self.sessions = [aiohttp.ClientSession() for _ in range(size)]
        self.index = 0

    async def get(self, proxy=None):
        if proxy:
            connector = aiohttp_socks.ProxyConnector.from_url(proxy)
            session = aiohttp.ClientSession(connector=connector)
        else:
            session = self.sessions[self.index]
            self.index = (self.index + 1) % len(self.sessions)
        return session

    async def close(self):
        for session in self.sessions:
            await session.close()

async def check_proxy(type, proxy, pool):
    async with sem:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            session = await pool.get(f"{type}://{proxy}")
            async with session.get("https://ipinfo.io/json", timeout=timeout) as response:
                try:
                    result = ujson.loads(await response.text())
                    ip = re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", proxy)
                    if result["ip"] == ip[0]:
                        print(
                            f"{GREEN}[+]{CLEAR}[{type}] {proxy} is {GREEN}live{CLEAR}"
                        )
                        country_dir = (
                            f'results/{type}/country/{result["country"]}'
                        )
                        os.makedirs(country_dir, exist_ok=True)
                        with open(
                            f'{country_dir}/{type}_{result["country"]}_checked.txt',
                            "a",
                        ) as f:
                            f.write(proxy + "\n")
                        with open(
                            f"results/{type}/global/{type}_checked.txt", "a"
                        ) as f:
                            f.write(proxy + "\n")
                    else:
                        print(f"{RED}[-]{CLEAR}[{type}] {proxy} is {RED}dead{CLEAR}")
                except ValueError:
                    print(
                        f"{YELLOW}[!]{CLEAR}[{type}] {proxy} is {YELLOW}returned non-JSON response{CLEAR}"
                    )
        except Exception as e:
            print(f"{RED}[-]{CLEAR}[{type}] Invalid proxy format: {proxy}. Error: {str(e).encode('utf-8', 'ignore').decode('utf-8')}")
        finally:
            if session:
                await session.close()
            rmold = Path(f'results/{type}/global/{type}.txt')
            if rmold.exists():
                rmold.unlink()

async def checker(type, pool):
    with open(f"results/{type}/global/{type}.txt", "r") as f:
        data = f.read().split("\n")
    data = [proxy for proxy in data if proxy]
    print(
        f"{YELLOW}[>]{CLEAR} {GREEN}{len(data)}{CLEAR} {type} proxies will be checked"
    )
    tasks = [check_proxy(type, i, pool) for i in data]
    for i in range(0, len(tasks), 100):
        await asyncio.gather(*tasks[i : i + 100])

async def fetch(url, pool):
    session = await pool.get()
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()
    except:
        print(f"An error occurred while fetching {url}.")
        return None

async def fetch_all(urls, pool):
    tasks = [fetch(url, pool) for url in urls]
    results = await asyncio.gather(*tasks)
    return results


sources = {
    "http": [
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/https.txt",
        "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/http.txt"
    ],
    "socks4": [
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/socks4.txt"
    ],
    "socks5": [
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
        "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/socks5.txt"
    ],
}


def handle_exception(loop, context):
    exception = context.get("exception")
    if isinstance(exception, ConnectionResetError):
        print(f"{RED}[-]{CLEAR} Connection was reset by the remote host")
    else:
        loop.default_exception_handler(context)


async def main():
    start_time = time.time()

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

    pool = SessionPool(100)

    if not os.path.exists("results"):
        os.makedirs("results")
        print(f"{GREEN}[+]{CLEAR} created new results directory")
    else:
        shutil.rmtree("results")
        print(f"{GREEN}[+]{CLEAR} deleted old results directory")

    for type, urls in sources.items():
        if not os.path.exists(f"results/{type}/global"):
            os.makedirs(f"results/{type}/global")

        results = await fetch_all(urls, pool)
        proxies = set()

        for result in results:
            if result:
                proxies.update(re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b:\d+", result))

        with open(f"results/{type}/global/{type}.txt", "w") as f:
            f.write("\n".join(proxies))

        print(f"{YELLOW}[>]{CLEAR} {GREEN}{len(proxies)}{CLEAR} {type} proxies grabbed")

        await checker(type, pool)

    await pool.close()

    print(f"{YELLOW}[>]{CLEAR} Done in {(time.time() - start_time)/60} minutes")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
