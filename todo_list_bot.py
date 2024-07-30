from aiogram import Bot, Dispatcher, types
from aiogram.utils.callback_data import CallbackData

from settings import settings
from task import Task
from task_repository import TaskRepository

import typing

bot = Bot(token=settings["TELEGRAM_TOKEN"])
dispatcher = Dispatcher(bot)
clear_cb = CallbackData("clear", "action")

tasks = []

_repository = TaskRepository()


def _task_dto_to_string(task: Task) -> str:
    status_char = "\u2705" if task.is_done else "\u274c"
    return f"{task.id}: {task.text} | {status_char}"


def _get_keyboard():
    return types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton(
            "Удалить все!", callback_data=clear_cb.new(action="all")
        ),
        types.InlineKeyboardButton(
            "Только завершенные", callback_data=clear_cb.new(action="completed")
        ),
    )


@dispatcher.message_handler(commands=["todo"])
async def create_task(message: types.Message):
    _repository.add_task(message.get_args())
    await message.reply("Добавлена задача")


@dispatcher.message_handler(commands=["list"])
async def get_list(message: types.Message):
    tasks = _repository.get_list()
    if tasks:
        text = "\n".join([_task_dto_to_string(res) for res in tasks])
    else:
        text = "У вас нет задач!"
    await bot.send_message(message.chat.id, text)


@dispatcher.message_handler(commands=["done"])
async def finish_task(message: types.Message):
    try:
        task_ids = [int(id_) for id_ in message.get_args().split(" ")]
        _repository.finish_tasks(task_ids)
        text = f"Завершенные задачи: {task_ids}"
    except ValueError as e:
        text = "Неправильный номер задачи"

    await message.reply(text)


@dispatcher.message_handler(commands=["clear"])
async def clear(message: types.Message):
    await message.reply("Вы хотите удалить ваши задачи?", reply_markup=_get_keyboard())


@dispatcher.callback_query_handler(clear_cb.filter(action=["all", "completed"]))
async def callback_clear_action(
    query: types.CallbackQuery, callback_data: typing.Dict[str, str]
):
    await query.answer()
    callback_data_action = callback_data["action"]

    if callback_data_action == "all":
        _repository.clear()
    else:
        _repository.clear(is_done=True)

    await bot.edit_message_text(
        f"Задачи удалены! ",
        query.from_user.id,
        query.message.message_id,
    )
