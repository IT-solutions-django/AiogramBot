from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from settings import load_table
from settings.utils import send_statistics_to_users, repeat_send_problems_advertisements, \
    send_statistics_to_users_friday, repeat_send_position_advertisements, slow_repeat_send_position_advertisements


def schedule_daily_statistics(bot):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Vladivostok'))
    scheduler.add_job(send_statistics_to_users, 'cron', hour=21, minute=0, args=[bot])
    scheduler.start()


def schedule_daily_data_loading():
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Vladivostok'))
    scheduler.add_job(
        load_table.load_companies_from_sheet,
        'cron',
        minute='0,30',
        args=[load_table.service]
    )
    scheduler.start()


def schedule_problems_advertisements(bot, chats_idx):
    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    scheduler = AsyncIOScheduler(timezone=vladivostok_tz)
    scheduler.add_job(
        repeat_send_problems_advertisements,
        CronTrigger(hour='7-23,0', minute='15,45', timezone=vladivostok_tz),
        args=[bot, chats_idx]
    )
    scheduler.start()


def schedule_daily_statistics_friday(bot):
    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    scheduler = AsyncIOScheduler(timezone=vladivostok_tz)
    scheduler.add_job(
        send_statistics_to_users_friday,
        CronTrigger(day_of_week='fri', hour=20, minute=50, timezone=vladivostok_tz),
        args=[bot]
    )
    scheduler.start()


def schedule_position_advertisements(bot, chats_idx, position_advertisements):
    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    scheduler = AsyncIOScheduler(timezone=vladivostok_tz)
    scheduler.add_job(
        repeat_send_position_advertisements,
        CronTrigger(hour='7-23,0', minute='18,48', timezone=vladivostok_tz),
        args=[bot, chats_idx, position_advertisements]
    )
    scheduler.start()


def schedule_slow_position_advertisements(bot, chats_idx, position_advertisements):
    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    scheduler = AsyncIOScheduler(timezone=vladivostok_tz)
    scheduler.add_job(
        slow_repeat_send_position_advertisements,
        CronTrigger(hour='7-23,0', minute='3,33', timezone=vladivostok_tz),
        args=[bot, chats_idx, position_advertisements]
    )
    scheduler.start()


def schedule_balance_position():
    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    scheduler = AsyncIOScheduler(timezone=vladivostok_tz)
    scheduler.add_job(
        load_table.get_balance_position,
        CronTrigger(hour='7-23,0', minute='1', timezone=vladivostok_tz)
    )
    scheduler.start()
