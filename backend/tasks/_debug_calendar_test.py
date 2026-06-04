from datetime import date

from tasks.tests import TasksApiTests


class DebugCalendarTest(TasksApiTests):
    def test_debug(self):
        self.setUp()
        mesic = date.today().strftime("%Y-%m")
        self._auth(self.admin)
        res_mine = self.client.get(f"/api/shifts/calendar/?mesic={mesic}&scope=mine")
        print("status", res_mine.status_code, "data", res_mine.data)
