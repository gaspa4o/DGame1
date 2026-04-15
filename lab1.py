import json
import random
import unittest
import sys
import networkx as nx
import matplotlib.pyplot as plt

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext


# ЛОГИКА ИГРЫ (Модель)
class DynamicGame:
    def __init__(self):
        self.G = nx.DiGraph()      # Создаем пустой направленный граф (дерево) из NetworkX
        self.num_players = 0       # Переменная для хранения количества игроков
        self.root = None           # Здесь будет храниться имя корневого узла
        self.solution_edges = []   # Список, в который мы сохраним "выигрышные" пути (стрелочки), потом в красный

    def load_from_json(self, json_string):
        self.G.clear()
        self.solution_edges = []
        data = json.loads(json_string) # Превращаем текстовую строку JSON в словарь Python
        self.num_players = data.get("players", 2) # Достаем количество игроков (по умолчанию 2)    
        # Цикл проходит по словарю "nodes" и добавляет узлы в граф с их атрибутами (игрок или выигрыши)
        for node_id, attrs in data.get("nodes", {}).items():
            self.G.add_node(node_id, **attrs)
         # Цикл проходит по списку "edges" и рисует направленные ребра между узлами, записывая на них имя действия    
        for edge in data.get("edges", []):
            self.G.add_edge(edge["source"], edge["target"], action=edge["action"])
            
        self._find_root() # Вызываем функцию поиска корня графа

    def export_to_json(self):
        """Экспорт текущего графа в JSON строку"""
        data = {"players": self.num_players, "nodes": {}, "edges": []}
        for n, attrs in self.G.nodes(data=True): #все узлы
            data["nodes"][n] = attrs
        for u, v, attrs in self.G.edges(data=True): #все ребра
            data["edges"].append({"source": u, "target": v, "action": attrs["action"]})
        return json.dumps(data, indent=4)

    def generate_random_model(self, num_players=3, depth=4, max_branching=2):
        self.G.clear()             
        self.solution_edges = []
        self.num_players = num_players
        self.root = "N0"           # Называем корень N0
        # Добавляем корень и случайно назначаем, кто делает первый ход
        self.G.add_node(self.root, player=random.randint(1, num_players))
        
        node_counter = 1           # Счетчик для уникальных имен узлов (N1, N2...)
        queue = [(self.root, 0)]   # Очередь для обработки: хранит (Имя_узла, Текущая_глубина)
        
        while queue: # Пока в очереди есть узлы
            current_node, current_depth = queue.pop(0) # Достаем первый узел
            
            # Если мы еще не достигли нужной глубины игры
            if current_depth < depth - 1: 
                # Выбираем случайное количество веток для этого узла
                branches = random.randint(2, max_branching)
                for i in range(branches):
                    child_id = f"N{node_counter}"      # Генерируем имя ребенка
                    node_counter += 1
                    action_name = f"Act_{child_id}"    # Генерируем имя действия
                    
                    # Соединяем текущий узел с дочерним об
                    self.G.add_edge(current_node, child_id, action=action_name)
                    
                    # Если следующий уровень - это уже конец игры 
                    if current_depth + 1 == depth - 1:
                        # Генерируем массив случайных чисел (выигрыши для каждого игрока)
                        payoffs = [random.randint(0, 10) for _ in range(num_players)]
                        self.G.add_node(child_id, payoffs=payoffs) # Создаем узел-лист
                    else:
                        # Иначе создаем обычный узел, назначаем случайного игрока 
                        self.G.add_node(child_id, player=random.randint(1, num_players))
                        # И добавляем этот дочерний об в очередь, чтобы на следующих циклах "вырастить" ветки и из него
                        queue.append((child_id, current_depth + 1))
        self._find_root()

    def _find_root(self):
        roots = [n for n, d in self.G.in_degree() if d == 0] #входящие стрелки=0
        if roots: self.root = roots[0]

    def validate(self):
        if not self.G.nodes:
            raise ValueError("Граф пуст.")
        if not nx.is_directed_acyclic_graph(self.G):  # Проверка, что это действительно дерево (нет циклов и стрелок назад)
            raise ValueError("Ошибка: Граф содержит циклы.")
        roots = [n for n, d in self.G.in_degree() if d == 0]
        if len(roots) != 1: # Проверка, что дерево не разорвано на 2 части
            raise ValueError(f"Ошибка: Должен быть 1 корень, найдено: {len(roots)}")
            
        # валидация глубины
        if nx.dag_longest_path_length(self.G) < 1:
            raise ValueError("Ошибка: Игра должна содержать как минимум 1 ход.")
            
        # Проверка каждого узла:
        for node in self.G.nodes():
            if self.G.out_degree(node) == 0: # Если из узла не выходит стрелок
                # Он обязан иметь атрибут 'payoffs'
                if "payoffs" not in self.G.nodes[node]: ...
                # Длина массива выигрышей должна совпадать с количеством игроков
                if len(self.G.nodes[node]["payoffs"]) != self.num_players: ...
            else: # Если это внутренний узел принятия решения
                # Он обязан иметь атрибут 'player'
                if "player" not in self.G.nodes[node]: ...
        return True

    def print_tree(self):
        if not self.G.nodes:
            print("\nГраф пуст!")
            return
            
        print("\n=== ИЕРАРХИЯ СТРУКТУРЫ ИГРЫ ===")
        
        
        if self.G.out_degree(self.root) == 0:
            print(f"[{self.root}] ➔ 🏁 Исход: {self.G.nodes[self.root]['payoffs']}")
            return
        else:
            print(f"[{self.root}] ➔ 👤 Ходит Игрок {self.G.nodes[self.root]['player']}")
            
        # Вложенная функция рекурсивного обхода дерева
        def display_branch(node, current_indent):
            children = list(self.G.successors(node))
            
            for index, child in enumerate(children):
                # Определяем, является ли дочерний об. последним в списке (влияет на символ отступа)
                is_tail = (index == len(children) - 1)
            
                connector = " ╚══" if is_tail else " ╠══"
                action_name = self.G.edges[node, child]['action']
                
                # Достаем данные целевого узла
                if self.G.out_degree(child) == 0: # Если это лист
                    node_desc = f"🏁 Выигрыши: {self.G.nodes[child]['payoffs']}"
                else: # Если это узел решения
                    node_desc = f"👤 Игрок {self.G.nodes[child]['player']}"
                    
                line = f"{current_indent}{connector}[{action_name}]══▶ Узел {child} ({node_desc})"
                print(line)

                # Если ветка последняя, под ней пустота, если нет - |
                next_indent = current_indent + ("     " if is_tail else " ║   ")
                
                display_branch(child, next_indent)
                
        # Запускаем обход от корня с пустым стартовым отступом
        display_branch(self.root, "")

    def solve(self):
        # Запускаем индукцию от корня. Она спустится вниз и вернет нам лучшие пути наверх
        optimal_payoffs, optimal_edges = self._backward_induction(self.root)
        
        # Убираем повторяющиеся выигрыши из итогового ответа
        unique_payoffs = []
        for p in optimal_payoffs:
            if p not in unique_payoffs: unique_payoffs.append(p)
                
        for i, p in enumerate(unique_payoffs, 1):
            print(f"Решение {i}: Выигрыши = {p}")
            
        self.solution_edges = optimal_edges # Сохраняем стрелки решений для рисования
        return optimal_edges

    def _backward_induction(self, node):
        # Базовый случай рекурсии: если мы спустились до конца, возвращаем его выигрыши наверх
        if self.G.out_degree(node) == 0:
            return [self.G.nodes[node]['payoffs']], []

        player = self.G.nodes[node]['player'] # Чей ход
        player_idx = player - 1               # Индекс в массиве (Игрок 1 -> индекс 0)
        
        best_payoffs, best_edges, best_action_names = [], [], []
        max_val = float('-inf') # Изначально максимальный выигрыш равен минус бесконечности

        # Перебираем все возможные ходы из этого узла
        for child in self.G.successors(node):
            action = self.G.edges[node, child]['action']
            
            # Рекурсия - запрашиваем у доч. об., какие выигрыши принесет этот путь
            child_payoffs_list, child_edges = self._backward_induction(child)
            
            # Анализируем ответы от доч.об.
            for payoffs in child_payoffs_list:
                val = payoffs[player_idx] # Смотрим на выигрыш конкретно ТЕКУЩЕГО ИГРОКА
                
                if val > max_val: # Если этот ход выгоднее предыдущих
                    max_val = val # Обновляем максимум
                    best_payoffs = [payoffs] # Запоминаем выигрыш
                    best_edges = [(node, child)] + child_edges # Записываем стрелку
                    best_action_names = [action] # Запоминаем название действия
                    
                elif val == max_val: # Если ход приносит такой же максимальный выигрыш
                    # Сохраняем все варианты 
                    best_payoffs.append(payoffs)
                    best_edges.extend([(node, child)] + child_edges)
                    best_action_names.append(action)

        # Выводим в лог, что решил игрок на этом этапе
        print(f"Узел '{node}': Игрок {player} выбирает {best_action_names} (макс. выигрыш: {max_val}).")
        # Возвращаем решения на уровень выше
        return best_payoffs, best_edges

    def draw(self):
        if not self.G.nodes:
            print("Граф пуст! Нечего рисовать.")
            return

        for layer, nodes in enumerate(nx.topological_generations(self.G)):
            for node in nodes: self.G.nodes[node]["layer"] = layer
                
        pos = nx.multipartite_layout(self.G, subset_key="layer", align="horizontal")
        for k in pos: pos[k][1] = -pos[k][1]

        plt.figure(figsize=(10, 6))
        nx.draw_networkx_edges(self.G, pos, edge_color='gray', arrows=True, node_size=1000)
        
        if self.solution_edges:
            nx.draw_networkx_edges(self.G, pos, edgelist=self.solution_edges, edge_color='red', width=2.5, arrows=True, node_size=1000)

        leaf_nodes = [n for n in self.G.nodes() if self.G.out_degree(n) == 0]
        internal_nodes = [n for n in self.G.nodes() if self.G.out_degree(n) > 0]
        
        nx.draw_networkx_nodes(self.G, pos, nodelist=internal_nodes, node_color='lightblue', node_size=1000)
        nx.draw_networkx_nodes(self.G, pos, nodelist=leaf_nodes, node_color='lightgreen', node_size=1000)

        labels = {}
        for node in self.G.nodes():
            if node in leaf_nodes: labels[node] = str(self.G.nodes[node]['payoffs'])
            else: labels[node] = f"{node}\n(P{self.G.nodes[node]['player']})"
        nx.draw_networkx_labels(self.G, pos, labels=labels, font_size=8, font_weight="bold")

        edge_labels = {(u, v): d['action'] for u, v, d in self.G.edges(data=True)}
        nx.draw_networkx_edge_labels(self.G, pos, edge_labels=edge_labels, font_color='blue', font_size=8)

        plt.title("Дерево игры (Красный - оптимальный путь)")
        plt.axis('off')
        plt.tight_layout()
        plt.show()


# GUI: ВСПЛЫВАЮЩИЕ ПОДСКАЗКИ И ПЕРЕНАПРАВЛЕНИЕ КОНСОЛИ
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1, font=("Arial", 9))
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class RedirectText(object):
    def __init__(self, text_ctrl):
        self.output = text_ctrl
    def write(self, string):
        self.output.insert(tk.END, string)
        self.output.see(tk.END)
    def flush(self): pass


# GUI: ОСНОВНОЕ ПРИЛОЖЕНИЕ
class GameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Анализатор динамических игр")
        self.root.geometry("950x650")
        
        self.game = DynamicGame()

        # Левая панель для кнопок и настроек
        self.frame_controls = tk.Frame(root, width=280, bg="#f0f0f0", padx=10, pady=10)
        self.frame_controls.pack(side=tk.LEFT, fill=tk.Y)

        # Правая панель для вывода текста
        self.frame_output = tk.Frame(root, padx=10, pady=10)
        self.frame_output.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.text_box = scrolledtext.ScrolledText(self.frame_output, wrap=tk.WORD, font=("Consolas", 10))
        self.text_box.pack(fill=tk.BOTH, expand=True)
        
        # Перенаправляем print() в текстовое поле
        sys.stdout = RedirectText(self.text_box)

        self.create_settings_panel()
        self.create_buttons()
        
        print("Добро пожаловать в анализатор динамических игр!")
        print("Настройте параметры слева и сгенерируйте случайную модель.\n")

    def create_settings_panel(self):
        """Панель с переключателями глубины и количества игроков"""
        self.frame_settings = tk.LabelFrame(self.frame_controls, text="Настройки генерации", bg="#f0f0f0", padx=5, pady=5)
        self.frame_settings.pack(fill=tk.X, pady=(0, 10))

        # Переключатель игроков
        tk.Label(self.frame_settings, text="Игроков:", bg="#f0f0f0").grid(row=0, column=0, sticky="w", pady=2)
        self.players_var = tk.IntVar(value=3)
        tk.Radiobutton(self.frame_settings, text="2", variable=self.players_var, value=2, bg="#f0f0f0").grid(row=0, column=1)
        tk.Radiobutton(self.frame_settings, text="3", variable=self.players_var, value=3, bg="#f0f0f0").grid(row=0, column=2)

        # Переключатель глубины
        tk.Label(self.frame_settings, text="Глубина:", bg="#f0f0f0").grid(row=1, column=0, sticky="w", pady=2)
        self.depth_var = tk.IntVar(value=4)
        tk.Radiobutton(self.frame_settings, text="2", variable=self.depth_var, value=2, bg="#f0f0f0").grid(row=1, column=1)
        tk.Radiobutton(self.frame_settings, text="3", variable=self.depth_var, value=3, bg="#f0f0f0").grid(row=1, column=2)
        tk.Radiobutton(self.frame_settings, text="4", variable=self.depth_var, value=4, bg="#f0f0f0").grid(row=1, column=3)

    def create_buttons(self):
        buttons_info = [
            ("Генерировать случайно", self.btn_generate, "Создает дерево игры на основе настроек выше"),
            ("Ввести / Редактировать вручную", self.btn_manual_edit, "Открывает окно для редактирования графа в формате JSON"),
            ("Загрузить из JSON", self.btn_load, "Загрузить модель из .json файла на диске"),
            ("Сохранить в JSON", self.btn_save, "Сохранить текущую модель в .json файл"),
            ("", None, ""), # Разделитель
            ("Валидация структуры", self.btn_validate, "Проверка графа на цикличность, глубину и наличие выигрышей"),
            ("Вывод графа (Текст)", self.btn_print_tree, "Показать структуру дерева в текстовом формате"),
            ("Найти решение (Алгоритм)", self.btn_solve, "Запуск обратной индукции (Backward Induction)"),
            ("Показать Граф (Окно)", self.btn_draw, "Отрисовать граф с помощью Matplotlib"),
            ("", None, ""),
            ("Запустить Авто-тесты", self.btn_test, "Автоматическое тестирование логики и валидатора"),
            ("Очистить консоль", lambda: self.text_box.delete('1.0', tk.END), "Очистить текстовое поле справа")
        ]

        for text, command, tooltip in buttons_info:
            if text == "":
                tk.Label(self.frame_controls, text="-"*35, bg="#f0f0f0").pack(pady=2)
                continue
            btn = tk.Button(self.frame_controls, text=text, command=command, width=28)
            btn.pack(pady=3)
            ToolTip(btn, tooltip)

    # --- Функции кнопок ---
    def btn_generate(self):
        p = self.players_var.get()
        d = self.depth_var.get()
        print(f"Генерация случайной модели (Игроков: {p}, Глубина: {d})...")
        self.game.generate_random_model(num_players=p, depth=d)
        print("Модель успешно сгенерирована! (Доступна для графического вывода или решения)")

    def btn_manual_edit(self):
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Редактор JSON модели")
        edit_window.geometry("500x500")
        
        text_area = scrolledtext.ScrolledText(edit_window, wrap=tk.WORD, font=("Consolas", 10))
        text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        if self.game.G.nodes:
            text_area.insert(tk.END, self.game.export_to_json())
        else:
            template = '{\n  "players": 2,\n  "nodes": {\n    "N0": {"player": 1},\n    "L1": {"payoffs": [1, 2]}\n  },\n  "edges": [\n    {"source": "N0", "target": "L1", "action": "Left"}\n  ]\n}'
            text_area.insert(tk.END, template)

        def apply_changes():
            json_data = text_area.get("1.0", tk.END)
            try:
                self.game.load_from_json(json_data)
                print("\nМодель успешно обновлена из ручного ввода!")
                edit_window.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка JSON", str(e))

        tk.Button(edit_window, text="Применить и закрыть", command=apply_changes, bg="lightgreen").pack(pady=5)

    def btn_load(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if filepath:
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    self.game.load_from_json(f.read())
                    print(f"\nМодель загружена из файла: {filepath}")
                except Exception as e:
                    print(f"Ошибка загрузки: {e}")

    def btn_save(self):
        if not self.game.G.nodes:
            messagebox.showwarning("Внимание", "Граф пуст! Нечего сохранять.")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.game.export_to_json())
                print(f"\nМодель сохранена в файл: {filepath}")

    def btn_validate(self):
        try:
            self.game.validate()
            print("\nВалидация пройдена успешно! Граф корректен.")
            messagebox.showinfo("Валидация", "Граф полностью корректен!")
        except Exception as e:
            print(f"\nОшибка валидации: {e}")
            messagebox.showerror("Ошибка валидации", str(e))

    def btn_print_tree(self):
        if not self.game.G.nodes:
            print("\nГраф пуст!")
            return
        self.game.print_tree()

    def btn_solve(self):
        if not self.game.G.nodes:
            print("\nГраф пуст! Сначала создайте или загрузите модель.")
            return
        try:
            self.game.validate()
            self.game.solve()
        except Exception as e:
            print(f"Невозможно решить: {e}")

    def btn_draw(self):
        self.game.draw()

    def btn_test(self):
        print("\n--- ЗАПУСК АВТОМАТИЧЕСКИХ ТЕСТОВ ---")
        old_stdout = sys.stdout
        sys.stdout = sys.__stdout__
        
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDynamicGame)
        result = unittest.TextTestRunner(stream=old_stdout, verbosity=2).run(suite)
        
        sys.stdout = old_stdout
        print(f"Тестов запущено: {result.testsRun}")
        if result.wasSuccessful():
            print("Все тесты пройдены УСПЕШНО!")
        else:
            print(f"Ошибок: {len(result.errors)}, Провалов: {len(result.failures)}")


# ТЕСТЫ ДЛЯ АВТОМАТИЗАЦИИ
class TestDynamicGame(unittest.TestCase):
    def setUp(self):
        self.game = DynamicGame()
        
    def test_validation_fails_on_empty_tree(self):
        # Проверка, что пустой граф вызывает ошибку
        with self.assertRaises(ValueError):
            self.game.validate()
            
    def test_random_generator(self):
        # Проверяем работу генератора с глубиной 3 и 3 игроками
        self.game.generate_random_model(num_players=3, depth=3, max_branching=2)
        self.assertTrue(self.game.validate())
        edges = self.game.solve()
        self.assertIsInstance(edges, list)


# ТОЧКА ВХОДА
if __name__ == "__main__":
    root = tk.Tk()
    app = GameApp(root)
    root.mainloop()