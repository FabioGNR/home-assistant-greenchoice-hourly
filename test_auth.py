import asyncio
from custom_components.greenchoice.api import GreenchoiceApi
import os
import logging
from datetime import date, timedelta

logging.basicConfig(level=logging.DEBUG)


username = os.environ.get("GREENCHOICE_USERNAME") or input("Email: ")
password = os.environ.get("GREENCHOICE_PASSWORD") or input("Password: ")


async def main():
    api = GreenchoiceApi(username, password)
    async with api:
        await api.login()
        profiles = await api.get_profiles()
        for i, p in enumerate(profiles, start=1):
            print(
                f"[{i}] Profile: {p.agreement_id} - {p.street} {p.house_number} ({p.energy_supply_status})"
            )
        selected_profile_id = input("Select profile number: ")
        selected_profile = profiles[int(selected_profile_id) - 1]

        consumption = await api.get_hourly_readings(
            selected_profile, date.today() - timedelta(days=3)
        )
        print(selected_profile.street, consumption)


if __name__ == "__main__":
    asyncio.run(main())
