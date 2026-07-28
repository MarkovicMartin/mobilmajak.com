from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        # Záchranná síť pro obyčejná DateTimeField + legacy MySQL zero-datetime.
        from users.mysql_datetime_patch import patch_mysql_datetime_conversion

        patch_mysql_datetime_conversion()
