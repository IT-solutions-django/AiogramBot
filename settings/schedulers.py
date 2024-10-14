from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from settings import load_table
from settings.utils import send_statistics_to_users


def schedule_daily_statistics(bot):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Vladivostok'))
    scheduler.add_job(send_statistics_to_users, 'cron', hour=21, minute=0, args=[bot])
    scheduler.start()


def schedule_daily_data_loading():
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Vladivostok'))
    scheduler.add_job(
        load_table.load_companies_from_sheet,
        'cron',
        hour=20,
        minute=50,
        args=[load_table.service]
    )
    scheduler.start()
