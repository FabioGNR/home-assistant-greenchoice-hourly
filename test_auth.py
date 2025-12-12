import asyncio
from aiohttp import ClientSession
from custom_components.greenchoice.auth import setup_auth
import os


username = os.environ.get("GREENCHOICE_USERNAME") or input("Email: ")
password = os.environ.get("GREENCHOICE_PASSWORD") or input("Password: ")


async def main():
    session = ClientSession()
    async with session:
        await setup_auth(session, username, password)


if __name__ == "__main__":
    asyncio.run(main())
