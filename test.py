import unittest
from rag import load_theorems, find_similar_theorem, get_theorem_content, get_hints_for_query, add_system_hints

class TestRAGFunctions(unittest.TestCase):

    def test_load_theorems(self):
        theorems = load_theorems()
        self.assertIsInstance(theorems, list)
        self.assertGreater(len(theorems), 0)

    def test_find_similar_theorem(self):
        query = "Теорема Абеля"
        similar_theorem = find_similar_theorem(query)
        self.assertEqual(similar_theorem, "Теорема Абеля")

    def test_get_theorem_content(self):
        theorem_name = "Теорема Абеля"
        content = get_theorem_content(theorem_name)
        self.assertIsInstance(content, str)
        self.assertGreater(len(content), 0)

    def test_get_hints_for_query(self):
        query = "напиши скрипт"
        hints = get_hints_for_query(query)
        self.assertIn("функция execute_python_code", hints)

    def test_add_system_hints(self):
        messages = [{"role": "system", "content": "System message"}]
        query = "Теорема Абеля"
        updated_messages = add_system_hints(messages, query)
        self.assertGreater(len(updated_messages), 1)
        self.assertIn("Запрос пользователя похож на теорему", updated_messages[0]["content"])
    def test_load_theorems_empty(self):
        theorems = load_theorems()
        self.assertNotEqual(theorems, [])

    def test_find_similar_theorem_no_match(self):
        query = "Несуществующая теорема"
        similar_theorem = find_similar_theorem(query)
        self.assertIsNone(similar_theorem)

    def test_get_theorem_content_invalid(self):
        theorem_name = "Несуществующая теорема"
        content = get_theorem_content(theorem_name)
        self.assertIsNone(content)

    def test_get_hints_for_query_no_hints(self):
        query = "неизвестный запрос"
        hints = get_hints_for_query(query)
        self.assertEqual(hints, [])

    def test_add_system_hints_no_query(self):
        messages = [{"role": "system", "content": "System message"}]
        query = ""
        updated_messages = add_system_hints(messages, query)
        self.assertEqual(len(updated_messages), 1)
if __name__ == '__main__':
    unittest.main()