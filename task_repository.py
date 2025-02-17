from db import tasks, engine
from task import Task

from typing import List


class TaskRepository:
    def add_task(self, text: str):
        query = tasks.insert().values(text=text, parent_id=-1)

        with engine.connect() as conn:
            task_num = conn.execute(query)
            conn.commit()
            return task_num.inserted_primary_key
        
    def add_subtask(self, text: str):
        text_list = text.split(' ')
        task_text = ' '.join(text_list[0:-1])
        parent_id = int(text_list[-1])
        query = tasks.insert().values(text=task_text, parent_id=parent_id)
        with engine.connect() as conn:
            task_num = conn.execute(query)
            conn.commit()
            return task_num.inserted_primary_key

    def get_list(self, is_done=None) -> List[Task]:
        query = tasks.select()

        if is_done != None:
            query = query.where(tasks.c.is_done == is_done)

        result = []
        with engine.connect() as conn:
            result = [
                Task(id=id, text=text, is_done=is_done, parent_id=parent_id)
                for id, text, is_done, parent_id in conn.execute(query.order_by(tasks.c.id))
            ]

        return result
    
    def find_tasks(self, text_string: str) -> List[Task]:
        query = tasks.select().filter(tasks.c.text.ilike(f'%{text_string}%'))

        result = []
        with engine.connect() as conn:
            result = [
                Task(id=id, text=text, is_done=is_done, parent_id=parent_id)
                for id, text, is_done, parent_id in conn.execute(query.order_by(tasks.c.id))
            ]

        return result

    def finish_tasks(self, ids: List[int]):
        query = tasks.update().where(tasks.c.id.in_(ids)).values(is_done=True)
        with engine.connect() as conn:
            conn.execute(query)
            conn.commit()
            
    def reopen_tasks(self, ids: List[int]):
        query = tasks.update().where(tasks.c.id.in_(ids)).values(is_done=False)
        with engine.connect() as conn:
            conn.execute(query)
            conn.commit()

    def clear(self, is_done=None):
        query = tasks.delete()

        if is_done is not None:
            query = query.where(tasks.c.is_done == is_done)

        with engine.connect() as conn:
            conn.execute(query)
            conn.commit()
