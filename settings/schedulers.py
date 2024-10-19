from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from settings import load_table
from settings.utils import send_statistics_to_users, repeat_send_problems_advertisements


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


def schedule_problems_advertisements(bot, chats_idx):
    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    scheduler = AsyncIOScheduler(timezone=vladivostok_tz)
    scheduler.add_job(
        repeat_send_problems_advertisements,
        CronTrigger(hour='7-23', minute=30, timezone=vladivostok_tz),
        args=[bot, chats_idx]
    )
    scheduler.start()
