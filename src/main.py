import asyncio
from viam.module.module import Module
try:
    from models.google_calender_service import GoogleCalenderService
except ModuleNotFoundError:
    # when running as local module with run.sh
    from .models.google_calender_service import GoogleCalenderService


if __name__ == '__main__':
    asyncio.run(Module.run_from_registry())
