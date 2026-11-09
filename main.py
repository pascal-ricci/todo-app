import os
import json
import threading
import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock

API_URL = "https://pascal4870.pythonanywhere.com/api.php"

LOCAL_DATA_DIR = "DataList"
if not os.path.exists(LOCAL_DATA_DIR):
    os.makedirs(LOCAL_DATA_DIR)

class TodoApp(App):
    def build(self):
        self.title = "To-Do List Automatique & Locale"
        self.sm = ScreenManager()
        
        self.lists_screen = ListsScreen(name='lists')
        self.tasks_screen = TasksScreen(name='tasks')
        
        self.sm.add_widget(self.lists_screen)
        self.sm.add_widget(self.tasks_screen)
        
        return self.sm

class ListsScreen(Screen):
    def __init__(self, **kwargs):
        super(ListsScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        layout.add_widget(Label(text="Mes Listes de Tâches", font_size=24, size_hint_y=None, height=50))
        
        input_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        self.list_name_input = TextInput(hint_text="Nom de la nouvelle liste", multiline=False)
        add_btn = Button(text="Créer", size_hint_x=None, width=100)
        add_btn.bind(on_press=self.create_list)
        input_layout.add_widget(self.list_name_input)
        input_layout.add_widget(add_btn)
        layout.add_widget(input_layout)
        
        scroll = ScrollView()
        self.lists_container = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        self.lists_container.bind(minimum_height=self.lists_container.setter('height'))
        scroll.add_widget(self.lists_container)
        layout.add_widget(scroll)
        
        self.add_widget(layout)

    def on_enter(self):
        # Synchronisation automatique à l'affichage de l'écran des listes
        self.load_lists()

    def load_lists(self):
        threading.Thread(target=self._fetch_lists_auto).start()

    def _fetch_lists_auto(self):
        lists = []
        # 1. Tentative de récupération depuis le serveur en arrière-plan
        try:
            response = requests.get(API_URL, params={"action": "get_lists"}, timeout=3)
            if response.status_code == 200:
                lists = response.json()
        except Exception:
            pass

        # 2. Si le serveur ne répond pas, on utilise les listes locales existantes
        if not lists and os.path.exists(LOCAL_DATA_DIR):
            lists = [f[:-5] for f in os.listdir(LOCAL_DATA_DIR) if f.endswith('.json')]

        # S'assure que chaque liste possède son fichier local de cache
        for name in lists:
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
            path = os.path.join(LOCAL_DATA_DIR, f"{safe_name}.json")
            if not os.path.exists(path):
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump([], f)

        Clock.schedule_once(lambda dt: self.update_lists_ui(lists))

    def update_lists_ui(self, lists):
        self.lists_container.clear_widgets()
        if not lists:
            self.lists_container.add_widget(Label(text="Aucune liste trouvée", size_hint_y=None, height=40))
            return
        for list_name in lists:
            row = BoxLayout(size_hint_y=None, height=50, spacing=5)
            
            btn = Button(text=list_name)
            btn.bind(on_press=lambda x, name=list_name: self.open_list(name))
            row.add_widget(btn)
            
            del_btn = Button(text="Supprimer", size_hint_x=None, width=120, color=(1, 0.3, 0.3, 1))
            del_btn.bind(on_press=lambda x, name=list_name: self.confirm_delete_list(name))
            row.add_widget(del_btn)
            
            self.lists_container.add_widget(row)

    def create_list(self, instance):
        name = self.list_name_input.text.strip()
        if name:
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
            path = os.path.join(LOCAL_DATA_DIR, f"{safe_name}.json")
            if not os.path.exists(path):
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump([], f)
            
            # Synchronisation distante automatique en arrière-plan
            def _req():
                try:
                    requests.get(API_URL, params={"action": "create_list", "name": name}, timeout=3)
                except:
                    pass
                Clock.schedule_once(lambda dt: self.load_lists())
            threading.Thread(target=_req).start()
            
            self.list_name_input.text = ""
            self.load_lists()

    def confirm_delete_list(self, name):
        content = BoxLayout(orientation='vertical', padding=15, spacing=15)
        popup = Popup(title="Confirmation", content=content, size_hint=(0.8, 0.4))
        
        lbl = Label(text=f"Voulez-vous vraiment supprimer\nla liste '{name}' ?", halign='center')
        lbl.bind(size=lbl.setter('text_size'))
        content.add_widget(lbl)
        
        btn_layout = BoxLayout(size_hint_y=None, height=45, spacing=10)
        btn_yes = Button(text="Oui, supprimer", color=(1, 0.3, 0.3, 1))
        btn_no = Button(text="Annuler")
        
        def do_delete(instance):
            popup.dismiss()
            self.delete_list(name)
            
        btn_yes.bind(on_press=do_delete)
        btn_no.bind(on_press=popup.dismiss)
        
        btn_layout.add_widget(btn_yes)
        btn_layout.add_widget(btn_no)
        content.add_widget(btn_layout)
        
        popup.open()

    def delete_list(self, name):
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
        path = os.path.join(LOCAL_DATA_DIR, f"{safe_name}.json")
        if os.path.exists(path):
            os.remove(path)
        
        def _req():
            try:
                requests.get(API_URL, params={"action": "delete_list", "name": name}, timeout=3)
            except:
                pass
            Clock.schedule_once(lambda dt: self.load_lists())
        threading.Thread(target=_req).start()
        self.load_lists()

    def open_list(self, name):
        app = App.get_running_app()
        app.tasks_screen.current_list = name
        app.sm.current = 'tasks'


class TasksScreen(Screen):
    def __init__(self, **kwargs):
        super(TasksScreen, self).__init__(**kwargs)
        self.current_list = ""
        self.tasks_data = [] 
        
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.title_label = Label(text="Tâches", font_size=22, size_hint_y=None, height=50)
        self.layout.add_widget(self.title_label)
        
        input_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        self.task_input = TextInput(hint_text="Nouvelle tâche", multiline=False)
        add_btn = Button(text="Ajouter", size_hint_x=None, width=100)
        add_btn.bind(on_press=self.add_task)
        input_layout.add_widget(self.task_input)
        input_layout.add_widget(add_btn)
        self.layout.add_widget(input_layout)
        
        self.scroll = ScrollView()
        self.tasks_container = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        self.tasks_container.bind(minimum_height=self.tasks_container.setter('height'))
        
        self.scroll.add_widget(self.tasks_container)
        self.layout.add_widget(self.scroll)
        
        back_btn = Button(text="<- Retour aux listes", size_hint_y=None, height=50)
        back_btn.bind(on_press=self.go_back)
        self.layout.add_widget(back_btn)

        self.add_widget(self.layout)

    def on_enter(self):
        self.title_label.text = f"Liste : {self.current_list}"
        self.load_tasks()

    def load_tasks(self):
        threading.Thread(target=self._fetch_tasks_auto).start()

    def _fetch_tasks_auto(self):
        if not self.current_list:
            return
        tasks = []
        safe_name = "".join(c for c in self.current_list if c.isalnum() or c in (' ', '_', '-')).strip()
        path = os.path.join(LOCAL_DATA_DIR, f"{safe_name}.json")
        
        # 1. Source de vérité prioritaire : le fichier local (garantit l'accès hors-ligne et la persistance immédiate)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        tasks = [str(item.get("label", item)) if isinstance(item, dict) else str(item) for item in data]
            except Exception as e:
                print(f"Erreur de lecture locale : {e}")

        self.tasks_data = tasks
        Clock.schedule_once(lambda dt: self.update_tasks_ui(tasks))

    def update_tasks_ui(self, tasks):
        self.tasks_container.clear_widgets()
        if not tasks:
            self.tasks_container.add_widget(Label(text="Aucune tâche dans cette liste", size_hint_y=None, height=40))
            return
        
        for index, task_text in enumerate(tasks):
            row = BoxLayout(size_hint_y=None, height=45, spacing=5)
            
            btn = Button(text=f"{index + 1}. {task_text}", halign='left', valign='middle')
            btn.bind(size=btn.setter('text_size'))
            btn.bind(on_press=lambda x, idx=index: self.open_task_options(idx))
            row.add_widget(btn)
            
            self.tasks_container.add_widget(row)

    def add_task(self, instance):
        task_text = self.task_input.text.strip()
        if task_text and self.current_list:
            if not isinstance(self.tasks_data, list):
                self.tasks_data = []
            self.tasks_data.append(task_text)
            self.save_and_refresh()
            self.task_input.text = ""

    def save_and_refresh(self):
        if not self.current_list:
            return
        safe_name = "".join(c for c in self.current_list if c.isalnum() or c in (' ', '_', '-')).strip()
        path = os.path.join(LOCAL_DATA_DIR, f"{safe_name}.json")
        
        # 1. Sauvegarde immédiate sur le disque local
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.tasks_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Erreur d'enregistrement local : {e}")
        
        # 2. Mise à jour instantanée de l'interface
        self.update_tasks_ui(self.tasks_data)

        # 3. Synchronisation automatique transparente en arrière-plan
        def _bg_sync():
            try:
                requests.get(API_URL, params={"action": "create_list", "name": self.current_list}, timeout=2)
            except:
                pass
        threading.Thread(target=_bg_sync).start()

    def open_task_options(self, index):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        popup = Popup(title=f"Options - Tâche {index + 1}", content=content, size_hint=(0.8, 0.7))
        
        btn_modify = Button(text="Modifier")
        btn_up = Button(text="Déplacer tout en haut")
        btn_down = Button(text="Déplacer tout en bas")
        btn_before = Button(text="Déplacer avant (Ligne précédente)")
        btn_after = Button(text="Déplacer après (Ligne suivante)")
        btn_pos = Button(text="Déplacer au numéro précis...")
        btn_delete = Button(text="Supprimer", color=(1, 0.3, 0.3, 1))
        
        btn_modify.bind(on_press=lambda x: [popup.dismiss(), self.prompt_modify_task(index)])
        btn_up.bind(on_press=lambda x: [popup.dismiss(), self.move_to_extremity(index, 'top')])
        btn_down.bind(on_press=lambda x: [popup.dismiss(), self.move_to_extremity(index, 'bottom')])
        btn_before.bind(on_press=lambda x: [popup.dismiss(), self.move_relative(index, -1)])
        btn_after.bind(on_press=lambda x: [popup.dismiss(), self.move_relative(index, 1)])
        btn_pos.bind(on_press=lambda x: [popup.dismiss(), self.prompt_move_to_position(index)])
        btn_delete.bind(on_press=lambda x: [popup.dismiss(), self.confirm_delete_task(index)])
        
        content.add_widget(btn_modify)
        content.add_widget(btn_up)
        content.add_widget(btn_down)
        content.add_widget(btn_before)
        content.add_widget(btn_after)
        content.add_widget(btn_pos)
        content.add_widget(btn_delete)
        
        popup.open()

    def prompt_modify_task(self, index):
        current_text = self.tasks_data[index]
        
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        popup = Popup(title="Modifier la tâche", content=content, size_hint=(0.8, 0.4))
        
        text_input = TextInput(text=current_text, multiline=False)
        save_btn = Button(text="Enregistrer", size_hint_y=None, height=45)
        
        def save_mod(instance):
            new_text = text_input.text.strip()
            if new_text:
                self.tasks_data[index] = new_text
                self.save_and_refresh()
            popup.dismiss()
            
        save_btn.bind(on_press=save_mod)
        content.add_widget(text_input)
        content.add_widget(save_btn)
        popup.open()

    def move_relative(self, index, offset):
        new_index = index + offset
        if 0 <= new_index < len(self.tasks_data):
            item = self.tasks_data.pop(index)
            self.tasks_data.insert(new_index, item)
            self.save_and_refresh()

    def move_to_extremity(self, index, position):
        item = self.tasks_data.pop(index)
        if position == 'top':
            self.tasks_data.insert(0, item)
        else:
            self.tasks_data.append(item)
        self.save_and_refresh()

    def prompt_move_to_position(self, index):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        popup = Popup(title="Déplacer au numéro", content=content, size_hint=(0.8, 0.4))
        
        text_input = TextInput(hint_text=f"Entrer un numéro (1 à {len(self.tasks_data)})", multiline=False, input_filter='int')
        ok_btn = Button(text="Déplacer", size_hint_y=None, height=45)
        
        def do_move(instance):
            try:
                target_pos = int(text_input.text.strip()) - 1
                if 0 <= target_pos < len(self.tasks_data):
                    item = self.tasks_data.pop(index)
                    self.tasks_data.insert(target_pos, item)
                    self.save_and_refresh()
            except ValueError:
                pass
            popup.dismiss()
            
        ok_btn.bind(on_press=do_move)
        content.add_widget(text_input)
        content.add_widget(ok_btn)
        popup.open()

    def confirm_delete_task(self, index):
        if not (0 <= index < len(self.tasks_data)):
            return
            
        task_text = self.tasks_data[index]
        content = BoxLayout(orientation='vertical', padding=15, spacing=15)
        popup = Popup(title="Confirmation", content=content, size_hint=(0.8, 0.4))
        
        lbl = Label(text=f"Voulez-vous vraiment supprimer\nla tâche :\n'{task_text}' ?", halign='center')
        lbl.bind(size=lbl.setter('text_size'))
        content.add_widget(lbl)
        
        btn_layout = BoxLayout(size_hint_y=None, height=45, spacing=10)
        btn_yes = Button(text="Oui, supprimer", color=(1, 0.3, 0.3, 1))
        btn_no = Button(text="Annuler")
        
        def do_delete(instance):
            popup.dismiss()
            self.delete_task(index)
            
        btn_yes.bind(on_press=do_delete)
        btn_no.bind(on_press=popup.dismiss)
        
        btn_layout.add_widget(btn_yes)
        btn_layout.add_widget(btn_no)
        content.add_widget(btn_layout)
        
        popup.open()

    def delete_task(self, index):
        if 0 <= index < len(self.tasks_data):
            self.tasks_data.pop(index)
            self.save_and_refresh()

    def go_back(self, instance):
        App.get_running_app().sm.current = 'lists'


if __name__ == '__main__':
    TodoApp().run()