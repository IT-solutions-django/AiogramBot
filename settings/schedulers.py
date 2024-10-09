from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from settings.utils import send_statistics_to_users


def schedule_daily_statistics(bot):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Vladivostok'))
    scheduler.add_job(send_statistics_to_users, 'cron', hour=21, minute=0, args=[bot])
    scheduler.start()
