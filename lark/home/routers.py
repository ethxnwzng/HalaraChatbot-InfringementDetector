"""Database routers for the home app."""

class ChatHistoryRouter:
    """
    A router to control all database operations on models in the
    chat history application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read chat history models go to chat_history DB.
        """
        if model._meta.app_label == 'home' and model._meta.model_name in ['chatmsg', 'chatcontext']:
            return 'chat_history'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write chat history models go to chat_history DB.
        """
        if model._meta.app_label == 'home' and model._meta.model_name in ['chatmsg', 'chatcontext']:
            return 'chat_history'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if both objects are chat history models.
        """
        if (
            obj1._meta.app_label == 'home' and
            obj2._meta.app_label == 'home' and
            obj1._meta.model_name in ['chatmsg', 'chatcontext'] and
            obj2._meta.model_name in ['chatmsg', 'chatcontext']
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the chat history models only appear in the 'chat_history'
        database.
        """
        if app_label == 'home' and model_name in ['chatmsg', 'chatcontext']:
            return db == 'chat_history'
        return None

class MaterialRouter:
    """
    A router to control all database operations on models in the
    material application.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read material models go to material DB.
        """
        if model._meta.app_label == 'home' and model._meta.model_name == 'material':
            return 'material'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write material models go to material DB.
        """
        if model._meta.app_label == 'home' and model._meta.model_name == 'material':
            return 'material'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if both objects are material models.
        """
        if (
            obj1._meta.app_label == 'home' and
            obj2._meta.app_label == 'home' and
            obj1._meta.model_name == 'material' and
            obj2._meta.model_name == 'material'
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the material models only appear in the 'material'
        database.
        """
        if app_label == 'home' and model_name == 'material':
            return db == 'material'
        return None 
