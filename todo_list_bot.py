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

def _set_tasks_level(tasks: typing.List[Task]):
    '''
    Функция простановки уровня вложенности задания
    '''
    
    for num2, task in enumerate(tasks):
        if task.parent_id != -1:
            for num in range(num2-1, -1, -1):
                if tasks[num].id == task.parent_id:
                    task.level = tasks[num].level + 1
    
def _sort_tasks(tasks: typing.List[Task], id_t: int):
    '''
    Функция сортировки заданий для корректного отображения в сообщении
    '''
    tasks_copy = []
    for task in tasks:
        if task.parent_id == id_t:
            tasks_copy.append(task)
            id_new = task.id
            new_task = _sort_tasks(tasks, id_new)
            for n_t in new_task:
                tasks_copy.append(n_t)
    return tasks_copy
                    
def _tasks_done(tasks: typing.List[Task], task_ids: typing.List[int]):
    '''
    Функция завершения дочерних заданий, если завершена головная, с учетом глубокой вложенности
    '''
    done_ids = []
    for t_id in task_ids:
        for task in tasks:
            if task.parent_id == t_id:
                done_ids.append(task.id)
                id_new = [task.id]
                new_ids = _tasks_done(tasks, id_new)
                for n_i in new_ids:
                    done_ids.append(n_i)
    return done_ids
            
def _task_dto_to_string(task: Task) -> str:
    status_char = "\u2705" if task.is_done else "\u274c"
    child = "" if task.parent_id == -1 else "  "*task.level #добавляем пробелы в зависимости от уровня вложенности задания
    return f"{child}{task.id}: {task.text} | {status_char}"


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
    task_number = _repository.add_task(message.get_args())
    await message.reply("Добавлена задача " + str(task_number[0]))
    
@dispatcher.message_handler(commands=["add_subtask"])
async def create_subtask(message: types.Message):
    if message.get_args() == '':
        await message.reply("Не указаны данные по подзадаче")
    else:
        task_list = _repository.get_list()
        task_numbers_list = [task.id for task in task_list]
        try:
            if int(message.get_args().split(" ")[-1]) in task_numbers_list:
                task_number = _repository.add_subtask(message.get_args())
                await message.reply("Добавлена подзадача " + str(task_number[0]))
            else:
                await message.reply("Не указана задача родитель или неверный номер задачи родителя")
        except ValueError:
            await message.reply("Не указана задача родитель")

@dispatcher.message_handler(commands=["list"])
async def get_list(message: types.Message):
    if message.get_args():
        tasks = _repository.get_list(message.get_args())
    else:
        tasks = _repository.get_list()
    _set_tasks_level(tasks)
    tasks = _sort_tasks(tasks, -1)
    if tasks:
        text = "\n".join([_task_dto_to_string(res) for res in tasks])
    else:
        text = "У вас нет задач!"
    await bot.send_message(message.chat.id, text)
    
@dispatcher.message_handler(commands=["find"])
async def find_tasks(message: types.Message):
    tasks = _repository.find_tasks(message.get_args())
    if tasks:
        text = "\n".join([_task_dto_to_string(res) for res in tasks])
    else:
        text = 'Задачи по условию "' + message.get_args() + '" не найдены!'
    await bot.send_message(message.chat.id, text)

@dispatcher.message_handler(commands=["done"])
async def finish_task(message: types.Message):
    try:
        task_ids = [int(id_) for id_ in message.get_args().split(" ")]
        _repository.finish_tasks(task_ids)
        tasks = _repository.get_list()
        subtasks = _tasks_done(tasks, task_ids)
        _repository.finish_tasks(subtasks)
        if len(subtasks) > 0:
            text = f"Завершенные задачи: {task_ids} и подзадачи: {subtasks}"
        else:
            text = f"Завершенные задачи: {task_ids}"
    except ValueError as e:
        text = "Неправильный номер задачи"

    await message.reply(text)
    
@dispatcher.message_handler(commands=["reopen"])
async def reopen_tasks(message: types.Message):
    try:
        task_ids = [int(id_) for id_ in message.get_args().split(" ")]
        _repository.reopen_tasks(task_ids)
        text = f"Переоткрытые задачи: {task_ids}"
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

@dispatcher.message_handler(commands=["help", "start"])
async def create_task(message: types.Message):
    await message.reply('ToDo бот - менеджер задач.\n\n' + 
                        '/todo - наберите команду и описание задачи и она добавится в список. Например: "/todo покормить питомцев"\n\n' + 
                        '/add_subtask - добавление подзадачи к существующей задаче, с указанием номера задачи. Нарпимер: "/add_subtask покормить кота (хоть он и толстый) 1"\n\n' + 
                        '/list - покажет список задач и их номера "/list True" или "/list False" покажет завершенные и не завершенные задачи соответственно\n\n' + 
                        '/find - поиск задачи по ключевому слову. Например: "/find кот" покажет задачи в которых упоминается кот\n\n' + 
                        '/done - команда и номер задачи отметит задачу и подзадачи как выполненные. Например: "/done 1 3" - команда отметит выполненными задания 1 и 3 и их подзадачи\n\n' + 
                        '/reopen - пометить задачу обратно не выполненной. Например: "/reopen 1"\n\n' + 
                        '/clear - удаление задач')