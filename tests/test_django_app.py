"""Проверки страниц Django-приложения FAQ."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from faq_web.models import Answer, Question, Section, User
from storage import load_data


class FaqPagesTests(TestCase):
    """Проверить ORM-модели и основные маршруты FAQ."""

    @classmethod
    def setUpTestData(cls):
        sections, questions = load_data(
            settings.BASE_DIR / "data" / "faq.json"
        )
        section_models = {
            section.name: Section.objects.create(
                name=section.name,
                is_active=section.is_active,
            )
            for section in sections
        }
        user_names = {
            question.author.name
            for question in questions
        }
        user_names.update(
            answer.author.name
            for question in questions
            for answer in question.answers
        )
        users = {
            name: User.objects.create(name=name)
            for name in user_names
        }
        for question in questions:
            question_model = Question.objects.create(
                pk=question.id,
                section=section_models[question.section],
                author=users[question.author.name],
                title=question.title,
                text=question.text,
                created_at=question.created_at,
                status=question.status,
            )
            Answer.objects.bulk_create(
                [
                    Answer(
                        question=question_model,
                        author=users[answer.author.name],
                        text=answer.text,
                        created_at=answer.created_at,
                    )
                    for answer in question.answers
                ]
            )

    def setUp(self):
        self.client = Client()

    def test_homepage_shows_service_summary(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Сервис вопросов и ответов")
        self.assertContains(response, "Перейти к вопросам")

    def test_question_list_links_to_dynamic_detail_pages(self):
        response = self.client.get("/faq/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Как преобразовать строку в число?")
        self.assertContains(response, 'href="/faq/1/"')

    def test_question_list_can_filter_by_creation_date(self):
        response = self.client.get("/faq/", {"date": "2026-10-01"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python · ivan_petrov")
        self.assertNotContains(response, "Как преобразовать строку в число?")

    def test_question_list_filters_by_section_author_and_search(self):
        response = self.client.get(
            "/faq/",
            {
                "date": "2026-10-01",
                "section": "Python",
                "author": "ivan",
                "q": "Python",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python · ivan_petrov")
        self.assertNotContains(response, "Как преобразовать строку в число?")

    def test_question_list_sorts_and_handles_invalid_parameters(self):
        response = self.client.get("/faq/", {"sort": "title"})

        self.assertEqual(response.context["questions"][0].pk, 3)
        invalid_sort = self.client.get("/faq/", {"sort": "not-a-field"})
        self.assertEqual(invalid_sort.context["sort"], "date")
        invalid_date = self.client.get("/faq/", {"date": "not-a-date"})
        self.assertContains(invalid_date, "Укажите корректную дату.")
        self.assertContains(invalid_date, "Пока нет вопросов.")

    def test_pagination_keeps_filters_and_sorting(self):
        author = User.objects.get(name="ivan_petrov")
        section = Section.objects.get(name="Python")
        Question.objects.bulk_create(
            [
                Question(
                    section=section,
                    author=author,
                    title=f"Дополнительный вопрос {number}",
                    text="Тестовый текст",
                    created_at="2026-10-11",
                )
                for number in range(6)
            ]
        )

        response = self.client.get(
            "/faq/",
            {
                "section": "Python",
                "author": "ivan",
                "sort": "title",
                "page": "2",
            },
        )

        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertContains(
            response,
            'href="?section=Python&amp;author=ivan&amp;sort=title&amp;page=1"',
        )
        invalid_page = self.client.get("/faq/", {"page": "abc"})
        self.assertEqual(invalid_page.context["page_obj"].number, 1)

    def test_question_detail_shows_answers(self):
        response = self.client.get("/faq/1/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Как из str получить int?")
        self.assertContains(response, "Используйте функцию int()")

    def test_section_page_lists_sections_and_questions(self):
        sections_response = self.client.get("/faq/sections/")

        self.assertEqual(sections_response.status_code, 200)
        self.assertContains(sections_response, "Тематические разделы")
        self.assertContains(
            sections_response,
            'href="/faq/sections/?section=Python"',
        )

        questions_response = self.client.get(
            "/faq/sections/",
            {"section": "Python"},
        )
        self.assertEqual(questions_response.status_code, 200)
        self.assertContains(
            questions_response,
            "Вопросы раздела «Python»",
        )
        self.assertContains(
            questions_response,
            "Как преобразовать строку в число?",
        )

    def test_section_page_handles_empty_sections(self):
        Section.objects.create(name="Новый раздел")

        response = self.client.get(
            "/faq/sections/",
            {"section": "Новый раздел"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "В этом разделе пока нет вопросов.")

    def test_models_expose_related_objects_and_reverse_relations(self):
        question = Question.objects.select_related(
            "section",
            "author",
        ).get(pk=1)

        self.assertEqual(question.section.name, "Python")
        self.assertEqual(question.author.name, "maria_smirnova")
        self.assertEqual(question.answers.count(), 1)
        self.assertEqual(question.author.authored_questions.count(), 1)

    def test_admin_can_update_and_delete_questions(self):
        admin_user = get_user_model().objects.create_superuser(
            username="faq_admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:faq_web_question_changelist"),
            {
                "action": "close_questions",
                "_selected_action": ["2"],
            },
        )

        self.assertEqual(response.status_code, 302)
        question = Question.objects.get(pk=2)
        self.assertEqual(question.status, Question.Status.CLOSED)

        response = self.client.post(
            reverse("admin:faq_web_question_delete", args=[question.pk]),
            {"post": "yes"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Question.objects.filter(pk=question.pk).exists())

    def test_statistics_page_shows_question_and_answer_counts(self):
        response = self.client.get("/faq/statistics/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Статистика FAQ")
        self.assertContains(response, "Всего вопросов: 5")
        self.assertContains(response, "Всего ответов: 5")
        self.assertContains(response, "Открытых вопросов: 3")
        self.assertContains(response, "Закрытых вопросов: 2")
        self.assertContains(response, "Python")

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_missing_section_uses_custom_404_page(self):
        response = self.client.get(
            "/faq/sections/",
            {"section": "Несуществующий раздел"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Страница не найдена", status_code=404)

    def test_user_can_create_question(self):
        response = self.client.post(
            "/faq/new/",
            {
                "author": "  alex  ",
                "section": "Python",
                "title": "Новый вопрос",
                "text": "Текст нового вопроса",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRegex(response.url, r"^/faq/\d+/$")
        question_response = self.client.get(response.url)
        self.assertContains(question_response, "Новый вопрос")
        self.assertContains(question_response, "alex")

    def test_invalid_question_is_not_saved(self):
        response = self.client.post(
            "/faq/new/",
            {
                "author": "alex",
                "section": "Python",
                "title": "Нет",
                "text": "Текст",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Заголовок слишком короткий",
            status_code=400,
        )
        list_response = self.client.get("/faq/")
        self.assertNotContains(list_response, "Нет")

    def test_user_can_answer_open_question(self):
        Question.objects.filter(pk=1).update(status=Question.Status.OPEN)

        response = self.client.post(
            "/faq/1/",
            {"author": "  alex  ", "text": "Новый ответ"},
        )

        self.assertRedirects(response, "/faq/1/")
        detail_response = self.client.get("/faq/1/")
        self.assertContains(detail_response, "Новый ответ")
        self.assertContains(detail_response, "alex")

    def test_closed_question_rejects_new_answer(self):
        response = self.client.post(
            "/faq/3/",
            {"author": "alex", "text": "Ответ к закрытому вопросу"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Вопрос закрыт",
            status_code=400,
        )
        detail_response = self.client.get("/faq/3/")
        self.assertNotContains(detail_response, "Ответ к закрытому вопросу")

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_missing_question_uses_custom_404_page(self):
        response = self.client.get("/faq/99999/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Страница не найдена", status_code=404)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_unknown_url_uses_custom_404_page(self):
        response = self.client.get("/unknown/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "На главную", status_code=404)
